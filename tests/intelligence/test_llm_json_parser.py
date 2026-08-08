from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.v2.intelligence.llm_json_parser import (
    LlmJsonValidationError,
    parse_llm_json_object,
    require_string,
    require_string_list,
)


class LlmJsonParserTests(unittest.TestCase):
    def test_parses_plain_json_object(self) -> None:
        payload = parse_llm_json_object(
            '{"summary": "Stable session", "tokens": ["BTC"]}'
        )

        self.assertEqual(payload["summary"], "Stable session")
        self.assertEqual(payload["tokens"], ["BTC"])

    def test_parses_json_markdown_fence(self) -> None:
        payload = parse_llm_json_object(
            '```json\n{"summary": "Stable session"}\n```'
        )

        self.assertEqual(payload["summary"], "Stable session")

    def test_rejects_python_dictionary_literal(self) -> None:
        with self.assertRaises(LlmJsonValidationError):
            parse_llm_json_object(
                "{'summary': 'This is Python, not JSON'}"
            )

    def test_rejects_json_array(self) -> None:
        with self.assertRaises(LlmJsonValidationError):
            parse_llm_json_object('["not", "an", "object"]')

    def test_rejects_malformed_fence(self) -> None:
        with self.assertRaises(LlmJsonValidationError):
            parse_llm_json_object(
                '```json\n{"summary": "missing closing fence"}'
            )

    def test_rejects_executable_python_without_running_it(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "eval_was_executed"

            malicious = (
                "__import__('pathlib').Path("
                f"{str(marker)!r}"
                ").write_text('unsafe')"
            )

            with self.assertRaises(LlmJsonValidationError):
                parse_llm_json_object(malicious)

            self.assertFalse(marker.exists())

    def test_require_string_rejects_empty_value(self) -> None:
        with self.assertRaises(LlmJsonValidationError):
            require_string({"summary": "   "}, "summary")

    def test_require_string_list_validates_item_limit(self) -> None:
        with self.assertRaises(LlmJsonValidationError):
            require_string_list(
                {"points": ["one", "two", "three", "four"]},
                "points",
                max_items=3,
            )


if __name__ == "__main__":
    unittest.main()
