import unittest

from platform_core import InspectionContext, PipelineEngine


class PipelineCoreTest(unittest.TestCase):

  def test_shared_pipeline_uses_cycle_context(self):
    seen = []

    def capture(context, step):
      seen.append((context.cycle_id, context.camera_id))
      return True

    engine = PipelineEngine({"capture": capture})
    context = InspectionContext("demo", "p1", "edge01", cycle_id="cycle-1", camera_id="cam_a")
    engine.run({"mode": "shared", "steps": [{"type": "capture"}]}, context)

    self.assertEqual(seen, [("cycle-1", "cam_a")])

  def test_per_camera_pipeline_reuses_one_cycle(self):
    seen = []

    def step(context, config):
      seen.append((context.cycle_id, context.camera_id))
      return True

    engine = PipelineEngine({"step": step})
    context = InspectionContext("demo", "p1", "edge01", cycle_id="cycle-2")
    engine.run(
        {
            "mode": "per_camera",
            "cameras": ["cam_a", "cam_b"],
            "steps": [{"type": "step"}],
        },
        context,
    )

    self.assertEqual(
        seen,
        [("cycle-2", "cam_a"), ("cycle-2", "cam_b")],
    )


if __name__ == "__main__":
  unittest.main()
