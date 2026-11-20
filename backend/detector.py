import math
import shutil
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import cv2
import numpy as np
from ultralytics import YOLO

import config

class EmergencyYOLODetector:
    """
    YOLOv8 Emergency and Collision Risk Detector for road safety monitoring.
    Detects vehicles, bicycles, motorcycles, and pedestrians, and performs
    spatial proximity and collision-risk analysis.
    """

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = Path(model_path or config.MODEL_PATH)
        self.model = self._load_model()
        self.target_classes = config.TARGET_CLASSES

    def _load_model(self) -> YOLO:
        """
        Loads the YOLOv8 model safely. If the model file is not present in
        backend/models/, it downloads yolov8n.pt and caches it.
        """
        config.MODELS_DIR.mkdir(parents=True, exist_ok=True)

        if self.model_path.exists():
            print(f"[Detector] Loading local YOLO model from {self.model_path}...")
            return YOLO(str(self.model_path))

        # Check if yolov8n.pt exists in root or working directory
        root_model = Path(config.DEFAULT_MODEL_NAME)
        if root_model.exists():
            print(f"[Detector] Found {root_model}. Moving to {self.model_path}...")
            shutil.copy(str(root_model), str(self.model_path))
            return YOLO(str(self.model_path))

        print(f"[Detector] Downloading standard {config.DEFAULT_MODEL_NAME} weights...")
        model = YOLO(config.DEFAULT_MODEL_NAME)
        # Save model copy into models/ folder for future offline use
        try:
            if root_model.exists() and not self.model_path.exists():
                shutil.copy(str(root_model), str(self.model_path))
        except Exception as e:
            print(f"[Detector] Note: Could not cache model copy: {e}")

        return model

    @staticmethod
    def calculate_iou(box1: List[int], box2: List[int]) -> float:
        """Calculates Intersection over Union (IoU) between two bounding boxes [x1, y1, x2, y2]."""
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])

        intersection_w = max(0, x2 - x1)
        intersection_h = max(0, y2 - y1)
        intersection_area = intersection_w * intersection_h

        if intersection_area == 0:
            return 0.0

        area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        union_area = area1 + area2 - intersection_area

        if union_area <= 0:
            return 0.0

        return intersection_area / union_area

    @staticmethod
    def calculate_centroid_distance(box1: List[int], box2: List[int]) -> float:
        """Calculates Euclidean distance between centroids of two boxes."""
        cx1 = (box1[0] + box1[2]) / 2.0
        cy1 = (box1[1] + box1[3]) / 2.0
        cx2 = (box2[0] + box2[2]) / 2.0
        cy2 = (box2[1] + box2[3]) / 2.0
        return math.sqrt((cx1 - cx2) ** 2 + (cy1 - cy2) ** 2)

    def analyze_collision_risks(
        self,
        detections: List[Dict[str, Any]]
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Analyzes pairs of detected objects to estimate collision risk levels.
        Categorizes risks as LOW, MEDIUM, or HIGH.
        Clearly notes that all alerts are estimated risks, not confirmed accidents.
        """
        risks = []
        highest_risk = "LOW" if detections else "NONE"
        has_medium = False
        has_high = False

        num_objects = len(detections)
        if num_objects < 2:
            return ("LOW" if detections else "NONE", risks)

        vulnerable_classes = {"person", "bicycle"}
        vehicle_classes = {"car", "motorcycle", "bus", "truck"}

        for i in range(num_objects):
            for j in range(i + 1, num_objects):
                obj_a = detections[i]
                obj_b = detections[j]

                box_a = obj_a["box"]
                box_b = obj_b["box"]
                cls_a = obj_a["class_name"]
                cls_b = obj_b["class_name"]

                iou = self.calculate_iou(box_a, box_b)
                dist = self.calculate_centroid_distance(box_a, box_b)

                is_vulnerable_pair = (
                    (cls_a in vulnerable_classes and cls_b in vehicle_classes) or
                    (cls_b in vulnerable_classes and cls_a in vehicle_classes)
                )

                risk_level = None
                incident_type = None
                description = None

                # Rule 1: Vulnerable road user (pedestrian/cyclist) + vehicle
                if is_vulnerable_pair:
                    ped_name = cls_a if cls_a in vulnerable_classes else cls_b
                    veh_name = cls_b if cls_a in vulnerable_classes else cls_a

                    if iou > 0.01 or dist < config.PEDESTRIAN_HAZARD_PROXIMITY_PX:
                        risk_level = "HIGH"
                        has_high = True
                        incident_type = "PEDESTRIAN_COLLISION_RISK"
                        description = (
                            f"High collision risk: Vulnerable road user ({ped_name}) in close proximity "
                            f"with {veh_name} (Distance: {int(dist)}px). Simulated risk estimate."
                        )
                    elif dist < config.COLLISION_PROXIMITY_MED_PX:
                        risk_level = "MEDIUM"
                        has_medium = True
                        incident_type = "PEDESTRIAN_PROXIMITY_WARNING"
                        description = (
                            f"Pedestrian proximity caution: {ped_name} moving near {veh_name} "
                            f"(Distance: {int(dist)}px). Simulated risk estimate."
                        )
                # Rule 2: Vehicle-to-vehicle interaction
                else:
                    if iou >= config.COLLISION_IOU_HIGH or dist < config.COLLISION_PROXIMITY_HIGH_PX:
                        risk_level = "HIGH"
                        has_high = True
                        incident_type = "POTENTIAL_VEHICLE_COLLISION"
                        description = (
                            f"High collision risk detected between {cls_a} and {cls_b} "
                            f"(IoU: {iou:.2f}, Centroid Distance: {int(dist)}px). "
                            f"Simulated risk estimate; not a confirmed physical accident."
                        )
                    elif iou >= config.COLLISION_IOU_MEDIUM or dist < config.COLLISION_PROXIMITY_MED_PX:
                        risk_level = "MEDIUM"
                        has_medium = True
                        incident_type = "IMMINENT_PROXIMITY_HAZARD"
                        description = (
                            f"Medium proximity hazard between {cls_a} and {cls_b} "
                            f"(Centroid Distance: {int(dist)}px). Simulated risk estimate."
                        )
                    elif dist < 120.0:
                        risk_level = "LOW"
                        incident_type = "CLOSE_TRAFFIC_PROXIMITY"
                        description = (
                            f"Low risk traffic proximity between {cls_a} and {cls_b}."
                        )

                if risk_level:
                    risks.append({
                        "risk_level": risk_level,
                        "incident_type": incident_type,
                        "description": description,
                        "iou": round(iou, 4),
                        "distance_px": round(dist, 2),
                        "pair": [cls_a, cls_b],
                        "object_indices": [i, j],
                        "confidence": round(float((obj_a["confidence"] + obj_b["confidence"]) / 2), 4)
                    })

        if has_high:
            highest_risk = "HIGH"
        elif has_medium:
            highest_risk = "MEDIUM"
        elif risks:
            highest_risk = "LOW"
        else:
            highest_risk = "LOW" if detections else "NONE"

        return highest_risk, risks

    def detect_frame(
        self,
        frame: np.ndarray,
        conf_threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Runs YOLOv8 object detection and collision risk analysis on a single OpenCV BGR frame.
        """
        conf = conf_threshold or config.CONFIDENCE_THRESHOLD
        results = self.model(frame, conf=conf, verbose=False)[0]

        detections = []
        class_counts: Dict[str, int] = {}

        if results.boxes is not None and len(results.boxes) > 0:
            boxes = results.boxes.xyxy.cpu().numpy().astype(int)
            confs = results.boxes.conf.cpu().numpy()
            classes = results.boxes.cls.cpu().numpy().astype(int)

            for i, cls_id in enumerate(classes):
                if cls_id in self.target_classes:
                    cls_name = self.target_classes[cls_id]
                    box = boxes[i].tolist()
                    confidence = float(confs[i])

                    cx = int((box[0] + box[2]) / 2)
                    cy = int((box[1] + box[3]) / 2)

                    detections.append({
                        "id": len(detections) + 1,
                        "class_id": int(cls_id),
                        "class_name": cls_name,
                        "confidence": round(confidence, 4),
                        "box": box,
                        "centroid": [cx, cy],
                        "risk_level": "LOW"  # default before pair analysis
                    })

                    class_counts[cls_name] = class_counts.get(cls_name, 0) + 1

        # Analyze pair interactions for collision hazards
        peak_risk, risks = self.analyze_collision_risks(detections)

        # Update individual object risk tags based on detected risk pairs
        for r in risks:
            level = r["risk_level"]
            for idx in r["object_indices"]:
                curr = detections[idx]["risk_level"]
                if level == "HIGH" or (level == "MEDIUM" and curr != "HIGH"):
                    detections[idx]["risk_level"] = level

        return {
            "detections": detections,
            "risks": risks,
            "peak_risk_level": peak_risk,
            "class_counts": class_counts,
            "total_objects": len(detections)
        }

    def annotate_frame(
        self,
        frame: np.ndarray,
        detection_result: Dict[str, Any],
        show_metrics: bool = True
    ) -> np.ndarray:
        """
        Draws bounding boxes, centroid lines, and emergency status banners onto the frame.
        """
        annotated = frame.copy()
        detections = detection_result["detections"]
        risks = detection_result["risks"]
        peak_risk = detection_result["peak_risk_level"]

        # Color codes: (B, G, R)
        color_green = (50, 205, 50)
        color_amber = (0, 165, 255)
        color_red = (0, 0, 235)

        # 1. Draw collision connection lines between risk pairs
        for r in risks:
            if r["risk_level"] in ("MEDIUM", "HIGH"):
                idx_a, idx_b = r["object_indices"]
                pt_a = tuple(detections[idx_a]["centroid"])
                pt_b = tuple(detections[idx_b]["centroid"])
                line_color = color_red if r["risk_level"] == "HIGH" else color_amber
                thickness = 2 if r["risk_level"] == "HIGH" else 1
                cv2.line(annotated, pt_a, pt_b, line_color, thickness, cv2.LINE_AA)

        # 2. Draw bounding boxes
        for det in detections:
            box = det["box"]
            cls_name = det["class_name"]
            conf = det["confidence"]
            risk = det["risk_level"]

            if risk == "HIGH":
                color = color_red
            elif risk == "MEDIUM":
                color = color_amber
            else:
                color = color_green

            # Draw rectangle
            cv2.rectangle(annotated, (box[0], box[1]), (box[2], box[3]), color, 2)

            # Draw centroid point
            cx, cy = det["centroid"]
            cv2.circle(annotated, (cx, cy), 4, color, -1)

            # Label text
            label = f"{cls_name.upper()} {conf:.2f}"
            if risk != "LOW":
                label += f" [{risk}]"

            (label_w, label_h), baseline = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
            )
            top_y = max(box[1], label_h + 10)
            cv2.rectangle(
                annotated,
                (box[0], top_y - label_h - 6),
                (box[0] + label_w + 6, top_y),
                color,
                -1
            )
            cv2.putText(
                annotated,
                label,
                (box[0] + 3, top_y - 4),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                1,
                cv2.LINE_AA
            )

        # 3. Draw top status banner
        if show_metrics:
            banner_color = (30, 30, 30)
            if peak_risk == "HIGH":
                banner_color = (0, 0, 160)
            elif peak_risk == "MEDIUM":
                banner_color = (0, 100, 180)

            h, w, _ = annotated.shape
            cv2.rectangle(annotated, (0, 0), (w, 36), banner_color, -1)

            status_text = f"EMERGENCY INTELLIGENCE | STATUS: {peak_risk} RISK | OBJECTS: {len(detections)}"
            cv2.putText(
                annotated,
                status_text,
                (12, 24),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2,
                cv2.LINE_AA
            )

        return annotated

# Global singleton detector instance
_detector_instance: Optional[EmergencyYOLODetector] = None

def get_detector() -> EmergencyYOLODetector:
    """Returns a shared EmergencyYOLODetector instance."""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = EmergencyYOLODetector()
    return _detector_instance
