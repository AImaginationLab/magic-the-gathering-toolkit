"""Shared fixtures for FocusView tests."""

from __future__ import annotations

import pytest
from PIL import Image

from mtg_core.data.models.responses import PrintingInfo


@pytest.fixture
def sample_printing() -> PrintingInfo:
    """Create a sample printing with typical data."""
    return PrintingInfo(
        uuid="test-uuid-1",
        set_code="lea",
        collector_number="161",
        image="https://example.com/image.jpg",
        art_crop="https://example.com/art_crop.jpg",
        price_usd=2.50,
        price_eur=2.20,
        artist="Christopher Rush",
        flavor_text="The spark of an idea can ignite a revolution.",
        rarity="common",
        release_date="1993-08-05",
        illustration_id="test-illustration-1",
    )


@pytest.fixture
def sample_printings() -> list[PrintingInfo]:
    """Create multiple sample printings for navigation testing."""
    return [
        PrintingInfo(
            uuid="test-uuid-1",
            set_code="lea",
            collector_number="161",
            image="https://example.com/image1.jpg",
            art_crop="https://example.com/art_crop1.jpg",
            price_usd=2.50,
            price_eur=2.20,
            artist="Christopher Rush",
            flavor_text="First printing flavor.",
            rarity="common",
            release_date="1993-08-05",
        ),
        PrintingInfo(
            uuid="test-uuid-2",
            set_code="m10",
            collector_number="146",
            image="https://example.com/image2.jpg",
            art_crop="https://example.com/art_crop2.jpg",
            price_usd=1.00,
            price_eur=0.90,
            artist="Christopher Moeller",
            flavor_text="Second printing flavor.",
            rarity="uncommon",
            release_date="2009-07-17",
        ),
        PrintingInfo(
            uuid="test-uuid-3",
            set_code="m11",
            collector_number="147",
            image="https://example.com/image3.jpg",
            art_crop="https://example.com/art_crop3.jpg",
            price_usd=5.00,
            price_eur=4.50,
            artist="Howard Lyon",
            flavor_text="Third printing flavor.",
            rarity="rare",
            release_date="2010-07-16",
        ),
    ]


@pytest.fixture
def minimal_printing() -> PrintingInfo:
    """Create a minimal printing with optional fields empty."""
    return PrintingInfo(
        uuid="test-uuid-min",
        set_code=None,
        collector_number=None,
        image="https://example.com/minimal.jpg",
        art_crop=None,
        price_usd=None,
        price_eur=None,
        artist=None,
        flavor_text=None,
        rarity=None,
        release_date=None,
    )


@pytest.fixture
def mock_image() -> Image.Image:
    """Create a mock PIL Image."""
    img = Image.new("RGB", (100, 100), color="red")
    return img
