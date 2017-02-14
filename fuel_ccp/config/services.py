SCHEMA = {
    "services": {
        "type": "object",
        "additionalProperties": {
            "type": "object",
            "additionalProperties": False,
            "required": ["service_def"],
            "properties": {
                "service_def": {"type": "string"},
                "mapping": {"type": "object"},
            }
        }
    }
}
DEFAULTS = {
    "services": {},
}
