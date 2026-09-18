import csv
import requests
import json
import os

class ChecklistData:
        def __init__(self, use_server=False, csv_path="datalist.csv") -> None:
            self.use_server = use_server
            self.csv_path = f"{csv_path}/datalist.csv"
            self.serverPath = "http://10.151.27.1:8082/Backgrinding_checklist"

        def getChecklistData(self, handle):
            if self.use_server:
                return self._get_from_server(handle)
            else:
                return self._get_from_csv(handle)

        def _get_from_server(self, handle):
            try:
                url = f"{self.serverPath}/{handle}"
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    return json.loads(response.text)
                else:
                    print(f"⚠️ Server returned {response.status_code}: {url}")
                    return None
            except Exception as e:
                print(f"❌ Error connecting to server: {e}")
                return None

        def _get_from_csv(self, handle):
            results = {handle: []}

            if not os.path.exists(self.csv_path):
                print(f"❌ CSV file not found: {self.csv_path}")
                return None

            try:
                with open(self.csv_path, mode="r", newline="", encoding="utf-8") as csvfile:
                    reader = csv.DictReader(csvfile)
                    for row in reader:
                        # Match by HANDLE_TYPE and only ACTIVEFLAG == 1
                        if row["HANDLE_TYPE"].strip() == handle and row["ACTIVEFLAG"].strip() == "1":
                            results[handle].append({
                                "LEFT_CASSETE": row["LEFT_CASSETE"].strip(),
                                "RIGHT_CASSETE": row["RIGHT_CASSETE"].strip()
                            })
            except Exception as e:
                print(f"⚠️ Error reading CSV: {e}")
                return None

            if len(results[handle]) > 0:
                return results
            else:
                print(f"⚠️ No matching handle found for '{handle}' in CSV.")
                return None


if __name__ == "__main__":
    use_server = False  # ✅ False = ใช้ CSV, True = ดึงจาก server
    csv_path = r"D:\fern\project_Fern\Backgrinding_utl1\Backgrinding_machine\config"

    proc = ChecklistData(use_server=use_server, csv_path=csv_path)
    # listhandle = ['handle_small', 'whitebox', 'black_6']
    listhandle = ['Cshape', 'DSC8inch', 'STD8inch']
    handle = listhandle[0]

    res = proc.getChecklistData(handle)
    if res is not None:
        data = res[handle]
        print(f"\n✅ Found {len(data)} checklist rows for {handle}:")
        for i, j in enumerate(data):
            print(f"{i+1}. LEFT={j['LEFT_CASSETE']}, RIGHT={j['RIGHT_CASSETE']}")
    else:
        print("⚠️ No data found.")