import os
import time
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, Generator
import cv2
import numpy as np

import config
import database
from detector import get_detector

def process_image(
    image_path: str,
    location_tag: str = "Uploaded Image Feeder"
) -> Dict[str, Any]:
    """
    Processes a single image: runs YOLO detection, estimates collision risks,
    saves an annotated snapshot, and stores any detected incidents in the database.
    """
    detector = get_detector()
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found at path: {image_path}")

    frame = cv2.imread(str(path))
    if frame is None:
        raise ValueError(f"Could not decode image at path: {image_path}")

    detection_result = detector.detect_frame(frame)
    annotated = detector.annotate_frame(frame, detection_result)

    # Save annotated snapshot
    filename = f"annotated_{uuid.uuid4().hex[:8]}_{path.name}"
    snapshot_rel_path = f"snapshots/{filename}"
    snapshot_full_path = config.SNAPSHOT_FOLDER / filename
    cv2.imwrite(str(snapshot_full_path), annotated)

    # If risk detected, insert incident record in DB
    incident_id = None
    peak_risk = detection_result["peak_risk_level"]
    risks = detection_result["risks"]

    if peak_risk in ("HIGH", "MEDIUM") and risks:
        primary_risk = risks[0]
        desc = primary_risk["description"]
        inc_type = primary_risk["incident_type"]
        conf = primary_risk["confidence"]
        involved_objects = primary_risk.get("pair", [])
        boxes = [d["box"] for d in detection_result["detections"]]

        incident_id = database.insert_incident(
            incident_type=inc_type,
            risk_level=peak_risk,
            confidence=conf,
            description=desc,
            location_tag=location_tag,
            objects_involved=involved_objects,
            bounding_boxes=[{"box": b} for b in boxes],
            snapshot_path=snapshot_rel_path,
            status="ACTIVE"
        )

    return {
        "success": True,
        "peak_risk_level": peak_risk,
        "total_objects": detection_result["total_objects"],
        "class_counts": detection_result["class_counts"],
        "detections": detection_result["detections"],
        "risks": risks,
        "incident_id": incident_id,
        "snapshot_path": snapshot_rel_path,
        "annotated_image_url": f"/outputs/{snapshot_rel_path}"
    }

def process_video_file(
    video_path: str,
    location_tag: str = "Recorded Video Stream",
    frame_sample_rate: int = 2
) -> Dict[str, Any]:
    """
    Analyzes an uploaded video file frame-by-frame using YOLOv8 and collision analysis.
    Produces an annotated output video and logs significant incidents to the database.
    """
    detector = get_detector()
    path = Path(video_path)
    if not path.exists():
        raise FileNotFoundError(f"Video file not found at: {video_path}")

    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise ValueError(f"Failed to open video file: {video_path}")

    orig_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    orig_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # Output video file
    out_name = f"processed_{uuid.uuid4().hex[:8]}.mp4"
    out_rel_path = f"videos/{out_name}"
    out_dir = config.OUTPUT_FOLDER / "videos"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_full_path = out_dir / out_name

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out_writer = cv2.VideoWriter(
        str(out_full_path),
        fourcc,
        float(fps / max(1, frame_sample_rate)),
        (orig_width, orig_height)
    )

    frame_idx = 0
    processed_count = 0
    overall_peak_risk = "NONE"
    aggregate_class_counts: Dict[str, int] = {}
    incidents_logged = []
    last_logged_frame = -999
    cooldown_frames = int(fps * 2)  # Cooldown between repeated DB logging

    best_snapshot_rel_path = None
    highest_risk_score = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            frame_idx += 1
            if frame_idx % frame_sample_rate != 0:
                continue

            processed_count += 1
            detection_result = detector.detect_frame(frame)
            annotated = detector.annotate_frame(frame, detection_result)
            out_writer.write(annotated)

            current_peak = detection_result["peak_risk_level"]
            risks = detection_result["risks"]

            # Update aggregate class counts
            for cls_name, count in detection_result["class_counts"].items():
                aggregate_class_counts[cls_name] = max(
                    aggregate_class_counts.get(cls_name, 0), count
                )

            # Update overall peak risk
            risk_hierarchy = {"NONE": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}
            if risk_hierarchy.get(current_peak, 0) > risk_hierarchy.get(overall_peak_risk, 0):
                overall_peak_risk = current_peak

            # Save snapshot if this frame has the highest severity seen so far
            current_score = risk_hierarchy.get(current_peak, 0)
            if current_score >= highest_risk_score and current_score > 0:
                highest_risk_score = current_score
                snap_name = f"snap_frame_{frame_idx}_{uuid.uuid4().hex[:6]}.jpg"
                snap_path = config.SNAPSHOT_FOLDER / snap_name
                cv2.imwrite(str(snap_path), annotated)
                best_snapshot_rel_path = f"snapshots/{snap_name}"

            # Log incident to SQLite with cooldown to avoid duplicate entries
            if current_peak in ("HIGH", "MEDIUM") and risks:
                if (frame_idx - last_logged_frame) >= cooldown_frames:
                    primary_risk = risks[0]
                    boxes = [d["box"] for d in detection_result["detections"]]

                    inc_id = database.insert_incident(
                        incident_type=primary_risk["incident_type"],
                        risk_level=current_peak,
                        confidence=primary_risk["confidence"],
                        description=f"[Video Frame {frame_idx}] {primary_risk['description']}",
                        location_tag=location_tag,
                        objects_involved=primary_risk.get("pair", []),
                        bounding_boxes=[{"box": b} for b in boxes],
                        snapshot_path=best_snapshot_rel_path,
                        status="ACTIVE"
                    )
                    incidents_logged.append(inc_id)
                    last_logged_frame = frame_idx

    finally:
        cap.release()
        out_writer.release()

    return {
        "success": True,
        "total_frames": total_frames,
        "processed_frames": processed_count,
        "fps": round(float(fps), 2),
        "duration_seconds": round(float(total_frames / max(1.0, fps)), 2),
        "peak_risk_level": overall_peak_risk,
        "class_counts": aggregate_class_counts,
        "incidents_logged_count": len(incidents_logged),
        "incident_ids": incidents_logged,
        "annotated_video_url": f"/outputs/{out_rel_path}",
        "snapshot_url": f"/outputs/{best_snapshot_rel_path}" if best_snapshot_rel_path else None
    }

