import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from flask import Flask, request, jsonify, Response, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

import config
import database
import video_processor
from detector import get_detector

def create_app() -> Flask:
    """Application factory for Flask emergency intelligence service."""
    app = Flask(__name__)
    app.config["SECRET_KEY"] = config.SECRET_KEY
    app.config["MAX_CONTENT_LENGTH"] = config.MAX_CONTENT_LENGTH

    # Enable Cross-Origin Resource Sharing (CORS) for Vercel and local dev
    CORS(app)

    @app.after_request
    def add_cors_headers(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        return response

    @app.before_request
    def handle_options_preflight():
        if request.method == "OPTIONS":
            response = Response()
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            return response

    # Initialize database tables
    database.init_db()

    # Preload YOLO detector model at startup
    try:
        get_detector()
    except Exception as e:
        app.logger.warning(f"Initial detector preload warning: {e}")

    # =========================================================================
    # Error Handlers
    # =========================================================================
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({"error": "Bad Request", "message": str(error)}), 400

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Not Found", "message": "Endpoint or resource not found"}), 404

    @app.errorhandler(413)
    def file_too_large(error):
        return jsonify({"error": "Payload Too Large", "message": "File exceeds 100MB limit"}), 413

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({"error": "Internal Server Error", "message": str(error)}), 500

    # =========================================================================
    # Helper Functions
    # =========================================================================
    def allowed_file(filename: str, allowed_set: set) -> bool:
        return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_set

    # =========================================================================
    # Core Health & System Endpoints
    # =========================================================================
    @app.route("/api/health", methods=["GET"])
    def health_check():
        """Health check endpoint for Render, uptime monitors, and frontend verification."""
        return jsonify({
            "status": "healthy",
            "service": "AI-Based Emergency Intelligence and Response System",
            "version": "1.0.0",
            "yolo_model": config.DEFAULT_MODEL_NAME,
            "yolo_classes": list(config.TARGET_CLASSES.values()),
            "environment": "production" if not config.DEBUG else "development",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 200

    @app.route("/api/stats", methods=["GET"])
    def get_stats():
        """Returns aggregate dashboard metrics."""
        stats = database.get_incident_stats()
        stats["timestamp"] = datetime.now(timezone.utc).isoformat()
        stats["system_status"] = "OPERATIONAL"
        return jsonify(stats), 200

    # =========================================================================
    # Media Analysis Endpoints (Image & Video)
    # =========================================================================
    @app.route("/api/detect/image", methods=["POST"])
    def detect_image():
        """
        Accepts an uploaded image file, processes it through YOLOv8,
        evaluates collision/hazard risks, and logs any incidents.
        """
        file = request.files.get("file") or request.files.get("image")
        if not file or file.filename == "":
            return jsonify({"error": "No image file provided in request (use field 'file' or 'image')"}), 400

        if not allowed_file(file.filename, config.ALLOWED_IMAGE_EXTENSIONS):
            return jsonify({
                "error": "Unsupported file extension",
                "allowed": list(config.ALLOWED_IMAGE_EXTENSIONS)
            }), 400

        filename = secure_filename(file.filename)
        unique_name = f"{uuid.uuid4().hex[:8]}_{filename}"
        save_path = config.UPLOAD_FOLDER / unique_name
        file.save(str(save_path))

        location = request.form.get("location_tag", "Uploaded Image Feed")

        try:
            result = video_processor.process_image(str(save_path), location_tag=location)
            result["original_filename"] = filename
            return jsonify(result), 200
        except Exception as e:
            return jsonify({"error": "Image processing failed", "details": str(e)}), 500

    @app.route("/api/detect/video", methods=["POST"])
    def detect_video():
        """
        Accepts an uploaded video file, processes frames using OpenCV and YOLOv8,
        detects collision risks, and creates an annotated video.
        """
        file = request.files.get("file") or request.files.get("video")
        if not file or file.filename == "":
            return jsonify({"error": "No video file provided in request (use field 'file' or 'video')"}), 400

        if not allowed_file(file.filename, config.ALLOWED_VIDEO_EXTENSIONS):
            return jsonify({
                "error": "Unsupported video extension",
                "allowed": list(config.ALLOWED_VIDEO_EXTENSIONS)
            }), 400

        filename = secure_filename(file.filename)
        unique_name = f"{uuid.uuid4().hex[:8]}_{filename}"
        save_path = config.UPLOAD_FOLDER / unique_name
        file.save(str(save_path))

        location = request.form.get("location_tag", "Recorded Traffic Stream")
        frame_skip = int(request.form.get("frame_sample_rate", 2))

        try:
            result = video_processor.process_video_file(
                str(save_path),
                location_tag=location,
                frame_sample_rate=frame_skip
            )
            result["original_filename"] = filename
            return jsonify(result), 200
        except Exception as e:
            return jsonify({"error": "Video processing failed", "details": str(e)}), 500

    # =========================================================================
    # Real-Time Video Streaming Endpoint
    # =========================================================================
    @app.route("/api/stream", methods=["GET"])
    def video_stream():
        """
        Streams real-time MJPEG video with live YOLO detection overlays.
        Falls back to a simulated road traffic stream if no physical camera is attached.
        """
        source = request.args.get("source", 0)
        try:
            source = int(source)
        except ValueError:
            pass  # keep as RTSP or video path string if passed

        return Response(
            video_processor.generate_mjpeg_stream(source=source),
            mimetype="multipart/x-mixed-replace; boundary=frame"
        )

    # =========================================================================
    # Incident Management & Alert Endpoints
    # =========================================================================
    @app.route("/api/incidents", methods=["GET"])
    def get_incidents():
        """Retrieves list of logged emergency incidents with optional filtering."""
        limit = min(int(request.args.get("limit", 50)), 200)
        risk_level = request.args.get("risk_level")
        status = request.args.get("status")

        incidents = database.get_incidents(limit=limit, risk_level=risk_level, status=status)
        return jsonify({
            "total": len(incidents),
            "incidents": incidents
        }), 200

    @app.route("/api/incidents/<int:incident_id>", methods=["GET"])
    def get_incident(incident_id: int):
        """Retrieves a single incident by ID."""
        incident = database.get_incident_by_id(incident_id)
        if not incident:
            return jsonify({"error": "Incident not found", "id": incident_id}), 404
        return jsonify(incident), 200

    @app.route("/api/incidents/<int:incident_id>/status", methods=["POST"])
    def update_incident_status(incident_id: int):
        """Updates the status of an incident (e.g. ACKNOWLEDGED or RESOLVED)."""
        data = request.get_json(silent=True) or {}
        new_status = data.get("status")
        notes = data.get("notes")

        if not new_status:
            return jsonify({"error": "Missing 'status' in JSON request body"}), 400

        updated = database.update_incident_status(
            incident_id=incident_id,
            status=new_status,
            simulated_dispatch_notes=notes
        )

        if not updated:
            return jsonify({"error": "Incident not found or status not changed", "id": incident_id}), 404

        return jsonify({
            "success": True,
            "incident_id": incident_id,
            "status": new_status.upper(),
            "message": f"Incident #{incident_id} marked as {new_status.upper()}"
        }), 200

    @app.route("/api/incidents/<int:incident_id>/dispatch", methods=["POST"])
    def dispatch_simulated_emergency(incident_id: int):
        """
        Triggers a SIMULATED emergency response dispatch (Ambulance / Traffic Patrol).
        Clearly marks dispatch as simulated in accordance with project safety guidelines.
        """
        data = request.get_json(silent=True) or {}
        agency = data.get("agency", "Traffic Police & Medical Response")
        notes = f"[SIMULATED DISPATCH] Request sent to {agency} at {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}. Simulation mode active."

        updated = database.update_incident_status(
            incident_id=incident_id,
            simulated_dispatch_status="SIMULATED_DISPATCHED",
            simulated_dispatch_notes=notes
        )

        if not updated:
            return jsonify({"error": "Incident not found", "id": incident_id}), 404

        return jsonify({
            "success": True,
            "incident_id": incident_id,
            "dispatch_type": "SIMULATED",
            "agency": agency,
            "dispatch_status": "SIMULATED_DISPATCHED",
            "message": "Simulated emergency dispatch recorded. In a live production system, dispatch signals would route to emergency dispatchers.",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 200

    @app.route("/api/incidents/manual-alert", methods=["POST"])
    def manual_alert():
        """Allows an operator or testing script to manually record an emergency incident."""
        data = request.get_json(silent=True) or {}
        incident_type = data.get("incident_type", "MANUAL_OPERATOR_ALERT")
        risk_level = data.get("risk_level", "MEDIUM").upper()
        description = data.get("description", "Manual operator incident logged from control room.")
        location = data.get("location_tag", "Camera Sector Beta - Manual Override")

        if risk_level not in ("LOW", "MEDIUM", "HIGH"):
            return jsonify({"error": "Invalid risk_level. Must be LOW, MEDIUM, or HIGH"}), 400

        inc_id = database.insert_incident(
            incident_type=incident_type,
            risk_level=risk_level,
            confidence=1.0,
            description=description,
            location_tag=location,
            objects_involved=data.get("objects_involved", ["operator_alert"]),
            status="ACTIVE"
        )

        return jsonify({
            "success": True,
            "incident_id": inc_id,
            "risk_level": risk_level,
            "message": f"Manual alert logged as Incident #{inc_id}"
        }), 201

    # =========================================================================
    # Static Output Files Serving (Snapshots and Processed Videos)
    # =========================================================================
    @app.route("/outputs/<path:filename>", methods=["GET"])
    def serve_output(filename: str):
        """Serves annotated images and processed videos from backend/outputs/."""
        return send_from_directory(str(config.OUTPUT_FOLDER), filename)

    # =========================================================================
    # Frontend Static & SPA Serving (Localhost All-in-One Testing)
    # =========================================================================
    frontend_dir = config.BASE_DIR.parent / "frontend"

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve_frontend(path):
        """Serves frontend static assets or index.html for SPA routes."""
        if path and (frontend_dir / path).exists():
            return send_from_directory(str(frontend_dir), path)
        if (frontend_dir / "index.html").exists():
            return send_from_directory(str(frontend_dir), "index.html")
        return jsonify({"service": "Emergency Intelligence API", "status": "active"}), 200

    return app

# WSGI Application object for Gunicorn / Render
app = create_app()

if __name__ == "__main__":
    print(f"Starting Emergency Intelligence Backend on {config.HOST}:{config.PORT} (Debug={config.DEBUG})...")
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
