import datetime
from pathlib import Path
import cv2
import numpy as np
import openvino as ov
import yaml
import base64
import asyncio


class Detector:

  def __init__(self, model_dir, save_dir, conf=0.5, device="CPU",api=None):
    self.conf_thresh = conf
    self.nms_thresh = 0.45
    self.device = device.upper()
    self.save_dir = Path(save_dir)
    self.save_dir.mkdir(parents=True, exist_ok=True)
    model_dir_path = Path(model_dir)
    self.api=api
    if model_dir_path.is_dir():
      xml_files = list(model_dir_path.glob("*.xml"))
      if not xml_files:
        raise FileNotFoundError(
            f"model not found : {model_dir_path}"
        )
      model_path = str(xml_files[0])
    else:
      model_path = str(model_dir_path)

    
    self.core = ov.Core()
    self.model = self.core.read_model(model=model_path)
    # load model
    
    try:
      self.compiled_model = self.core.compile_model(
          model=self.model, device_name=self.device
      )
    except Exception as e:
      self.device = 'CPU'
      self.compiled_model = self.core.compile_model(
        model=self.model, device_name= self.device
      )

    self.input_layer = self.compiled_model.input(0)
    self.output_layer = self.compiled_model.output(0)


    _, _, self.img_h, self.img_w = self.input_layer.shape

    self.names = self._load_class_name(model_dir)
    print(
        f" (Input Size: {self.img_w}x{self.img_h} )"
        f" {self.device})"
    )
  def _load_class_name(self, model_dir_part):
    yaml_path = Path(model_dir_part) / "metadata.yaml"

    if yaml_path.exists():
        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if "names" in data:
                return {
                    int(k): str(v)
                    for k, v in data["names"].items()
                }

            if "name" in data:
                return {
                    int(k): str(v)
                    for k, v in data["name"].items()
                }

        except Exception as e:
            print(f"metadata.yaml error: {e}")

    print("metadata.yaml not found, using class IDs")
    return {}



  def resize(
      self,
      img: np.ndarray,
      new_shape=(640, 640),
      color=(114, 114, 114),
      auto=False,
      scaleFill=False,
      scaleup=True,
      stride=32,
  ):
 
    h_orig, w_orig = img.shape[:2]
    if isinstance(new_shape, int):
      new_shape = (new_shape, new_shape)

    img_resized = cv2.resize(
        img, (new_shape[1], new_shape[0]), interpolation=cv2.INTER_LINEAR
    )

    r_x = new_shape[1] / w_orig
    r_y = new_shape[0] / h_orig

    pad_w, pad_h = 0.0, 0.0

    return img_resized, (r_x, r_y), (pad_w, pad_h)
  def preprocess(self, image: np.ndarray):
    h_orig, w_orig = image.shape[:2]

    img_resize, ratio, (pad_w, pad_h) = self.resize(
        image, new_shape=(self.img_h, self.img_w)
    )
    # cv2.imshow("YOLO12 OpenVINO Debug", img_letterboxed)
    # cv2.waitKey(0)
    
    input_tensor = (
        np.expand_dims(img_resize.transpose(2, 0, 1), axis=0).astype(np.float32)
        / 255.0
    )

    return input_tensor, h_orig, w_orig, ratio, (pad_w, pad_h)

  def postprocess(self, outputs, h_orig, w_orig, ratio, pad):
    predictions = np.squeeze(outputs)  # Shape: (4 + num_classes, 8400)

    if predictions.shape[0] < predictions.shape[1]:
      predictions = predictions.T

    boxes, confidences, class_ids = [], [], []
    r_x, r_y = ratio
    pad_w, pad_h = pad

    for pred in predictions:
      scores = pred[4:]  # Class confidence scores
      class_id = np.argmax(scores)
      confidence = scores[class_id]

      if confidence >= self.conf_thresh:
        cx, cy, w, h = pred[0], pred[1], pred[2], pred[3]
        
        cx_orig = (cx - pad_w) / r_x
        cy_orig = (cy - pad_h) / r_y
        w_orig_box = w / r_x
        h_orig_box = h / r_y

        left = int(cx_orig - 0.5 * w_orig_box)
        top = int(cy_orig - 0.5 * h_orig_box)
        width = int(w_orig_box)
        height = int(h_orig_box)

        boxes.append([left, top, width, height])
        confidences.append(float(confidence))
        class_ids.append(int(class_id))

    boxes = np.array(boxes)
    confidences = np.array(confidences)
    class_ids = np.array(class_ids)
    results = []
    if len(boxes) > 0:
      indices = cv2.dnn.NMSBoxes(
          boxes.tolist(), confidences.tolist(), self.conf_thresh, self.nms_thresh
      .tolist() if hasattr(self.nms_thresh, 'tolist') else self.nms_thresh
      )

      if len(indices) > 0:
        for i in indices.flatten():
          results.append({
              "box": boxes[i].tolist(),
              "confidence": float(confidences[i]),
              "class_id": int(class_ids[i]),
          })
          
    return results
  
  def detect_image(self, image: np.ndarray, timestamp=None, json_safe=False):
    if image is None:
      return []

    annotated = image.copy()


    input_tensor, h_orig, w_orig, ratio, pad = self.preprocess(image)


    outputs = self.compiled_model([input_tensor])[self.output_layer]

 
    parsed_results = self.postprocess(outputs, h_orig, w_orig, ratio, pad)

    detections = []
    colors = [
        (255, 0, 0),
        (0, 255, 0),
        (0, 0, 255),
        (100, 255, 0),
        (100, 0, 255),
        (0, 100, 255),
        (128, 0, 255),
        (255, 128, 0),
        (128, 128, 128),
        (128, 0, 128),
    ]

    for item in parsed_results:
        left, top, width, height = item["box"]

        x1, y1 = max(0, left), max(0, top)
        x2, y2 = min(w_orig, left + width), min(h_orig, top + height)

        conf = round(item["confidence"], 2)
        cls_id = item["class_id"]

        class_name = self.names.get(cls_id, f"Class_{cls_id}")
        label_str = f"{class_name} {conf}"

        detections.append(((x1, y1), (x2, y2), label_str))

        color = colors[cls_id % len(colors)]

        # Bounding box
        cv2.rectangle(
            annotated,
            (x1, y1),
            (x2, y2),
            color,
            2
        )

        # Get text size
        (text_w, text_h), baseline = cv2.getTextSize(
            label_str,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            2
        )

        # Text background rectangle
        cv2.rectangle(
            annotated,
            (x1, max(0, y1 - text_h - 10)),
            (x1 + text_w, y1),
            color,
            -1
        )

        # Text
        cv2.putText(
            annotated,
            label_str,
            (x1, max(y1 - 5, text_h)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2
        )


    safe_timestamp = (
        timestamp.replace(":", "-").replace("T", "_")
        if timestamp
        else datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    )
    save_name = f"detect_{safe_timestamp}.jpg"
    save_path = self.save_dir / save_name
    cv2.imwrite(str(save_path), annotated)
    img = self.imagebase64encode(frame=annotated,quality=80)

    if json_safe:
      detections = [
          [[int(x1), int(y1)], [int(x2), int(y2)], str(label_str)]
          for ((x1, y1), (x2, y2), label_str) in detections
      ]
    try:
      asyncio.run(self.api.newAlarm(img,str(detections)))
    except Exception:
      print('Failed Send image')
    return {"result":detections}
  
  def imagebase64encode(self,frame,quality=80):
    if frame is None:
      return ''
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY),quality]
    success,buffer = cv2.imencode('.jpg',frame,encode_param)
    if not success:
      raise ValueError('Faild to endode frame to JPEG')
    b64_str = base64.b64encode(buffer).decode('utf-8')
    return b64_str

if __name__ == "__main__":
  model_path = r"Yolov12best_bg_v2_openvino_model"
  save_dir = r"saved_images"
  image_path = r"D:\BG\model\test\NA5.bmp"

  image = cv2.imread(image_path, cv2.IMREAD_COLOR)
  image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
  if image is not None:
    t = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")

    detector = Detector(
        model_dir=model_path, save_dir=save_dir, conf=0.7, device="CPU"
    )

    res = detector.detect_image(image, t)
    print("Normal Detection:", res)
  else:
    print(f"No image path: {image_path}")