"""Terminal image display utilities."""

from __future__ import annotations


async def fetch_card_image(url: str) -> bytes | None:
    """Fetch card image from URL."""
    import httpx

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0)
            if response.status_code == 200:
                return response.content
    except (httpx.HTTPError, httpx.TimeoutException, OSError):
        pass
    return None


def display_image_iterm2(image_data: bytes) -> bool:
    """Display image using iTerm2's imgcat protocol (high fidelity)."""
    import base64
    import os
    import sys

    # Check if we're in iTerm2 or a compatible terminal
    term_program = os.environ.get("TERM_PROGRAM", "")
    if term_program not in ("iTerm.app", "WezTerm", "mintty"):
        # Check for other iTerm2-compatible terminals
        lc_terminal = os.environ.get("LC_TERMINAL", "")
        if lc_terminal != "iTerm2":
            return False

    try:
        # iTerm2 inline images protocol
        # Format: ESC ] 1337 ; File = [arguments] : base64data ^G
        encoded = base64.b64encode(image_data).decode("ascii")

        # Width=auto fits to terminal, preserveAspectRatio keeps card shape
        sys.stdout.write(f"\033]1337;File=inline=1;width=30;preserveAspectRatio=1:{encoded}\a")
        sys.stdout.write("\n")
        sys.stdout.flush()
        return True
    except (OSError, ValueError):
        return False


def display_image_kitty(image_data: bytes) -> bool:
    """Display image using Kitty graphics protocol (high fidelity)."""
    import base64
    import os
    import sys

    # Check if we're in Kitty terminal
    if os.environ.get("TERM", "") != "xterm-kitty":
        return False

    try:
        encoded = base64.b64encode(image_data).decode("ascii")

        # Kitty graphics protocol - send in chunks
        # a=T means transmit, f=100 means PNG format auto-detect
        chunk_size = 4096
        first_chunk = True

        for i in range(0, len(encoded), chunk_size):
            chunk = encoded[i : i + chunk_size]
            is_last = i + chunk_size >= len(encoded)

            if first_chunk:
                # First chunk: a=T (transmit), f=100 (auto format), m=1 if more chunks
                m = 0 if is_last else 1
                sys.stdout.write(f"\033_Ga=T,f=100,m={m};{chunk}\033\\")
                first_chunk = False
            else:
                # Continuation chunks
                m = 0 if is_last else 1
                sys.stdout.write(f"\033_Gm={m};{chunk}\033\\")

        sys.stdout.write("\n")
        sys.stdout.flush()
        return True
    except (OSError, ValueError):
        return False


def display_image_sixel(image_data: bytes, width: int = 25) -> bool:
    """Display image using Sixel graphics (for compatible terminals)."""
    import os

    # Sixel support check - very few terminals support this
    # Known: xterm with +sixel, mlterm, some others
    term = os.environ.get("TERM", "")
    if "sixel" not in term.lower():
        return False

    try:
        from io import BytesIO

        from PIL import Image

        img = Image.open(BytesIO(image_data))

        # Resize for display (sixel has ~6 pixels per character height)
        aspect_ratio = img.height / img.width
        px_width = width * 10  # ~10 pixels per character width
        px_height = int(px_width * aspect_ratio)

        resized = img.resize((px_width, px_height), Image.Resampling.LANCZOS)
        palette_img = resized.convert("P", palette=Image.Palette.ADAPTIVE, colors=256)  # noqa: F841

        # This would require a sixel encoder - skip for now
        return False
    except (ImportError, OSError, ValueError):
        return False


def display_image_in_terminal(image_data: bytes, width: int = 60) -> bool:
    """Display image in terminal. Tries high-fidelity protocols first, falls back to ANSI."""

    # Try high-fidelity protocols first
    if display_image_iterm2(image_data) or display_image_kitty(image_data):
        return True

    # Fall back to ANSI half-block rendering
    try:
        from io import BytesIO
        from typing import cast

        from PIL import Image

        img = Image.open(BytesIO(image_data))

        # Calculate height maintaining aspect ratio (cards are ~745x1040)
        aspect_ratio = img.height / img.width
        height = int(width * aspect_ratio * 0.5)  # Terminal chars are ~2:1

        # Resize - use higher internal resolution for better quality
        # Sample at 2x width and height, then each character represents 2x2 pixels
        resized = img.resize((width * 2, height * 2), Image.Resampling.LANCZOS)
        rgb_img = resized.convert("RGB")

        lines: list[str] = []

        for y in range(0, rgb_img.height, 2):
            line = ""
            for x in range(rgb_img.width):
                # Get top and bottom pixels
                r1, g1, b1 = cast("tuple[int, int, int]", rgb_img.getpixel((x, y)))
                if y + 1 < rgb_img.height:
                    r2, g2, b2 = cast("tuple[int, int, int]", rgb_img.getpixel((x, y + 1)))
                else:
                    r2, g2, b2 = 0, 0, 0

                # Use half-block character with fg=top, bg=bottom
                line += f"\033[38;2;{r1};{g1};{b1}m\033[48;2;{r2};{g2};{b2}m▀"

            line += "\033[0m"  # Reset colors
            lines.append(line)

        # Print the image
        for line in lines:
            print(line)

        return True
    except (ImportError, OSError, ValueError):
        return False
