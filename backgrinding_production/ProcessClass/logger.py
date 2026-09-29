from ProcessClass.pathProcess import PathProcess, StatusLevel
import os
import datetime

class Logger:
    def __init__(self):
        # self.MQ = mq
        self.log_dir = PathProcess.logPath
        os.makedirs(self.log_dir, exist_ok=True)

    def cleanup_old_logs(self, days=180):
        try:
            now = datetime.datetime.now()
            for filename in os.listdir(self.log_dir):
                file_path = os.path.join(self.log_dir, filename)
                if not os.path.isfile(file_path):
                    continue
                mtime = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
                if (now - mtime).days > days:
                    os.remove(file_path)
                    print(f"[LOG CLEANUP] Deleted old log: {filename}")
        except Exception as e:
            print(f"[LOG CLEANUP ERROR] {e}")

    def logStatusUpdate(self, msg, statusLevel=StatusLevel.INFO):
        try:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_text = f"{timestamp} [{statusLevel.name}] {msg}"

            log_filename = os.path.join(
                self.log_dir,
                f"log_{datetime.datetime.now().strftime('%Y-%m-%d')}.txt"
            )
            with open(log_filename, "a", encoding="utf-8") as f:
                f.write(log_text + "\n")

            return log_text
        except Exception as e:
            print(f"[Logger Error] {e}")
            e_text = f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} [ERROR] Logger Error: {e}"
            return e_text
