"""Unit tests for renderer filters."""

import pytest

from chronicle.renderers.filters import (
    NEGATIVE_PATTERNS,
    is_empty_section,
    replace_negative_assertions,
)


class TestReplaceNegativeAssertions:
    """Tests for replace_negative_assertions filter.

    The filter REMOVES lines with negative assertions rather than replacing with N/A.
    Empty result means all content was negative assertions.
    """

    def test_removes_not_detected(self) -> None:
        """Test removing 'not detected' pattern."""
        text = "*No frameworks not detected.*"
        result = replace_negative_assertions(text)
        assert result == ""

    def test_removes_not_found(self) -> None:
        """Test removing 'not found' pattern."""
        text = "*Dependencies not found.*"
        result = replace_negative_assertions(text)
        assert result == ""

    def test_removes_unable_to_determine(self) -> None:
        """Test removing 'unable to determine' pattern."""
        text = "*Unable to determine the framework.*"
        result = replace_negative_assertions(text)
        assert result == ""

    def test_removes_none_identified(self) -> None:
        """Test removing 'none identified' pattern."""
        text = "*None identified in the codebase.*"
        result = replace_negative_assertions(text)
        assert result == ""

    def test_removes_no_x_detected(self) -> None:
        """Test removing 'no X detected' pattern."""
        text = "*No dependencies detected.*"
        result = replace_negative_assertions(text)
        assert result == ""

    def test_removes_could_not_find(self) -> None:
        """Test removing 'could not find' pattern."""
        text = "*Could not find any configuration.*"
        result = replace_negative_assertions(text)
        assert result == ""

    def test_preserves_valid_content(self) -> None:
        """Test that valid content is preserved."""
        text = "The system uses Python 3.11 with FastAPI framework."
        result = replace_negative_assertions(text)
        assert result == text

    def test_preserves_multiline_valid_content(self) -> None:
        """Test that multiline valid content is preserved."""
        text = """This codebase is a CLI tool.
It uses Python 3.11.
The main entry point is in cli.py."""
        result = replace_negative_assertions(text)
        assert result == text

    def test_empty_string_returns_empty(self) -> None:
        """Test that empty string returns empty string."""
        assert replace_negative_assertions("") == ""
        assert replace_negative_assertions("   ") == ""

    def test_whitespace_only_returns_empty(self) -> None:
        """Test that whitespace-only input returns empty string."""
        assert replace_negative_assertions("") == ""

    def test_handles_mixed_content(self) -> None:
        """Test content with both valid and negative assertions."""
        text = """The system uses Python 3.11.
*No security patterns detected.*
The main framework is FastAPI."""
        result = replace_negative_assertions(text)
        assert "Python 3.11" in result
        assert "FastAPI" in result
        assert "not detected" not in result.lower()

    def test_removes_all_negative_assertions(self) -> None:
        """Test that all negative assertion lines are removed."""
        text = """*Not found.*
*Not detected.*
*None identified.*"""
        result = replace_negative_assertions(text)
        # All lines should be removed
        assert result == ""

    def test_removes_italicized_negative_assertion(self) -> None:
        """Test removing italicized negative assertions (markdown style)."""
        text = "*No modules detected.*"
        result = replace_negative_assertions(text)
        assert result == ""

    def test_preserves_content_with_not_in_context(self) -> None:
        """Test that 'not' in proper context is preserved."""
        text = "This module is not responsible for authentication."
        result = replace_negative_assertions(text)
        # This is a long sentence with 'not' in proper context, should be preserved
        assert "not responsible" in result

    def test_removes_short_negative_lines(self) -> None:
        """Test that short lines with negative patterns are removed."""
        text = "Not found"
        result = replace_negative_assertions(text)
        assert result == ""


class TestIsEmptySection:
    """Tests for is_empty_section helper."""

    def test_empty_string(self) -> None:
        """Test that empty string is considered empty."""
        assert is_empty_section("") is True

    def test_whitespace_only(self) -> None:
        """Test that whitespace-only string is empty."""
        assert is_empty_section("   \n\t  ") is True

    def test_na_is_empty(self) -> None:
        """Test that N/A is considered empty."""
        assert is_empty_section("N/A") is True
        assert is_empty_section("n/a") is True
        assert is_empty_section("  N/A  ") is True

    def test_valid_content_not_empty(self) -> None:
        """Test that valid content is not empty."""
        assert is_empty_section("This is content") is False


class TestNegativePatterns:
    """Tests for negative patterns list."""

    def test_patterns_exist(self) -> None:
        """Test that patterns list is populated."""
        assert len(NEGATIVE_PATTERNS) > 0

    def test_common_patterns_included(self) -> None:
        """Test that common negative patterns are included."""
        patterns_str = " ".join(NEGATIVE_PATTERNS).lower()
        assert "not detected" in patterns_str
        assert "not found" in patterns_str
        assert "unable to determine" in patterns_str
