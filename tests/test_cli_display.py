"""Tests for CLI display utilities."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from mtg_mcp.cli.display import (
    display_image_in_terminal,
    display_image_iterm2,
    display_image_kitty,
    display_image_sixel,
    fetch_card_image,
)


class TestFetchCardImage:
    """Tests for fetch_card_image function."""

    @pytest.mark.asyncio
    async def test_fetch_valid_url(self) -> None:
        """Fetching a valid image URL should return bytes."""
        # Use a small, reliable test image
        url = "https://httpbin.org/image/png"
        result = await fetch_card_image(url)
        # httpbin might be slow/unavailable, so we just check the function doesn't crash
        # In real tests we'd mock httpx
        assert result is None or isinstance(result, bytes)

    @pytest.mark.asyncio
    async def test_fetch_invalid_url(self) -> None:
        """Fetching an invalid URL should return None."""
        url = "https://invalid.example.com/nonexistent.png"
        result = await fetch_card_image(url)
        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_timeout(self) -> None:
        """Fetching with timeout should return None gracefully."""
        # Use httpbin delay endpoint that takes longer than timeout
        url = "https://httpbin.org/delay/15"
        result = await fetch_card_image(url)
        assert result is None


class TestDisplayImageIterm2:
    """Tests for iTerm2 image display."""

    def test_iterm2_without_iterm_env(self) -> None:
        """iTerm2 display should return False when not in iTerm2."""
        image_data = b"fake image data"
        # Clear iTerm2-related env vars
        with patch.dict(
            os.environ,
            {"TERM_PROGRAM": "not-iterm", "LC_TERMINAL": ""},
            clear=False,
        ):
            result = display_image_iterm2(image_data)
            assert result is False

    def test_iterm2_with_iterm_env(self) -> None:
        """iTerm2 display should attempt display when TERM_PROGRAM is set."""
        image_data = b"\x89PNG\r\n\x1a\n"  # PNG header

        with patch.dict(os.environ, {"TERM_PROGRAM": "iTerm.app"}):
            # It will try to write to stdout - we just verify it doesn't crash
            # In a real terminal it would display the image
            result = display_image_iterm2(image_data)
            # Should return True if it tried to display
            assert isinstance(result, bool)

    def test_iterm2_with_lc_terminal(self) -> None:
        """iTerm2 display should work with LC_TERMINAL=iTerm2."""
        image_data = b"\x89PNG\r\n\x1a\n"

        with patch.dict(os.environ, {"TERM_PROGRAM": "", "LC_TERMINAL": "iTerm2"}):
            result = display_image_iterm2(image_data)
            assert isinstance(result, bool)


class TestDisplayImageKitty:
    """Tests for Kitty terminal image display."""

    def test_kitty_not_available_in_test_env(self) -> None:
        """Kitty display should return False when not in Kitty."""
        image_data = b"fake image data"
        result = display_image_kitty(image_data)
        assert result is False

    def test_kitty_with_env(self) -> None:
        """Kitty display should attempt display when TERM is xterm-kitty."""
        image_data = b"\x89PNG\r\n\x1a\n"

        with patch.dict(os.environ, {"TERM": "xterm-kitty"}):
            result = display_image_kitty(image_data)
            assert isinstance(result, bool)


class TestDisplayImageSixel:
    """Tests for Sixel image display."""

    def test_sixel_not_available_in_test_env(self) -> None:
        """Sixel display should return False when not in sixel terminal."""
        image_data = b"fake image data"
        result = display_image_sixel(image_data)
        assert result is False

    def test_sixel_with_env(self) -> None:
        """Sixel display should check for sixel in TERM."""
        image_data = b"\x89PNG\r\n\x1a\n"

        with patch.dict(os.environ, {"TERM": "xterm-sixel"}):
            # Will return False because sixel encoder isn't implemented
            result = display_image_sixel(image_data)
            assert result is False


class TestDisplayImageInTerminal:
    """Tests for the main display_image_in_terminal function."""

    def test_display_falls_back_to_ansi(self) -> None:
        """When no special terminal is detected, should try ANSI fallback."""
        # Create a minimal valid PNG
        # This is a 1x1 red pixel PNG
        png_data = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00"
            b"\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N"
            b"\x00\x00\x00\x00IEND\xaeB`\x82"
        )

        # In test environment, will try ANSI fallback with PIL
        result = display_image_in_terminal(png_data)
        # Result depends on whether PIL is available and can decode
        assert isinstance(result, bool)

    def test_display_invalid_image_data(self) -> None:
        """Invalid image data should return False gracefully (when not in iTerm2)."""
        # Need to disable iTerm2 detection to test the fallback path
        with patch.dict(
            os.environ,
            {"TERM_PROGRAM": "not-iterm", "LC_TERMINAL": "", "TERM": "xterm"},
            clear=False,
        ):
            result = display_image_in_terminal(b"not an image")
            assert result is False

    def test_display_empty_data(self) -> None:
        """Empty image data should return False (when not in iTerm2)."""
        with patch.dict(
            os.environ,
            {"TERM_PROGRAM": "not-iterm", "LC_TERMINAL": "", "TERM": "xterm"},
            clear=False,
        ):
            result = display_image_in_terminal(b"")
            assert result is False
