class BGLogic:
    """BackGrinding business rules. Hardware access stays outside this class."""

    AOI = (
        (485, 7, 2095, 865, "top"),
        (1, 280, 1240, 1944, "left"),
        (1375, 280, 2590, 1944, "right"),
    )

    def __init__(self, checklist):
        self.checklist = checklist

    @staticmethod
    def _intersection(a0, a1, b0, b1):
        if a0 >= b0 and a1 <= b1:
            return a1 - a0
        if a0 < b0 and a1 > b1:
            return b1 - b0
        if a0 < b0 < a1:
            return a1 - b0
        if a0 < b1 < a1:
            return b1 - a0
        return 0

    def _position(self, box):
        x0, y0 = box[0]
        x1, y1 = box[1]
        area = float((x1 - x0) * (y1 - y0))
        if area <= 0:
            return None
        for ax0, ay0, ax1, ay1, name in self.AOI:
            width = self._intersection(x0, x1, ax0, ax1)
            height = self._intersection(y0, y1, ay0, ay1)
            if width * height / area >= 0.65:
                return name
        return None

    def _normalize_detection(self, detection):
        # Detector output: ((x1,y1),(x2,y2),"class confidence")
        position = self._position(detection)
        label = str(detection[2]).split(" ", 1)[0]
        return position, label

    def evaluate(self, detections):
        if not isinstance(detections, (list, tuple)) or len(detections) != 3:
            return False, []

        mapped = []
        for item in detections:
            try:
                position, label = self._normalize_detection(item)
            except (IndexError, TypeError):
                return False, []
            if position is None:
                return False, []
            mapped.append((position, label))

        order = {"top": 0, "left": 1, "right": 2}
        if len({p for p, _ in mapped}) != 3:
            return False, mapped
        mapped.sort(key=lambda x: order.get(x[0], 99))
        labels = [label for _, label in mapped]
        handle = labels[0]

        rows = self.checklist.get(handle)
        if not rows:
            return False, []

        expected = [handle]
        for row in rows:
            expected_row = [
                handle,
                row.get("LEFT_CASSETE", ""),
                row.get("RIGHT_CASSETE", ""),
            ]
            if labels == expected_row:
                return True, expected_row
            expected = expected_row

        # Preserve the legacy "nobox" acceptance rule.
        if "nobox" in labels:
            return True, labels
        return False, expected
