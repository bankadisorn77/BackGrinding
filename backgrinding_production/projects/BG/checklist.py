from __future__ import annotations

import csv
import json
from pathlib import Path


class Checklist:
    def __init__(self, csv_path=None, server_url=None):
        self.csv_path = Path(csv_path) if csv_path else None
        self.server_url = server_url

    def get(self, handle):
        if self.csv_path:
            result = self._from_csv(handle)
            if result is not None:
                return result
        return self._from_server(handle)

    def _from_csv(self, handle):
        if not self.csv_path.exists():
            return None
        rows = []
        try:
            with self.csv_path.open("r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("HANDLE_TYPE", "").strip() == handle and row.get("ACTIVEFLAG", "").strip() == "1":
                        rows.append({
                            "LEFT_CASSETE": row.get("LEFT_CASSETE", "").strip(),
                            "RIGHT_CASSETE": row.get("RIGHT_CASSETE", "").strip(),
                        })
            return rows or None
        except (OSError, csv.Error):
            return None

    def _from_server(self, handle):
        if not self.server_url:
            return None
        try:
            import requests
            response = requests.get(
                "{}/{}".format(self.server_url.rstrip("/"), handle), timeout=5
            )
            if response.status_code != 200:
                return None
            data = response.json()
            return data.get(handle) if isinstance(data, dict) else data
        except Exception:
            return None