class SimulatedRoadTrafficStream:
    """
    Generates synthetic road traffic video frames with moving vehicles,
    pedestrians, and road markings. Enables real YOLO detection and collision
    analysis even when running on a headless cloud server (Render) without a physical webcam.
    """

    def __init__(self, width: int = 640, height: int = 480):
        self.width = width
        self.height = height
        self.step = 0

        # Simulated entities: (x, y, dx, dy, color, size, label)
        self.entities = [
            {"type": "car", "x": 100, "y": 280, "dx": 3, "w": 70, "h": 40, "color": (220, 50, 50)},
            {"type": "truck", "x": 450, "y": 320, "dx": -2, "w": 100, "h": 50, "color": (50, 120, 220)},
            {"type": "motorcycle", "x": 250, "y": 240, "dx": 4, "w": 40, "h": 25, "color": (220, 220, 50)},
            {"type": "pedestrian", "x": 300, "y": 200, "dx": 1, "w": 25, "h": 50, "color": (200, 200, 200)}
        ]

    def get_frame(self) -> np.ndarray:
        self.step += 1
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)

        # Background environment
        frame[:180, :] = [80, 140, 70]   # Grass / roadside
        frame[180:, :] = [60, 60, 60]    # Asphalt road

        # Road lane dividers
        dash_offset = (self.step * 5) % 40
        for x in range(-dash_offset, self.width, 40):
            cv2.line(frame, (x, 300), (x + 20, 300), (255, 255, 255), 3)

        # Crosswalk
        for x in range(260, 360, 20):
            cv2.rectangle(frame, (x, 190), (x + 12, 230), (240, 240, 240), -1)

        # Move and draw entities
        for ent in self.entities:
            ent["x"] += ent["dx"]
            if ent["x"] > self.width + 50:
                ent["x"] = -100
            elif ent["x"] < -120:
                ent["x"] = self.width + 80

            x, y, w, h = ent["x"], ent["y"], ent["w"], ent["h"]

            # Draw vehicle/pedestrian body
            cv2.rectangle(frame, (x, y), (x + w, y + h), ent["color"], -1)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 255, 255), 1)

            # Draw wheels or head
            if ent["type"] in ("car", "truck"):
                cv2.circle(frame, (x + 15, y + h), 6, (20, 20, 20), -1)
                cv2.circle(frame, (x + w - 15, y + h), 6, (20, 20, 20), -1)
            elif ent["type"] == "pedestrian":
                cv2.circle(frame, (x + 12, y - 6), 6, (240, 200, 180), -1)

            cv2.putText(
                frame,
                ent["type"],
                (x + 2, y - 8),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.35,
                (255, 255, 255),
                1
            )

        return frame

def generate_mjpeg_stream(source: Any = 0) -> Generator[bytes, None, None]:
    """
    Yields multipart MJPEG stream frames with real-time YOLO detection and risk overlay.
    Falls back gracefully to a simulated road traffic CCTV stream if physical webcam is inaccessible.
    """
    detector = get_detector()
    cap = None
    use_simulation = False

    try:
        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            use_simulation = True
    except Exception:
        use_simulation = True

    sim_stream = SimulatedRoadTrafficStream() if use_simulation else None

    try:
        while True:
            if not use_simulation and cap is not None and cap.isOpened():
                ret, frame = cap.read()
                if not ret or frame is None:
                    # Switch to simulation if webcam read fails
                    use_simulation = True
                    sim_stream = SimulatedRoadTrafficStream()
                    continue
            else:
                frame = sim_stream.get_frame()
                time.sleep(0.04)  # ~25 FPS

            detection_result = detector.detect_frame(frame)
            annotated = detector.annotate_frame(frame, detection_result)

            ret, buffer = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if not ret:
                continue

            frame_bytes = buffer.tobytes()
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
            )
    finally:
        if cap is not None and cap.isOpened():
            cap.release()
