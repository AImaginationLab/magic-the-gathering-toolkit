"""Collection list panel for browsing owned cards."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Label, ListItem, ListView, Static

from ..ui.theme import ui_colors
from .messages import CardRemovedFromCollection, CollectionCardSelected
from .modals import AddToCollectionResult, ConfirmDeleteModal

if TYPE_CHECKING:
    from ..collection_manager import CollectionCardWithData, CollectionManager


class CollectionCardItem(ListItem):
    """A card in the collection list."""

    DEFAULT_CSS = """
    CollectionCardItem {
        height: 2;
        padding: 0 1;
        background: #121218;
    }

    CollectionCardItem:hover {
        background: #1a1a2e;
    }

    CollectionCardItem.-highlight {
        background: #2a2a4e;
    }

    CollectionCardItem .card-qty {
        width: 4;
        color: #e6c84a;
    }

    CollectionCardItem .card-name {
        width: 1fr;
    }

    CollectionCardItem .card-mana {
        width: auto;
        min-width: 8;
        text-align: right;
        color: #888;
    }

    CollectionCardItem .card-avail {
        width: 16;
        text-align: right;
    }

    CollectionCardItem .avail-good {
        color: #7ec850;
    }

    CollectionCardItem .avail-partial {
        color: #e6c84a;
    }

    CollectionCardItem .avail-none {
        color: #666;
    }
    """

    def __init__(self, card: CollectionCardWithData) -> None:
        super().__init__()
        self.card_data = card

    def compose(self) -> ComposeResult:
        card = self.card_data
        total = card.total_owned
        avail = card.available

        # Determine availability styling
        if avail == total:
            avail_class = "avail-good"
            avail_text = f"[green]✓[/] {avail} avail"
        elif avail > 0:
            avail_class = "avail-partial"
            avail_text = f"[yellow]○[/] {avail}/{total}"
        else:
            avail_class = "avail-none"
            avail_text = f"[dim]● 0/{total}[/]"

        # Get mana cost
        mana = ""
        if card.card and card.card.mana_cost:
            mana = card.card.mana_cost

        with Horizontal():
            yield Label(f"{total}x", classes="card-qty")
            yield Label(card.card_name, classes="card-name")
            yield Label(mana, classes="card-mana")
            yield Label(avail_text, classes=f"card-avail {avail_class}")


class CollectionListPanel(Vertical):
    """Panel showing the user's card collection."""

    BINDINGS: ClassVar[list[Binding]] = [  # type: ignore[assignment]
        Binding("enter", "select_card", "View"),
        Binding("plus", "add_card", "Add"),
        Binding("delete", "remove_card", "Remove"),
        Binding("y", "show_synergies", "Synergy"),
        Binding("escape", "back", "Back"),
    ]

    DEFAULT_CSS = """
    CollectionListPanel {
        width: 100%;
        height: 100%;
        background: #0a0a14;
    }

    #collection-header {
        height: 3;
        background: #1a1a2e;
        border-bottom: heavy #c9a227;
        padding: 0 1;
        content-align: center middle;
    }

    #collection-header Label {
        text-style: bold;
    }

    #collection-stats {
        height: 2;
        padding: 0 1;
        background: #151520;
        border-bottom: solid #333;
    }

    #collection-list {
        height: 1fr;
    }

    #collection-empty {
        width: 100%;
        height: 100%;
        content-align: center middle;
        color: #666;
    }

    #collection-footer {
        height: 1;
        dock: bottom;
        background: #1a1a2e;
        padding: 0 1;
    }
    """

    def __init__(self, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self._manager: CollectionManager | None = None
        self._cards: list[CollectionCardWithData] = []
        self._total_count = 0
        self._page = 1
        self._page_size = 100

    def compose(self) -> ComposeResult:
        with Horizontal(id="collection-header"):
            yield Label(f"[{ui_colors.GOLD}]📦 MY COLLECTION[/]")

        yield Static("", id="collection-stats")

        yield ListView(id="collection-list")

        yield Static(
            "[dim]+[/] Add  [dim]Del[/] Remove  [dim]Enter[/] View  [dim]Esc[/] Back",
            id="collection-footer",
        )

    def set_manager(self, manager: CollectionManager) -> None:
        """Set the collection manager."""
        self._manager = manager

    @work
    async def refresh_collection(self) -> None:
        """Refresh the collection list."""
        if self._manager is None:
            return

        self._cards, self._total_count = await self._manager.get_collection(
            page=self._page,
            page_size=self._page_size,
        )

        stats = await self._manager.get_stats()

        # Update stats display
        stats_label = self.query_one("#collection-stats", Static)
        stats_label.update(
            f"[dim]Unique:[/] [{ui_colors.GOLD}]{stats.unique_cards}[/]  "
            f"[dim]Total:[/] [{ui_colors.GOLD}]{stats.total_cards}[/]  "
            f"[dim]Foils:[/] [{ui_colors.GOLD}]{stats.total_foils}[/]"
        )

        # Update list
        list_view = self.query_one("#collection-list", ListView)
        await list_view.clear()

        if not self._cards:
            # Show empty state
            list_view.display = False
            empty = self.query("#collection-empty")
            if not empty:
                await self.mount(
                    Static(
                        "[dim]No cards in collection.\nPress [bold]+[/] to add cards.[/]",
                        id="collection-empty",
                    ),
                    after=self.query_one("#collection-stats"),
                )
        else:
            list_view.display = True
            empty = self.query("#collection-empty")
            if empty:
                await empty.first().remove()

            for card in self._cards:
                await list_view.append(CollectionCardItem(card))

    def action_select_card(self) -> None:
        """Select the highlighted card."""
        list_view = self.query_one("#collection-list", ListView)
        if list_view.highlighted_child is not None:
            item = list_view.highlighted_child
            if isinstance(item, CollectionCardItem):
                self.post_message(
                    CollectionCardSelected(
                        item.card_data.card_name,
                        set_code=item.card_data.set_code,
                        collector_number=item.card_data.collector_number,
                    )
                )

    def action_add_card(self) -> None:
        """Open add card modal."""
        from .modals import AddToCollectionModal

        self.app.push_screen(AddToCollectionModal(), self._on_add_result)

    def _on_add_result(self, result: AddToCollectionResult | None) -> None:
        """Handle add modal result."""
        if result is not None:
            self._add_card_to_collection(result)

    @work
    async def _add_card_to_collection(self, data: AddToCollectionResult) -> None:
        """Add a card to the collection."""
        if self._manager is None:
            return

        result = await self._manager.add_card(
            card_name=data.card_name,
            quantity=data.quantity,
            foil=data.foil,
            set_code=data.set_code,
            collector_number=data.collector_number,
        )
        if result.success and result.card:
            # Show appropriate message based on input type
            if data.set_code and data.collector_number:
                msg = f"Added {data.quantity}x {result.card.name} ({data.set_code.upper()} #{data.collector_number})"
            else:
                msg = f"Added {data.quantity}x {result.card.name}"
            self.notify(msg)
            self.refresh_collection()
        else:
            self.notify(result.error or "Failed to add card", severity="error")

    def action_remove_card(self) -> None:
        """Remove the selected card with confirmation."""
        list_view = self.query_one("#collection-list", ListView)
        if list_view.highlighted_child is not None:
            item = list_view.highlighted_child
            if isinstance(item, CollectionCardItem):
                card_data = item.card_data
                # Show confirmation modal
                modal = ConfirmDeleteModal(
                    card_data.card_name,
                    card_data.quantity,
                    card_data.foil_quantity,
                )
                self.app.push_screen(modal, self._on_delete_confirmed)

    def _on_delete_confirmed(self, confirmed: bool | None) -> None:
        """Handle delete confirmation result."""
        if not confirmed:
            return
        list_view = self.query_one("#collection-list", ListView)
        if list_view.highlighted_child is not None:
            item = list_view.highlighted_child
            if isinstance(item, CollectionCardItem):
                self._remove_card(item.card_data.card_name)

    @work
    async def _remove_card(self, card_name: str) -> None:
        """Remove a card from the collection."""
        if self._manager is None:
            return

        removed = await self._manager.remove_card(card_name)
        if removed:
            self.notify(f"Removed {card_name} from collection")
            self.post_message(CardRemovedFromCollection(card_name))
            self.refresh_collection()

    def action_back(self) -> None:
        """Go back to dashboard."""
        self.add_class("hidden")

    def action_show_synergies(self) -> None:
        """Show synergies for the currently selected card."""
        list_view = self.query_one("#collection-list", ListView)
        if list_view.highlighted_child is None:
            self.notify("Select a card first", severity="warning", timeout=2)
            return

        item = list_view.highlighted_child
        if isinstance(item, CollectionCardItem):
            card_name = item.card_data.card_name
            # Call find_synergies on the app
            if hasattr(self.app, "find_synergies"):
                self.add_class("hidden")  # Hide this panel
                self.app.find_synergies(card_name)
