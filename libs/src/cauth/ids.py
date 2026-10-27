import uuid

_ROOT = uuid.UUID("6ba7b811-9dad-11d1-80b4-00c04fd430c8")  # RFC 4122 URL namespace


def deterministic_uuid(audience: str, source_id) -> uuid.UUID:
    """UUIDv5 of source_id inside a namespace derived from audience."""
    namespace = uuid.uuid5(_ROOT, audience)
    return uuid.uuid5(namespace, str(source_id))
