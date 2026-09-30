import numpy as np
import cv2 as cv

class SfsDetector:
    def __init__(self, color_ranges=None, spec=None):
        self.color_ranges = color_ranges or [
            (np.array([0, 100, 70]), np.array([10, 255, 255])),
            (np.array([170, 100, 70]), np.array([180, 255, 255]))
        ]
        self.spec = spec or {
            "max_angle": 7.5,
            "max_mid_y": 248,
            "min_mid_x": 540,
            "max_mid_x": 690,
        }

    def detect_frame(self, img: np.ndarray):
        if img is None:
            return None, {"status": "NO_FRAME"}

        blur = cv.GaussianBlur(img, (5, 5), 0)
        hsv = cv.cvtColor(blur, cv.COLOR_BGR2HSV)

        combined_mask = np.zeros(img.shape[:2], dtype=np.uint8)
        for lower, upper in self.color_ranges:
            sub_mask = cv.inRange(hsv, np.array(lower), np.array(upper))
            combined_mask = cv.bitwise_or(combined_mask, sub_mask)

        kernal = cv.getStructuringElement(cv.MORPH_ELLIPSE, (5, 5))
        opening = cv.morphologyEx(combined_mask, cv.MORPH_OPEN, kernal)
        contours, _ = cv.findContours(opening, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)

        valid_contours = [cnt for cnt in contours if 1000 < cv.contourArea(cnt) <= 3500]

        if len(valid_contours) != 2:
            return img, {"status": "FAIL_CONTOURS", "count": len(valid_contours)}

        return self._process_contours(img, valid_contours)

    def _process_contours(self, img, valid_contours):
        valid_contours = sorted(valid_contours, key=lambda c: np.min(c[:, :, 0]))
        top_edge_points = []
        for cnt in valid_contours:
            min_y = np.min(cnt[:, :, 1])
            for pt in cnt:
                x, y = pt[0]
                if abs(y - min_y) <= 2:
                    top_edge_points.append([x, y])

        top_edge_points = np.array(top_edge_points, dtype=np.int32)
        if len(top_edge_points) <= 5:
            return img, {"status": "FAIL_POINTS"}

        line_params = cv.fitLine(top_edge_points, cv.DIST_L2, 0, 0.01, 0.01)
        vx, vy, x0, y0 = float(line_params[0][0]), float(line_params[1][0]), float(line_params[2][0]), float(line_params[3][0])
        angle_deg = float(np.degrees(np.arctan2(vy, vx)))

        left_hole_x = int(np.mean(valid_contours[0][:, :, 0]))
        left_hole_y = int(np.mean(valid_contours[0][:, :, 1]))
        right_hole_x = int(np.mean(valid_contours[1][:, :, 0]))
        right_hole_y = int(np.mean(valid_contours[1][:, :, 1]))

        mid_x = int((left_hole_x + right_hole_x) / 2)
        mid_y = int(((mid_x - x0) * vy / vx) + y0)

        info = {
            "status": "OK",
            "angle_deg": angle_deg,
            "mid_x": mid_x,
            "mid_y": mid_y,
            "left_hole": (left_hole_x, left_hole_y),
            "right_hole": (right_hole_x, right_hole_y),
        }
        return img, info

    def evaluate(self, info: dict) -> tuple[bool, str]:
        if not info or info.get("status") != "OK":
            return False, "Detection Failed (< 2 Holes)"

        angle = info["angle_deg"]
        mid_y = info["mid_y"]
        mid_x = info["mid_x"]

        if mid_y > self.spec["max_mid_y"]:
            return False, f"Position Y out of spec ({mid_y})"
        if abs(angle) > self.spec["max_angle"]:
            return False, f"Angle out of spec ({angle:.2f} deg)"
        if not (self.spec["min_mid_x"] <= mid_x <= self.spec["max_mid_x"]):
            return False, f"Position X out of spec ({mid_x})"

        return True, "PASS"