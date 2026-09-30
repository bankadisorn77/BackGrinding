# test_isolate.py
import multiprocessing as mp
import time
from platform_core.module.gpio.advantech import GPIO
from ProcessClass.ueyeCam import UeyeCamera

def run_gpio_test():
    gpio = GPIO()
    print("[Child Process] GPIO Connected:", gpio.is_connected)
    for i in range(5):
        ok = gpio.outputWrite(1, True)
        print(f"[Child Process] Write ON: {ok}")
        time.sleep(0.5)
        ok = gpio.outputWrite(1, False)
        print(f"[Child Process] Write OFF: {ok}")
        time.sleep(0.5)
    gpio.closeIO()

if __name__ == "__main__":
    # เริ่มกล้องใน Main Process
    cam = UeyeCamera(camera_id=0)
    cam.connection(1920, 1080)
    print("Camera running in main process...")
    time.sleep(1.0)

    # รัน GPIO ใน Process แยกขาดจากกัน
    p = mp.Process(target=run_gpio_test)
    p.start()
    p.join()

    cam.disconnect()