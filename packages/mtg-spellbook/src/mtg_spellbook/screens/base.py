"""Base screen with persistent menu bar."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, ClassVar, TypeVar

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.css.query import NoMatches
from textual.screen import Screen
from textual.widgets import Footer

from ..widgets.menu import MenuActionRequested, MenuBar

if TYPE_CHECKING:
    pass

T = TypeVar("T")


class BaseScreen(Screen[T]):
    """Base screen providing consistent layout with menu bar.

    Subclasses should:
    1. Override compose_content() to provide their specific UI
    2. Optionally override BINDINGS to add screen-specific key bindings
    3. Optionally set show_footer = False to hide the footer

    The base screen provides:
    - MenuBar at top (expandable, persists across screens)
    - Content area (from compose_content())
    - Footer at bottom (optional)

    IMPORTANT LAYOUT PATTERN:
    When overriding #screen-content with grid layout, use only 2 rows:
        grid-rows: <header-height> 1fr;
    Put any statusbar INSIDE the main content pane, not as a separate grid row.
    This avoids layout bugs where content collapses to 0 height.

    Example:
        SomeScreen #screen-content {
            layout: grid;
            grid-size: 1;
            grid-rows: 4 1fr;  /* header + main, statusbar goes inside main */
        }
    """

    BINDINGS: ClassVar[list[Binding]] = [  # type: ignore[assignment]
        Binding("f10", "toggle_menu", "Menu", show=False),
        Binding("ctrl+m", "toggle_menu", "Menu", show=False),
    ]

    CSS = """
    BaseScreen {
        layout: grid;
        grid-size: 1;
        grid-rows: auto 1fr;  /* menu-bar, content */
        height: 100%;
        overflow: hidden;  /* Prevent content from overflowing */
    }

    BaseScreen.with-footer {
        grid-rows: auto 1fr auto;  /* menu-bar, content, footer */
    }

    #screen-content {
        width: 100%;
        overflow: hidden;  /* Clip overflowing children */
    }

    /* CRITICAL: Ensure ALL direct children of screen-content fill their grid cells.
       Without this, Horizontal/Vertical containers in grid rows collapse to 0 height.
       This prevents layout bugs where content exists in DOM but isn't visible. */
    #screen-content > Horizontal,
    #screen-content > Vertical,
    #screen-content > Container {
        width: 100%;
        height: 100%;
    }
    """

    # Subclasses can set this to False to hide footer
    show_footer: ClassVar[bool] = True

    async def on_mount(self) -> None:
        """Apply footer class on mount if footer is shown."""
        if self.show_footer:
            self.add_class("with-footer")

    def compose(self) -> ComposeResult:
        """Compose the screen with menu bar, content, and optional footer."""
        yield MenuBar(id="screen-menu-bar")
        with Container(id="screen-content"):
            yield from self.compose_content()
        if self.show_footer:
            yield Footer()

    @abstractmethod
    def compose_content(self) -> ComposeResult:
        """Compose the screen-specific content.

        Subclasses must implement this to provide their UI.
        """
        yield from ()

    def action_toggle_menu(self) -> None:
        """Toggle the menu bar."""
        try:
            menu = self.query_one("#screen-menu-bar", MenuBar)
            menu.toggle()
        except NoMatches:
            pass

    @on(MenuActionRequested)
    def on_menu_action_requested(self, event: MenuActionRequested) -> None:
        """Route menu actions to action handlers.

        Checks for handlers on the screen first, then on the app.
        Uses call_later to defer action execution, allowing the message
        processing to complete before the action runs. This prevents
        timeout issues when actions push new screens.
        """
        event.stop()

        # First try screen-level action
        action_method = getattr(self, f"action_{event.action}", None)
        if action_method and callable(action_method):
            self.call_later(action_method)
            return

        # Fall back to app-level action
        action_method = getattr(self.app, f"action_{event.action}", None)
        if action_method and callable(action_method):
            self.call_later(action_method)
