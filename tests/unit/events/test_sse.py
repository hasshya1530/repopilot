from apps.api.app.api.v1.events import parse_last_event_id


def test_parse_missing_last_event_id() -> None:
    assert parse_last_event_id(None) == "0-0"


def test_parse_empty_last_event_id() -> None:
    assert parse_last_event_id("") == "0-0"


def test_parse_valid_last_event_id() -> None:
    assert parse_last_event_id("123-4") == "123-4"


def test_parse_dollar_event_id() -> None:
    assert parse_last_event_id("$") == "$"


def test_parse_invalid_last_event_id() -> None:
    assert parse_last_event_id("invalid") == "0-0"


def test_parse_partial_event_id() -> None:
    assert parse_last_event_id("123") == "0-0"


def test_parse_event_id_with_whitespace() -> None:
    assert parse_last_event_id(" 123-4 ") == "123-4"
