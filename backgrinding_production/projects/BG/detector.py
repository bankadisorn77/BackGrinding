import datetime
from pathlib import Path
import cv2
import numpy as np
import openvino as ov
import yaml


class BGDetector:
    def __init__(self, model_dir, save_dir, conf=0.7, device="CPU", api=None):
        self.conf_thresh = float(conf)
        self.nms_thresh = 0.45
        self.device = device.upper()
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)
        model_path = self._resolve_model(model_dir)
        self.core = ov.Core()
        self.model = self.core.read_model(model=model_path)
        try:
            self.compiled_model = self.core.compile_model(self.model, self.device)
        except Exception:
            self.device = "CPU"
            self.compiled_model = self.core.compile_model(self.model, self.device)
        self.input_layer = self.compiled_model.input(0)
        self.output_layer = self.compiled_model.output(0)
        _, _, self.img_h, self.img_w = self.input_layer.shape
        self.names = self._load_names(Path(model_dir))
        self.api = api

    @staticmethod
    def _resolve_model(model_dir):
        path = Path(model_dir)
        if path.is_dir():
            xmls = list(path.glob("*.xml"))
            if not xmls:
                raise FileNotFoundError("OpenVINO model not found: {}".format(path))
            return str(xmls[0])
        return str(path)

    @staticmethod
    def _load_names(model_dir):
        metadata = model_dir / "metadata.yaml"
        if not metadata.exists():
            return {}
        try:
            with metadata.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            names = data.get("names", data.get("name", {}))
            return {int(k): str(v) for k, v in names.items()}
        except Exception:
            return {}

    def _preprocess(self, image):
        original_h, original_w = image.shape[:2]
        resized = cv2.resize(image, (self.img_w, self.img_h), interpolation=cv2.INTER_LINEAR)
        tensor = np.expand_dims(resized.transpose(2, 0, 1), 0).astype(np.float32) / 255.0
        return tensor, original_h, original_w

    def _postprocess(self, output, original_h, original_w):
        predictions = np.squeeze(output)
        if predictions.shape[0] < predictions.shape[1]:
            predictions = predictions.T
        boxes, scores, class_ids = [], [], []
        rx = float(self.img_w) / original_w
        ry = float(self.img_h) / original_h
        for pred in predictions:
            scores_all = pred[4:]
            class_id = int(np.argmax(scores_all))
            score = float(scores_all[class_id])
            if score < self.conf_thresh:
                continue
            cx, cy, w, h = map(float, pred[:4])
            x = int((cx - w / 2) / rx)
            y = int((cy - h / 2) / ry)
            bw = int(w / rx)
            bh = int(h / ry)
            boxes.append([x, y, bw, bh])
            scores.append(score)
            class_ids.append(class_id)
        results = []
        if boxes:
            indices = cv2.dnn.NMSBoxes(boxes, scores, self.conf_thresh, self.nms_thresh)
            if len(indices):
                for idx in np.asarray(indices).reshape(-1):
                    results.append({
                        "box": boxes[int(idx)],
                        "confidence": scores[int(idx)],
                        "class_id": class_ids[int(idx)],
                    })
        return results

    def detect_image(self, image, context=None):
        if image is None:
            return []
        tensor, h, w = self._preprocess(image)
        output = self.compiled_model([tensor])[self.output_layer]
        parsed = self._postprocess(output, h, w)
        detections = []
        annotated = image.copy()
        for item in parsed:
            x, y, bw, bh = item["box"]
            x1, y1 = max(0, x), max(0, y)
            x2, y2 = min(w, x + bw), min(h, y + bh)
            label = self.names.get(item["class_id"], "Class_{}".format(item["class_id"]))
            text = "{} {:.2f}".format(label, item["confidence"])
            detections.append(((x1, y1), (x2, y2), text))
            cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(annotated, text, (x1, max(20, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        cv2.imwrite(str(self.save_dir / "detect_{}.jpg".format(stamp)), annotated)
        if self.api and context:
            self.api.log_detection(annotated, detections, context)
        return detections
