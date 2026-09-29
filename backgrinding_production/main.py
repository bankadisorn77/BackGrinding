# main.py
import logging
import cv2 as cv
from platform_core.runtime import PlatformRuntime
from project.project import BackGrindingProject
from ProcessClass.detector import Detector
from ProcessClass.logicAnalysis import Analysis
from ProcessClass.BGconfig import BackgrindConfig
from ProcessClass.serverAPI import API_CALL

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("MAIN")

def main():
    logger.info("Initializing BackGrinding Project with Camera...")
    config = BackgrindConfig()
    api = API_CALL(config=config)
    detector = Detector(
        model_dir=config.model_path,
        save_dir=config.save_image_path,
        conf=0.7,
        api=api,
    )
    analysis = Analysis()

    # 1. โหลด config กล้อง
    try:
        config.loadConfig()
    except Exception as e:
        logger.warning(f"Load config warning: {e}")

    # 2. สร้าง Project และ Runtime (Runtime จะสร้าง CameraManager ผ่าน from_definitions ให้อัตโนมัติ)
    project = BackGrindingProject(
    detector=detector,
    analysis=analysis,
    config=config
)
    runtime = PlatformRuntime(project=project)

    # 3. สั่ง Start (เชื่อมต่อกล้องจริง)
    aoi = getattr(config, "cameraAOI", {})
    width = aoi.get("width", 1920)
    height = aoi.get("height", 1080)
    
    logger.info(f"Connecting cameras (Resolution: {width}x{height})...")
    runtime.start(width=width, height=height)

    # 4. ทดสอบจับภาพจริง 1 รอบ
    logger.info("Testing run_cycle capture...")
    context = runtime.run_cycle(pipeline_id="backgrinding")

    # 5. ตรวจสอบภาพที่ได้
    logger.info(f"Cycle ID: {context.cycle_id}")
    for cam_id, frame in context.frames.items():
        if frame is not None:
            logger.info(f">>> Successfully captured [{cam_id}] - Frame shape: {frame.shape} <<<")
            cv.imwrite(f"test_{cam_id}.jpg", frame)
            logger.info(f"Saved test image to test_{cam_id}.jpg")
        else:
            logger.warning(f"Frame from [{cam_id}] is None!")

    # 6. ปิดการเชื่อมต่อ
    runtime.stop()
    logger.info("Platform stopped cleanly.")

if __name__ == "__main__":
    main()