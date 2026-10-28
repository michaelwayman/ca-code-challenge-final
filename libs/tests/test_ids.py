import uuid

from shared_auth import deterministic_uuid


def test_pinned_values():
    assert deterministic_uuid("wp_user", 1) == uuid.UUID("1fa2ae49-3568-5649-872f-96984fdeec39")
    assert deterministic_uuid("wp_user", 2) == uuid.UUID("0b49e386-5700-51ad-91de-e70869095fdc")


def test_namespaces_differ():
    assert deterministic_uuid("wp_user", 1) != deterministic_uuid("other", 1)


def test_stable_and_str_equivalent():
    assert deterministic_uuid("a", 7) == deterministic_uuid("a", "7")
