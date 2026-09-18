# Edge Platform Architecture

## Core vs Project

The Edge runtime owns reusable infrastructure:

- camera lifecycle and health
- inspection cycle context
- pipeline execution
- IO/communication boundaries
- logging and device health

The project owns:

- program status names
- camera definitions and hardware mapping
- IO names/channels
- pipeline definitions and project rules

## Pipeline model

A cycle creates one `cycle_id`. A pipeline can use one or many cameras.

```text
Trigger
  -> Pipeline
       -> capture camera(s)
       -> AI/OCR/processing
       -> project validation
       -> decision
  -> final result
```

Each camera can point to a different pipeline. A pipeline may also be shared by multiple cameras.

## Configuration example

```json
{
  "cameras": [
    {"id": "cam_1", "hardware_index": 0, "pipeline": "inspection"},
    {"id": "cam_2", "hardware_index": 1, "pipeline": "stream_only"}
  ],
  "pipelines": {
    "inspection": {
      "mode": "shared",
      "steps": ["capture", "detect", "validate", "decision"]
    }
  }
}
```

The platform core must not contain BackGrinding-specific state names, IO meanings, camera counts, or business rules.
