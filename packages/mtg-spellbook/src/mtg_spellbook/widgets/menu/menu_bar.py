"""Persistent expandable menu bar widget."""

from __future__ import annotations

from typing import ClassVar

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.reactive import reactive
from textual.widgets import Static

from .menu_item import MenuItem
from .messages import MenuActionRequested, MenuToggled


class MenuBar(Vertical, can_focus=True):
    """Persistent menu bar that expands to show navigation options.

    Features:
    - Click trigger or press F10/Ctrl+M to toggle
    - Arrow keys navigate items when expanded
    - Enter/Space/Click activates items
    - Escape collapses menu
    - Shows hotkey hints inline
    """

    DEFAULT_CSS = """
    MenuBar {
        width: 100%;
        height: auto;
        background: #1a1a1a;
        border-bottom: solid #333333;
    }

    MenuBar #menu-trigger {
        width: 100%;
        height: 1;
        padding: 0 1;
        background: #1a1a1a;
    }

    MenuBar #menu-trigger:hover {
        background: #252525;
    }

    MenuBar #menu-content {
        display: none;
        width: 100%;
        height: auto;
        max-height: 20;
        background: #151515;
        padding: 0;
    }

    MenuBar.expanded #menu-content {
        display: block;
    }

    MenuBar .section-header {
        width: 100%;
        height: 1;
        padding: 0 2;
        margin-top: 1;
        color: #c9a227;
        text-style: bold;
    }

    MenuBar .section-header:first-child {
        margin-top: 0;
    }
    """

    BINDINGS: ClassVar[list[Binding]] = [  # type: ignore[assignment]
        Binding("escape", "collapse_menu", "Close Menu", show=False),
        Binding("up,k", "nav_up", "Up", show=False),
        Binding("down,j,tab", "nav_down", "Down", show=False),
        Binding("shift+tab", "nav_up", "Up", show=False),
        Binding("enter,space", "select_item", "Select", show=False),
        Binding("f10,ctrl+m", "toggle_menu", "Toggle Menu", show=False),
        Binding("home", "nav_first", "First", show=False),
        Binding("end", "nav_last", "Last", show=False),
    ]

    is_expanded: reactive[bool] = reactive(False, toggle_class="expanded")

    def __init__(self, id: str | None = None) -> None:
        super().__init__(id=id)
        self._selected_index: int = 0
        self._menu_items: list[MenuItem] = []
        self._previous_focus: str | None = None  # ID of widget focused before menu opened

    def compose(self) -> ComposeResult:
        yield Static(self._render_trigger(), id="menu-trigger")
        with Vertical(id="menu-content"):
            # Browse section
            yield Static("[bold]Browse[/]", classes="section-header")
            yield MenuItem("Search", "h", "show_search", id="menu-search")
            yield MenuItem("Artists", "a", "browse_artists", id="menu-artists")
            yield MenuItem("Sets", "s", "browse_sets", id="menu-sets")
            yield MenuItem("Decks", "d", "browse_decks", id="menu-decks")
            yield MenuItem("Collection", "c", "browse_collection", id="menu-collection")

            # Card Actions section
            yield Static("[bold]Card Actions[/]", classes="section-header")
            yield MenuItem("Find Synergies", "Ctrl+S", "synergy_current", id="menu-synergy")
            yield MenuItem("Detect Combos", "Ctrl+O", "combos_current", id="menu-combos")
            yield MenuItem("View Art", "Ctrl+A", "art_current", id="menu-art")
            yield MenuItem("Show Price", "Ctrl+P", "price_current", id="menu-price")

            # Quick Actions section
            yield Static("[bold]Quick[/]", classes="section-header")
            yield MenuItem("Random Card", "r", "random_card", id="menu-random")

    def on_mount(self) -> None:
        """Cache menu items for navigation."""
        self._menu_items = list(self.query(MenuItem))

    def _render_trigger(self) -> str:
        """Render the menu trigger text."""
        arrow = "▼" if self.is_expanded else "▶"
        return f" {arrow} [bold]Menu[/]  [dim]F10 or Ctrl+M to toggle[/dim]"

    def watch_is_expanded(self, expanded: bool) -> None:
        """Update trigger display when expanded state changes."""
        # Guard: only update if widget is mounted (trigger exists)
        from textual.css.query import NoMatches

        try:
            trigger = self.query_one("#menu-trigger", Static)
            trigger.update(self._render_trigger())
        except NoMatches:
            # Widget not yet mounted, skip update
            return

        self.post_message(MenuToggled(expanded=expanded))

        if expanded and self._menu_items:
            # Save the currently focused widget before switching to menu
            try:
                focused = self.app.focused
                if (
                    focused is not None
                    and focused.id is not None
                    and not isinstance(focused, MenuItem)
                ):
                    self._previous_focus = focused.id
            except Exception:
                pass  # App not ready, skip saving focus

            # Focus first menu item when expanding
            self._selected_index = 0
            self._menu_items[0].focus()
        elif not expanded and self._previous_focus:
            # Restore focus to the previously focused widget
            # Query from screen level first (for widgets in pushed screens),
            # fall back to app level
            try:
                previous_widget = self.screen.query_one(f"#{self._previous_focus}")
                previous_widget.focus()
            except NoMatches:
                # Try app level for widgets in main app
                try:
                    previous_widget = self.app.query_one(f"#{self._previous_focus}")
                    previous_widget.focus()
                except NoMatches:
                    pass  # Previous widget no longer exists
            except Exception:
                pass  # App/screen not ready
            finally:
                self._previous_focus = None

    def toggle(self) -> None:
        """Toggle menu expanded/collapsed state."""
        self.is_expanded = not self.is_expanded

    def action_toggle_menu(self) -> None:
        """Toggle menu (F10/Ctrl+M key handler)."""
        self.toggle()

    def expand_menu(self) -> None:
        """Expand the menu."""
        self.is_expanded = True

    def collapse_menu(self) -> None:
        """Collapse the menu."""
        self.is_expanded = False

    def action_collapse_menu(self) -> None:
        """Collapse the menu (escape key handler)."""
        if self.is_expanded:
            self.collapse_menu()

    def action_nav_up(self) -> None:
        """Navigate to previous menu item."""
        if not self.is_expanded or not self._menu_items:
            return
        self._selected_index = (self._selected_index - 1) % len(self._menu_items)
        self._menu_items[self._selected_index].focus()

    def action_nav_down(self) -> None:
        """Navigate to next menu item."""
        if not self.is_expanded or not self._menu_items:
            return
        self._selected_index = (self._selected_index + 1) % len(self._menu_items)
        self._menu_items[self._selected_index].focus()

    def action_nav_first(self) -> None:
        """Navigate to first menu item."""
        if not self.is_expanded or not self._menu_items:
            return
        self._selected_index = 0
        self._menu_items[0].focus()

    def action_nav_last(self) -> None:
        """Navigate to last menu item."""
        if not self.is_expanded or not self._menu_items:
            return
        self._selected_index = len(self._menu_items) - 1
        self._menu_items[-1].focus()

    def action_select_item(self) -> None:
        """Select the currently focused menu item."""
        if not self.is_expanded or not self._menu_items:
            return
        if 0 <= self._selected_index < len(self._menu_items):
            item = self._menu_items[self._selected_index]
            if not item.is_disabled:
                self.post_message(MenuActionRequested(item.action))
                self.collapse_menu()

    @on(MenuItem.Selected)
    def on_menu_item_selected(self, event: MenuItem.Selected) -> None:
        """Handle menu item selection via click."""
        event.stop()
        self.post_message(MenuActionRequested(event.item.action))
        self.collapse_menu()

    def on_click(self) -> None:
        """Handle click on menu bar (toggle if on trigger)."""
        # If collapsed, expand on any click
        if not self.is_expanded:
            self.toggle()

    def set_card_actions_enabled(self, enabled: bool) -> None:
        """Enable or disable card-related menu items.

        Called by the app when the current card changes.
        Disables synergy, combos, art, price when no card is selected.
        """
        card_action_ids = ["menu-synergy", "menu-combos", "menu-art", "menu-price"]
        for item_id in card_action_ids:
            try:
                item = self.query_one(f"#{item_id}", MenuItem)
                item.is_disabled = not enabled
            except Exception:
                pass  # Item not found, skip
