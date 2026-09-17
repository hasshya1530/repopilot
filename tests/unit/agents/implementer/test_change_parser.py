import pytest

from agents.implementer.change_parser import parse_implementation_result
from agents.implementer.errors import ChangeParsingError
from agents.implementer.models import ChangeOperation


def test_parse_valid_implementation_result() -> None:
    result = parse_implementation_result(
        """
{
  "summary": "Improve authentication validation.",
  "changes": [
    {
      "file_path": "auth.py",
      "operation": "modify",
      "content": "def validate_token(token):\\n    return token == \\"valid\\"\\n",
      "reason": "Update token validation."
    }
  ]
}
"""
    )

    assert result.summary == "Improve authentication validation."
    assert len(result.changes) == 1

    change = result.changes[0]

    assert change.file_path == "auth.py"
    assert change.operation is ChangeOperation.MODIFY
    assert change.content.startswith("def validate_token")
    assert change.reason == "Update token validation."


def test_parse_json_code_fence() -> None:
    result = parse_implementation_result(
        '```json\n'
        '{\n'
        '  "summary": "Create a test.",\n'
        '  "changes": [\n'
        '    {\n'
        '      "file_path": "tests/test_auth.py",\n'
        '      "operation": "create",\n'
        '      "content": "def test_auth():\\\\n    assert True\\\\n",\n'
        '      "reason": "Add regression coverage."\n'
        '    }\n'
        '  ]\n'
        '}\n'
        '```'
    )

    assert result.summary == "Create a test."
    assert len(result.changes) == 1
    assert result.changes[0].file_path == "tests/test_auth.py"
    assert result.changes[0].operation is ChangeOperation.CREATE
    assert result.changes[0].reason == "Add regression coverage."


def test_delete_requires_empty_content() -> None:
    with pytest.raises(ChangeParsingError, match="Delete change"):
        parse_implementation_result(
            """
{
  "summary": "Delete obsolete code.",
  "changes": [
    {
      "file_path": "old.py",
      "operation": "delete",
      "content": "print('bad')",
      "reason": "Remove obsolete code."
    }
  ]
}
"""
        )


def test_rejects_path_traversal() -> None:
    with pytest.raises(ChangeParsingError, match="path traversal"):
        parse_implementation_result(
            """
{
  "summary": "Modify a file.",
  "changes": [
    {
      "file_path": "../secret.py",
      "operation": "modify",
      "content": "bad",
      "reason": "Bad change."
    }
  ]
}
"""
        )


def test_rejects_absolute_path() -> None:
    with pytest.raises(ChangeParsingError, match="absolute file path"):
        parse_implementation_result(
            """
{
  "summary": "Modify a file.",
  "changes": [
    {
      "file_path": "/tmp/secret.py",
      "operation": "modify",
      "content": "bad",
      "reason": "Bad change."
    }
  ]
}
"""
        )


def test_requires_at_least_one_change() -> None:
    with pytest.raises(ChangeParsingError, match="at least one code change"):
        parse_implementation_result(
            """
{
  "summary": "Nothing changed.",
  "changes": []
}
"""
        )
