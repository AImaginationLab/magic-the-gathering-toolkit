"""Tests for image loading functionality."""

from __future__ import annotations

from io import BytesIO
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import httpx
import pytest
from PIL import Image

from mtg_spellbook.widgets.art_navigator import HAS_IMAGE_SUPPORT

if TYPE_CHECKING:
    pass


class TestImageLoading:
    """Test image loading functionality."""

    @pytest.mark.skipif(not HAS_IMAGE_SUPPORT, reason="Image support not available")
    async def test_load_image_with_valid_url(self, mock_image: Image.Image) -> None:
        """Test load_image_from_url handles valid URL."""
        from mtg_spellbook.widgets.art_navigator.image_loader import (
            clear_image_cache,
            load_image_from_url,
        )

        # Clear caches to ensure fresh request
        await clear_image_cache()

        mock_widget = MagicMock()
        mock_widget.loading = False

        # Mock httpx response
        mock_response = MagicMock()
        img_bytes = BytesIO()
        mock_image.save(img_bytes, format="PNG")
        mock_response.content = img_bytes.getvalue()
        mock_response.raise_for_status = MagicMock()

        # Create mock client (not context manager - shared client pattern)
        mock_client = MagicMock()

        async def mock_get(_url: str, timeout: float | None = None) -> MagicMock:  # noqa: ARG001
            return mock_response

        mock_client.get = mock_get

        async def mock_get_http_client() -> MagicMock:
            return mock_client

        with (
            patch(
                "mtg_spellbook.widgets.art_navigator.image_loader._get_http_client",
                mock_get_http_client,
            ),
            patch(
                "mtg_spellbook.widgets.art_navigator.image_loader._load_from_disk",
                return_value=None,
            ),
        ):
            result = await load_image_from_url("https://example.com/test.jpg", mock_widget)

            assert result is True
            assert mock_widget.loading is False
            assert mock_widget.image is not None

    @pytest.mark.skipif(not HAS_IMAGE_SUPPORT, reason="Image support not available")
    async def test_load_image_with_404_error(self) -> None:
        """Test load_image_from_url handles 404 gracefully."""
        from mtg_spellbook.widgets.art_navigator.image_loader import (
            clear_image_cache,
            load_image_from_url,
        )

        await clear_image_cache()

        mock_widget = MagicMock()
        mock_widget.loading = False

        mock_client = MagicMock()

        async def mock_get(_url: str, timeout: float | None = None) -> MagicMock:  # noqa: ARG001
            raise httpx.HTTPStatusError("404", request=MagicMock(), response=MagicMock())

        mock_client.get = mock_get

        async def mock_get_http_client() -> MagicMock:
            return mock_client

        with (
            patch(
                "mtg_spellbook.widgets.art_navigator.image_loader._get_http_client",
                mock_get_http_client,
            ),
            patch(
                "mtg_spellbook.widgets.art_navigator.image_loader._load_from_disk",
                return_value=None,
            ),
        ):
            result = await load_image_from_url("https://example.com/missing.jpg", mock_widget)

            assert result is False
            assert mock_widget.loading is False

    @pytest.mark.skipif(not HAS_IMAGE_SUPPORT, reason="Image support not available")
    async def test_load_image_with_timeout(self) -> None:
        """Test load_image_from_url handles timeout."""
        from mtg_spellbook.widgets.art_navigator.image_loader import (
            clear_image_cache,
            load_image_from_url,
        )

        await clear_image_cache()

        mock_widget = MagicMock()
        mock_widget.loading = False

        mock_client = MagicMock()

        async def mock_get(_url: str, timeout: float | None = None) -> MagicMock:  # noqa: ARG001
            raise httpx.TimeoutException("Timeout")

        mock_client.get = mock_get

        async def mock_get_http_client() -> MagicMock:
            return mock_client

        with (
            patch(
                "mtg_spellbook.widgets.art_navigator.image_loader._get_http_client",
                mock_get_http_client,
            ),
            patch(
                "mtg_spellbook.widgets.art_navigator.image_loader._load_from_disk",
                return_value=None,
            ),
        ):
            result = await load_image_from_url(
                "https://example.com/slow.jpg", mock_widget, timeout=1.0
            )

            assert result is False
            assert mock_widget.loading is False

    @pytest.mark.skipif(not HAS_IMAGE_SUPPORT, reason="Image support not available")
    async def test_load_image_sets_loading_state(self, mock_image: Image.Image) -> None:
        """Test load_image_from_url sets and clears loading state."""
        from mtg_spellbook.widgets.art_navigator.image_loader import (
            clear_image_cache,
            load_image_from_url,
        )

        await clear_image_cache()

        loading_states: list[bool] = []

        class MockWidget:
            def __init__(self) -> None:
                self._loading = False
                self.image: Image.Image | None = None

            @property
            def loading(self) -> bool:
                return self._loading

            @loading.setter
            def loading(self, value: bool) -> None:
                self._loading = value
                loading_states.append(value)

        mock_widget = MockWidget()

        # Mock httpx response
        mock_response = MagicMock()
        img_bytes = BytesIO()
        mock_image.save(img_bytes, format="PNG")
        mock_response.content = img_bytes.getvalue()
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()

        async def mock_get(_url: str, timeout: float | None = None) -> MagicMock:  # noqa: ARG001
            return mock_response

        mock_client.get = mock_get

        async def mock_get_http_client() -> MagicMock:
            return mock_client

        with (
            patch(
                "mtg_spellbook.widgets.art_navigator.image_loader._get_http_client",
                mock_get_http_client,
            ),
            patch(
                "mtg_spellbook.widgets.art_navigator.image_loader._load_from_disk",
                return_value=None,
            ),
        ):
            await load_image_from_url("https://example.com/test.jpg", mock_widget)

            # Should set loading=True, then loading=False (verify order)
            assert loading_states == [True, False], f"Expected [True, False], got {loading_states}"

    @pytest.mark.skipif(not HAS_IMAGE_SUPPORT, reason="Image support not available")
    async def test_load_image_converts_rgba_to_rgb(self) -> None:
        """Test load_image_from_url converts RGBA images to RGB."""
        from mtg_spellbook.widgets.art_navigator.image_loader import (
            clear_image_cache,
            load_image_from_url,
        )

        await clear_image_cache()

        mock_widget = MagicMock()
        mock_widget.loading = False

        # Create RGBA image
        rgba_image = Image.new("RGBA", (100, 100), color=(255, 0, 0, 128))

        # Mock httpx response
        mock_response = MagicMock()
        img_bytes = BytesIO()
        rgba_image.save(img_bytes, format="PNG")
        mock_response.content = img_bytes.getvalue()
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()

        async def mock_get(_url: str, timeout: float | None = None) -> MagicMock:  # noqa: ARG001
            return mock_response

        mock_client.get = mock_get

        async def mock_get_http_client() -> MagicMock:
            return mock_client

        with (
            patch(
                "mtg_spellbook.widgets.art_navigator.image_loader._get_http_client",
                mock_get_http_client,
            ),
            patch(
                "mtg_spellbook.widgets.art_navigator.image_loader._load_from_disk",
                return_value=None,
            ),
        ):
            result = await load_image_from_url("https://example.com/rgba.png", mock_widget)

            assert result is True
            # Image should be converted to RGB
            assert mock_widget.image.mode == "RGB"

    @pytest.mark.skipif(not HAS_IMAGE_SUPPORT, reason="Image support not available")
    async def test_load_image_replaces_normal_with_large(self, mock_image: Image.Image) -> None:
        """Test load_image_from_url replaces 'normal' with 'large' in URL."""
        from mtg_spellbook.widgets.art_navigator.image_loader import (
            clear_image_cache,
            load_image_from_url,
        )

        # Clear caches to ensure fresh request
        await clear_image_cache()

        mock_widget = MagicMock()
        mock_widget.loading = False
        called_url = None

        # Mock httpx response
        mock_response = MagicMock()
        img_bytes = BytesIO()
        mock_image.save(img_bytes, format="PNG")
        mock_response.content = img_bytes.getvalue()
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()

        async def mock_get(url: str, timeout: float | None = None) -> MagicMock:  # noqa: ARG001
            nonlocal called_url
            called_url = url
            return mock_response

        mock_client.get = mock_get

        async def mock_get_http_client() -> MagicMock:
            return mock_client

        with (
            patch(
                "mtg_spellbook.widgets.art_navigator.image_loader._get_http_client",
                mock_get_http_client,
            ),
            patch(
                "mtg_spellbook.widgets.art_navigator.image_loader._load_from_disk",
                return_value=None,
            ),
        ):
            await load_image_from_url(
                "https://example.com/normal/test.jpg", mock_widget, use_large=True
            )

            # Check that URL was modified
            assert called_url is not None
            assert "large" in called_url
            assert "normal" not in called_url

    @pytest.mark.skipif(not HAS_IMAGE_SUPPORT, reason="Image support not available")
    async def test_load_image_does_not_replace_when_use_large_false(
        self, mock_image: Image.Image
    ) -> None:
        """Test load_image_from_url keeps original URL when use_large=False."""
        from mtg_spellbook.widgets.art_navigator.image_loader import (
            clear_image_cache,
            load_image_from_url,
        )

        await clear_image_cache()

        mock_widget = MagicMock()
        mock_widget.loading = False
        called_url = None

        # Mock httpx response
        mock_response = MagicMock()
        img_bytes = BytesIO()
        mock_image.save(img_bytes, format="PNG")
        mock_response.content = img_bytes.getvalue()
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()

        async def mock_get(url: str, timeout: float | None = None) -> MagicMock:  # noqa: ARG001
            nonlocal called_url
            called_url = url
            return mock_response

        mock_client.get = mock_get

        async def mock_get_http_client() -> MagicMock:
            return mock_client

        with (
            patch(
                "mtg_spellbook.widgets.art_navigator.image_loader._get_http_client",
                mock_get_http_client,
            ),
            patch(
                "mtg_spellbook.widgets.art_navigator.image_loader._load_from_disk",
                return_value=None,
            ),
        ):
            original_url = "https://example.com/normal/test.jpg"
            await load_image_from_url(original_url, mock_widget, use_large=False)

            # Check that URL was NOT modified
            assert called_url == original_url
