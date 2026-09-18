from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from .context import InspectionContext


class PipelineEngine:
    """Generic sequential pipeline runner (Python 3.6 compatible)."""

    def __init__(self, handlers: Optional[Dict[str, Callable]] = None):
        self.handlers = dict(handlers or {})

    def register(self, step_type: str, handler: Callable):
        self.handlers[step_type] = handler

    def run(
        self,
        definition: Dict[str, Any],
        context: InspectionContext,
        camera_ids: Optional[List[str]] = None,
    ) -> InspectionContext:
        mode = definition.get("mode", "shared")
        targets = camera_ids or definition.get("cameras") or []

        if mode == "per_camera":
            for camera_id in targets:
                camera_context = context.for_camera(camera_id)
                self._run_steps(definition.get("steps", []), camera_context)
        else:
            self._run_steps(definition.get("steps", []), context)

        return context

    def _run_steps(self, steps, context: InspectionContext):
        for step in steps:
            if isinstance(step, str):
                step = {"type": step}
            if not isinstance(step, dict):
                continue

            step_type = step.get("type")
            if not step_type:
                continue

            handler = self.handlers.get(step_type)
            if handler is None:
                raise KeyError("Unknown pipeline step: {}".format(step_type))

            result = handler(context, step)
            if result is not None:
                step_id = step.get("id") or step_type
                context.metadata.setdefault("steps", {})[step_id] = result
