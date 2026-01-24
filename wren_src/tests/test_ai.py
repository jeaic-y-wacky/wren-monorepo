"""
Tests for wren.ai module.

Tests the AI interface, particularly the extract() method which now
requires explicit types (no more silent fallback to DynamicObject).
"""

import pytest
from unittest.mock import patch, MagicMock
from dataclasses import dataclass
from pydantic import BaseModel

from wren.ai import AI, ai
from wren.errors import TypeInferenceError


class BookingModel(BaseModel):
    """Test Pydantic model."""
    name: str
    guests: int


@dataclass
class BookingDataclass:
    """Test dataclass."""
    name: str
    guests: int


class TestExtractRequiresType:
    """Tests for extract() requiring explicit types."""

    def test_extract_raises_without_type(self):
        """extract() should raise TypeInferenceError when no type specified."""
        ai_instance = AI()

        with pytest.raises(TypeInferenceError) as exc_info:
            ai_instance.extract("some text")

        assert "No target type specified" in str(exc_info.value)
        assert "Type hint" in str(exc_info.value)

    def test_extract_raises_for_basic_types(self):
        """extract() should raise for non-structured types like dict, str."""
        ai_instance = AI()

        with pytest.raises(TypeInferenceError) as exc_info:
            ai_instance.extract("some text", dict)

        assert "Cannot extract to type" in str(exc_info.value)
        assert "Pydantic BaseModel or dataclass" in str(exc_info.value)

    def test_extract_raises_for_list(self):
        """extract() should raise for list type."""
        ai_instance = AI()

        with pytest.raises(TypeInferenceError) as exc_info:
            ai_instance.extract("some text", list)

        assert "Cannot extract to type" in str(exc_info.value)


class TestExtractWithPydantic:
    """Tests for extract() with Pydantic models."""

    @patch.object(AI, '_complete')
    def test_extract_with_pydantic_model(self, mock_complete):
        """extract() should work with Pydantic models."""
        mock_complete.return_value = '{"name": "Alice", "guests": 4}'

        ai_instance = AI()
        result = ai_instance.extract("Book for Alice, 4 guests", BookingModel)

        assert isinstance(result, BookingModel)
        assert result.name == "Alice"
        assert result.guests == 4

    @patch.object(AI, '_complete')
    def test_extract_pydantic_includes_schema_in_prompt(self, mock_complete):
        """extract() should include Pydantic schema in the prompt."""
        mock_complete.return_value = '{"name": "Bob", "guests": 2}'

        ai_instance = AI()
        ai_instance.extract("Book for Bob", BookingModel)

        # Check that the prompt included schema info
        call_args = mock_complete.call_args[0][0]
        assert "Schema" in call_args
        assert "name" in call_args
        assert "guests" in call_args


class TestExtractWithDataclass:
    """Tests for extract() with dataclasses."""

    @patch.object(AI, '_complete')
    def test_extract_with_dataclass(self, mock_complete):
        """extract() should work with dataclasses."""
        mock_complete.return_value = '{"name": "Charlie", "guests": 3}'

        ai_instance = AI()
        result = ai_instance.extract("Book for Charlie, 3 guests", BookingDataclass)

        assert isinstance(result, BookingDataclass)
        assert result.name == "Charlie"
        assert result.guests == 3

    @patch.object(AI, '_complete')
    def test_extract_dataclass_includes_fields_in_prompt(self, mock_complete):
        """extract() should include dataclass fields in the prompt."""
        mock_complete.return_value = '{"name": "Dana", "guests": 1}'

        ai_instance = AI()
        ai_instance.extract("Book for Dana", BookingDataclass)

        # Check that the prompt included field info
        call_args = mock_complete.call_args[0][0]
        assert "Fields" in call_args
        assert "name" in call_args
        assert "guests" in call_args


class TestExtractJsonParsing:
    """Tests for JSON parsing in extract()."""

    @patch.object(AI, '_complete')
    def test_extract_handles_json_in_markdown(self, mock_complete):
        """extract() should handle JSON wrapped in markdown code blocks."""
        mock_complete.return_value = '```json\n{"name": "Eve", "guests": 5}\n```'

        ai_instance = AI()
        # This should extract the JSON from within the response
        result = ai_instance.extract("Book for Eve", BookingModel)

        assert result.name == "Eve"
        assert result.guests == 5

    @patch.object(AI, '_complete')
    def test_extract_raises_on_invalid_json(self, mock_complete):
        """extract() should raise TypeInferenceError on invalid JSON."""
        mock_complete.return_value = 'This is not JSON at all'

        ai_instance = AI()

        with pytest.raises(TypeInferenceError) as exc_info:
            ai_instance.extract("some text", BookingModel)

        assert "Failed to parse" in str(exc_info.value)


class TestGlobalAiInstance:
    """Tests for the global ai instance."""

    def test_global_ai_exists(self):
        """Global ai instance should exist."""
        assert ai is not None
        assert isinstance(ai, AI)

    def test_extract_on_global_requires_type(self):
        """Global ai.extract() should also require type."""
        with pytest.raises(TypeInferenceError):
            ai.extract("some text")
