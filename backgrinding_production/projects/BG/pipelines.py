BG_PIPELINES = {
    "backgrinding": {
        "mode": "shared",
        "steps": [
            {"id": "capture", "type": "capture"},
            {"id": "detect", "type": "detect"},
            {"id": "validate", "type": "validate"},
            {"id": "decision", "type": "decision"},
        ],
    },
    "stream_only": {
        "mode": "shared",
        "steps": [{"id": "stream", "type": "stream_only"}],
    },
}
