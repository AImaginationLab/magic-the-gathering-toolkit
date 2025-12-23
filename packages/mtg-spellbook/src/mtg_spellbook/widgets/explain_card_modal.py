"""Explain Card modal - shows keyword explanations for a card."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import ScrollableContainer, Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, Static

if TYPE_CHECKING:
    from mtg_core.data.models.responses import CardDetail


class ExplainCardModal(ModalScreen[None]):
    """Modal that explains keywords found on a card."""

    DEFAULT_CSS = """
    ExplainCardModal {
        align: center middle;
    }

    ExplainCardModal > Vertical {
        width: 70;
        height: auto;
        max-height: 30;
        background: #1e1e2e;
        border: thick #c9a227;
        padding: 1 2;
    }

    ExplainCardModal .modal-title {
        text-align: center;
        text-style: bold;
        color: #c9a227;
        margin-bottom: 1;
    }

    ExplainCardModal .card-name {
        text-align: center;
        color: #fff;
        margin-bottom: 1;
    }

    ExplainCardModal .keywords-container {
        height: auto;
        max-height: 22;
        padding: 0 1;
    }

    ExplainCardModal .keyword-section {
        margin-bottom: 1;
        padding: 1;
        background: #252540;
        border: round #444;
    }

    ExplainCardModal .keyword-name {
        text-style: bold;
        color: #ffd700;
    }

    ExplainCardModal .keyword-summary {
        color: #ccc;
    }

    ExplainCardModal .no-keywords {
        text-align: center;
        color: #888;
        padding: 2;
    }

    ExplainCardModal .hint {
        text-align: center;
        color: #666;
        margin-top: 1;
    }
    """

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        ("escape,q,enter,space", "dismiss", "Close"),
    ]

    # Keywords we can detect - loaded from keywords.json
    _keywords_data: ClassVar[list[dict[str, Any]] | None] = None

    def __init__(self, card: CardDetail) -> None:
        super().__init__()
        self._card = card
        self._load_keywords()

    @classmethod
    def _load_keywords(cls) -> None:
        """Load keywords data from JSON file (cached)."""
        if cls._keywords_data is not None:
            return

        keywords_path = Path(__file__).parent.parent / "data" / "keywords.json"
        if keywords_path.exists():
            try:
                data = json.loads(keywords_path.read_text())
                cls._keywords_data = data.get("keywords", [])
            except Exception:
                cls._keywords_data = []
        else:
            cls._keywords_data = []

    def _find_keywords_in_text(self, text: str) -> list[dict[str, Any]]:
        """Find keywords present in the card text."""
        if not self._keywords_data or not text:
            return []

        found = []
        text_lower = text.lower()

        for kw in self._keywords_data:
            kw_name = kw.get("name", "").lower()
            if not kw_name:
                continue

            # Check for keyword in text (whole word match)
            pattern = r"\b" + re.escape(kw_name) + r"\b"
            if re.search(pattern, text_lower):
                found.append(kw)

        return found

    def compose(self) -> ComposeResult:
        card = self._card
        card_text = card.text or ""
        card_name = card.name

        # Find keywords in the card's text
        found_keywords = self._find_keywords_in_text(card_text)

        # Also check type line for creature types that might have keywords
        card_type = card.type or ""
        type_keywords = self._find_keywords_in_text(card_type)

        # Combine and deduplicate
        all_keywords = {kw["name"]: kw for kw in found_keywords + type_keywords}
        keywords = list(all_keywords.values())

        with Vertical():
            yield Label("Card Keywords Explained", classes="modal-title")
            yield Label(f"[bold]{card_name}[/]", classes="card-name")

            with ScrollableContainer(classes="keywords-container"):
                if keywords:
                    for kw in keywords:
                        name = kw.get("name", "")
                        summary = kw.get("summary", "")
                        reminder = kw.get("reminder_text", "")

                        with Vertical(classes="keyword-section"):
                            yield Static(f"[bold #ffd700]{name}[/]", classes="keyword-name")
                            yield Static(summary, classes="keyword-summary")
                            if reminder:
                                yield Static(
                                    f"[italic dim]{reminder}[/]",
                                    classes="keyword-reminder",
                                )
                else:
                    yield Static(
                        "[dim]No keywords found on this card.[/]\n\n"
                        "Try the Knowledge Base (?) for the full glossary.",
                        classes="no-keywords",
                    )

            yield Static("[dim]Press Esc to close[/]", classes="hint")

    async def action_dismiss(self, result: None = None) -> None:
        """Close the modal."""
        self.dismiss(result)
