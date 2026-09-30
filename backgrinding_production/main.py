# main.py
import logging
import time
from platform_core.runtime import PlatformRuntime
from projects.SFS.project import SfsPokaYokeProject

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s]: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("MAIN")

def main():
    # 1. สร้าง Project และ Runtime
    project = SfsPokaYokeProject()
    runtime = PlatformRuntime(project=project)

    # 2. เริ่มต้นระบบ (กล้องทั้ง 3 ตัวเข้า Standby Mode และตามด้วยต่อ IO)
    logger.info("Starting PlatformRuntime...")
    runtime.start(width=1920, height=1080)

    # กำหนดหมายเลข Channel
    INPUT_TRIGGER_CH = 0   # รับสัญญาณ Trigger ถ่ายภาพที่ Channel 1
    OUTPUT_RELAY_CH = 1    # ส่งผล Pass ออก Relay Channel 1
    OUTPUT_ALARM_CH = 0    # ส่งผล Fail ออก Alarm Channel 0

    # กำหนด ID ของกล้องทั้ง 3 ตัวที่จะสั่งถ่ายพร้อมกัน
    TARGET_CAMERAS = ["cam_1", "cam_2", "cam_3"]

    logger.info("=" * 55)
    logger.info(f"System ready! Waiting for trigger on DI Channel {INPUT_TRIGGER_CH}...")
    logger.info(f"Target cameras for capture: {TARGET_CAMERAS}")
    logger.info("=" * 55)

    last_trigger_state = 0

    try:
        while True:
            # อ่านค่าสถานะจาก Digital Input Channel 1 (0 หรือ 1)
            current_trigger = runtime.io_manager.read_input(channel=INPUT_TRIGGER_CH)

            # ตรวจจับจังหวะ Rising Edge (0 -> 1) เมื่อมีสัญญาณกระตุ้นเข้ามา
            if current_trigger == 1 and last_trigger_state == 0:
                logger.info(f">>> [TRIGGER RECEIVED] on DI Ch {INPUT_TRIGGER_CH}! Triggering 3 cameras... <<<")
                start_time = time.time()

                # รันรอบตรวจสอบ โดยระบุ cam_active ให้ถ่ายภาพกล้องทั้ง 3 ตัวพร้อมกัน
                context = runtime.run_cycle(
                    pipeline_id="sfs_pokayoke",
                    cam_active=TARGET_CAMERAS
                )

                elapsed = (time.time() - start_time) * 1000
                logger.info(f"Capture & Process completed in {elapsed:.1f} ms")

                # ตรวจสอบจำนวนภาพที่จับได้จริงจากกล้องแต่ละตัว
                captured_cams = list(context.frames.keys())
                logger.info(f"Captured frames from: {captured_cams} (Total: {len(captured_cams)}/3)")

                # ดึงผลการตรวจ
                is_pass = context.results.get("final", False)
                logger.info(f"Inspection Result: {'PASS' if is_pass else 'FAIL'}")

                # สั่งงาน Output ตามผลลัพธ์
                if is_pass:
                    runtime.io_manager.write_output(channel=OUTPUT_RELAY_CH, value=True)
                    runtime.io_manager.write_output(channel=OUTPUT_ALARM_CH, value=False)
                    time.sleep(0.3)
                    runtime.io_manager.write_output(channel=OUTPUT_RELAY_CH, value=False)
                else:
                    runtime.io_manager.write_output(channel=OUTPUT_ALARM_CH, value=True)

            last_trigger_state = current_trigger
            time.sleep(0.01)  # หน่วงเวลาสั้นๆ ป้องกัน CPU ทำงาน 100%

    except KeyboardInterrupt:
        logger.info("Stopping system by user (Ctrl+C)...")
    finally:
        runtime.stop()
        logger.info("Platform stopped cleanly.")

if __name__ == "__main__":
    main()