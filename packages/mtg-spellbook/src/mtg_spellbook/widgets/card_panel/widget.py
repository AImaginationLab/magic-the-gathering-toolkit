"""Main CardPanel widget for displaying card details."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.css.query import NoMatches
from textual.events import Key

from ..art_navigator import EnhancedArtNavigator

if TYPE_CHECKING:
    from mtg_core.data.database import MTGDatabase, ScryfallDatabase
    from mtg_core.data.models.responses import CardDetail, PrintingInfo

    from ...collection_manager import CollectionManager


class CardPanel(Vertical, can_focus=True):
    """Display card with immersive art-focused view."""

    BINDINGS: ClassVar[list[Binding]] = [  # type: ignore[assignment]
        Binding("s", "view_set", "View Set", show=False),
    ]

    def __init__(self, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self._card: CardDetail | None = None
        self._printings: list[PrintingInfo] = []
        self._current_printing_index: int = 0
        self._card_name_for_art: str = ""
        self._id_prefix = id or "card-panel"
        self._keywords: set[str] = set()

    def set_keywords(self, keywords: set[str]) -> None:
        """Set the keywords to highlight in card text."""
        self._keywords = keywords

    def set_collection_manager(self, manager: CollectionManager | None) -> None:
        """Set collection manager for owned status and quick-add."""
        try:
            art_nav = self.query_one(f"#{self._child_id('art-navigator')}", EnhancedArtNavigator)
            art_nav.set_collection_manager(manager)
        except NoMatches:
            pass

    def _child_id(self, name: str) -> str:
        """Generate a unique child widget ID based on panel's ID."""
        return f"{self._id_prefix}-{name}"

    def get_child_name(self, name: str) -> str:
        """Get the child widget ID without selector."""
        return self._child_id(name)

    def get_child_id(self, name: str) -> str:
        """Get the full CSS selector for a child widget."""
        return f"#{self._child_id(name)}"

    def compose(self) -> ComposeResult:
        yield EnhancedArtNavigator(
            self._id_prefix,
            id=self._child_id("art-navigator"),
            classes="-art-navigator",
        )

    def on_key(self, event: Key) -> None:
        """Handle key events - focus art navigator on down arrow."""
        if event.key == "down" and self.focus_art_navigator():
            event.stop()

    def focus_art_navigator(self) -> bool:
        """Focus the art navigator. Returns True if focused."""
        try:
            art_nav = self.query_one(f"#{self._child_id('art-navigator')}", EnhancedArtNavigator)
            art_nav.focus()
            return True
        except NoMatches:
            pass
        return False

    def show_loading(self, message: str = "Loading card details...") -> None:
        """Show loading indicator."""
        try:
            art_nav = self.query_one(f"#{self._child_id('art-navigator')}", EnhancedArtNavigator)
            art_nav.show_loading(message)
        except NoMatches:
            pass

    def update_card(self, card: CardDetail | None) -> None:
        """Update the displayed card."""
        self._card = card

    def update_card_with_synergy(
        self, card: CardDetail | None, _synergy_info: dict[str, object] | None
    ) -> None:
        """Update the displayed card with synergy information."""
        self._card = card

    async def load_legalities(self, db: MTGDatabase, card_name: str) -> None:
        """Load and pass legalities to the focus view."""
        try:
            from mtg_core.exceptions import CardNotFoundError
            from mtg_core.tools import cards

            result = await cards.get_card_legalities(db, card_name)
            art_nav = self.query_one(f"#{self._child_id('art-navigator')}", EnhancedArtNavigator)
            art_nav.set_legalities(result.legalities)
        except NoMatches:
            pass  # Art navigator not mounted yet
        except CardNotFoundError:
            pass  # Card not found, no legalities to show

    async def load_printings(
        self,
        scryfall: ScryfallDatabase | None,
        mtg_db: MTGDatabase | None,
        card_name: str,
        flavor_name: str | None = None,
        target_set: str | None = None,
        target_number: str | None = None,
    ) -> None:
        """Load all printings for a card."""
        from . import loaders

        printings, error = await loaders.load_printings(scryfall, mtg_db, card_name)
        if error:
            return

        self._printings = printings
        self._card_name_for_art = card_name

        # Find the index of the target printing (matching set + collector number)
        start_index = 0
        if target_set and printings:
            target_set_upper = target_set.upper()
            for i, p in enumerate(printings):
                set_matches = p.set_code and p.set_code.upper() == target_set_upper
                number_matches = target_number is None or p.collector_number == target_number
                if set_matches and number_matches:
                    start_index = i
                    break
        self._current_printing_index = start_index

        try:
            art_nav = self.query_one(f"#{self._child_id('art-navigator')}", EnhancedArtNavigator)
            await art_nav.load_printings(
                card_name,
                printings,
                flavor_name=flavor_name,
                start_index=start_index,
            )
        except NoMatches:
            pass

    def action_view_set(self) -> None:
        """View the current card's set."""
        if self._card and self._card.set_code:
            from typing import Any, cast

            app = cast(Any, self.app)
            app.show_set_detail(self._card.set_code)
        else:
            self.notify("No set information available", severity="warning", timeout=2)

    @property
    def current_card(self) -> CardDetail | None:
        """Get the currently displayed card."""
        return self._card
