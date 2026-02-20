# shared_contracts/task_schemas.py — ADR-057 §2.9
# JSON Schemas for cross-service Celery task payloads.
# Both sender and receiver validate against these schemas.
#
# Usage:
#   from shared_contracts.task_schemas import TASK_SCHEMAS
#   import jsonschema
#   jsonschema.validate(payload, TASK_SCHEMAS["task_name"])

TASK_SCHEMAS: dict = {
    # Template — replace with actual task schemas per service
    # "generate_zone_report": {
    #     "type": "object",
    #     "required": ["assessment_id", "zone_ids", "requested_by"],
    #     "properties": {
    #         "assessment_id": {"type": "integer"},
    #         "zone_ids": {"type": "array", "items": {"type": "integer"}},
    #         "requested_by": {"type": "string", "format": "email"},
    #     },
    #     "additionalProperties": False,
    # },
}
