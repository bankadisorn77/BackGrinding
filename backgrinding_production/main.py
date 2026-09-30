import logging

from platform_core.runtime import PlatformRuntime
from projects.BG.project import BackGrindingProject

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s]: %(message)s",
    datefmt="%H:%M:%S",
)


def main():
    project = BackGrindingProject()
    runtime = PlatformRuntime(project=project)
    try:
        runtime.start(
            width=project.config.width,
            height=project.config.height,
        )
        runtime.run()
    except KeyboardInterrupt:
        logging.getLogger("MAIN").info("Stopping system by user.")
    finally:
        runtime.stop()


if __name__ == "__main__":
    main()
