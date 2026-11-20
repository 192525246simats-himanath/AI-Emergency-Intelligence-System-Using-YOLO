"""
Complete Automated Verification Suite for Emergency Intelligence Backend.
Tests all functional endpoints, database operations, YOLO detection, and simulated dispatches.
"""

import io
import json
import unittest
import cv2
import numpy as np

from app import create_app
import database

class BackendVerificationTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

    def test_01_health_check(self):
        """Test GET /api/health returns 200 and expected metadata."""
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("yolo_model", data)
        self.assertIn("car", data["yolo_classes"])
        self.assertIn("person", data["yolo_classes"])
        print("  [PASS] GET /api/health verified")

    def test_02_stats_endpoint(self):
        """Test GET /api/stats returns system metrics."""
        resp = self.client.get("/api/stats")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("total_incidents", data)
        self.assertIn("high_risk", data)
        self.assertEqual(data["system_status"], "OPERATIONAL")
        print("  [PASS] GET /api/stats verified")

    def test_03_manual_alert(self):
        """Test POST /api/incidents/manual-alert creates an incident record."""
        payload = {
            "incident_type": "TEST_OPERATOR_ALERT",
            "risk_level": "HIGH",
            "description": "Verification test alert on Sector 4",
            "location_tag": "Sector 4 North Gate",
            "objects_involved": ["car", "bus"]
        }
        resp = self.client.post(
            "/api/incidents/manual-alert",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertIn("incident_id", data)
        BackendVerificationTests.test_incident_id = data["incident_id"]
        print(f"  [PASS] POST /api/incidents/manual-alert created Incident #{data['incident_id']}")

    def test_04_get_incidents(self):
        """Test GET /api/incidents returns list containing the created alert."""
        resp = self.client.get("/api/incidents?limit=10")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertGreaterEqual(data["total"], 1)
        found = any(inc["id"] == self.test_incident_id for inc in data["incidents"])
        self.assertTrue(found, "Created incident should appear in incident list")
        print("  [PASS] GET /api/incidents verified")

    def test_05_get_incident_detail(self):
        """Test GET /api/incidents/<id> retrieves the specific incident."""
        resp = self.client.get(f"/api/incidents/{self.test_incident_id}")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["id"], self.test_incident_id)
        self.assertEqual(data["risk_level"], "HIGH")
        print(f"  [PASS] GET /api/incidents/{self.test_incident_id} verified")

    def test_06_update_incident_status(self):
        """Test POST /api/incidents/<id>/status updates status to ACKNOWLEDGED."""
        payload = {"status": "ACKNOWLEDGED", "notes": "Officer acknowledged alert."}
        resp = self.client.post(
            f"/api/incidents/{self.test_incident_id}/status",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "ACKNOWLEDGED")
        print(f"  [PASS] POST /api/incidents/{self.test_incident_id}/status updated to ACKNOWLEDGED")

    def test_07_simulated_dispatch(self):
        """Test POST /api/incidents/<id>/dispatch triggers simulated emergency response."""
        payload = {"agency": "Metropolitan Traffic Rescue"}
        resp = self.client.post(
            f"/api/incidents/{self.test_incident_id}/dispatch",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["dispatch_type"], "SIMULATED")
        self.assertEqual(data["dispatch_status"], "SIMULATED_DISPATCHED")
        print("  [PASS] POST /api/incidents/<id>/dispatch executed simulated dispatch")

    def test_08_detect_image(self):
        """Test POST /api/detect/image processes an uploaded image with YOLO."""
        # Create a synthetic image with two drawn vehicles
        test_img = np.zeros((480, 640, 3), dtype=np.uint8)
        test_img[200:, :] = [70, 70, 70]  # asphalt
        # Draw vehicle 1
        cv2.rectangle(test_img, (150, 260), (280, 350), (40, 40, 220), -1)
        # Draw vehicle 2 nearby
        cv2.rectangle(test_img, (270, 270), (400, 360), (220, 40, 40), -1)

        _, encoded = cv2.imencode(".jpg", test_img)
        file_bytes = io.BytesIO(encoded.tobytes())

        resp = self.client.post(
            "/api/detect/image",
            data={"file": (file_bytes, "test_traffic.jpg"), "location_tag": "Unit Test Cam"},
            content_type="multipart/form-data"
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertIn("peak_risk_level", data)
        self.assertIn("annotated_image_url", data)
        print("  [PASS] POST /api/detect/image processed image and returned detection analysis")

    def test_09_invalid_upload_handling(self):
        """Test error handling when no file is uploaded or bad extension passed."""
        # Missing file
        resp = self.client.post("/api/detect/image", data={})
        self.assertEqual(resp.status_code, 400)

        # Invalid extension
        dummy_file = io.BytesIO(b"fake executable content")
        resp = self.client.post(
            "/api/detect/image",
            data={"file": (dummy_file, "malicious.exe")},
            content_type="multipart/form-data"
        )
        self.assertEqual(resp.status_code, 400)
        print("  [PASS] Invalid file handling and security filters verified")

    def test_10_stream_endpoint(self):
        """Test GET /api/stream connects and yields MJPEG chunks."""
        resp = self.client.get("/api/stream", buffered=False)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("multipart/x-mixed-replace", resp.content_type)
        print("  [PASS] GET /api/stream connected and validated MJPEG header")

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("RUNNING EMERGENCY INTELLIGENCE BACKEND TEST SUITE")
    print("=" * 70)
    unittest.main()
