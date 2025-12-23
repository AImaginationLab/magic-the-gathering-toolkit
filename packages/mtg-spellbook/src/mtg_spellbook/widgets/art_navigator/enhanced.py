"""Enhanced art navigator with gallery and focus views."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.css.query import NoMatches
from textual.reactive import reactive
from textual.widgets import LoadingIndicator, Static

from .compare import CompareView
from .focus import FocusView
from .grid import PrintingsGrid
from .preview import PreviewPanel
from .view_toggle import ViewMode, ViewModeToggle

if TYPE_CHECKING:
    from mtg_core.data.models.responses import PrintingInfo

    from ...collection_manager import CollectionManager

# Status bar hints for each view mode
_STATUSBAR_HINTS = {
    ViewMode.GALLERY: "←→ Navigate | a: Art crop | f: Focus mode | c: Compare | s: Sort | esc: back",
    ViewMode.FOCUS: "←→ Next printing | a: Art crop | e: Explore Artist | g: Gallery | c: Compare | esc: back",
    ViewMode.COMPARE: "Space: Add | x: Remove | 1-4: Select slot | Backspace: Clear | g: Gallery | esc: back",
}


class EnhancedArtNavigator(Vertical, can_focus=True):
    """Multi-mode art navigator with gallery and focus views."""

    current_view: reactive[ViewMode] = reactive(ViewMode.FOCUS)  # Focus mode by default
    is_loading: reactive[bool] = reactive(False)

    BINDINGS: ClassVar[list[Binding]] = [  # type: ignore[assignment]
        Binding("h,left", "navigate_left", "← Left", show=False),
        Binding("j,down", "navigate_down", "↓ Down", show=False),
        Binding("k,up", "navigate_up", "↑ Up", show=False),
        Binding("l,right", "navigate_right", "→ Right", show=False),
        Binding("e", "browse_artist", "Explore Artist", show=False),
        Binding("s", "cycle_sort", "Sort", show=False),
        Binding("g", "switch_to_gallery", "Gallery", show=False),
        Binding("f", "switch_to_focus", "Focus", show=False),
        Binding("c", "switch_to_compare", "Compare", show=False),
        Binding("a", "toggle_art_crop", "Art Crop", show=False),
        Binding("space", "add_to_compare", "Add to Compare", show=False),
        Binding("x", "remove_from_compare", "Remove", show=False),
        Binding("backspace", "clear_compare", "Clear All", show=False),
        Binding("1", "select_slot_1", "Slot 1", show=False),
        Binding("2", "select_slot_2", "Slot 2", show=False),
        Binding("3", "select_slot_3", "Slot 3", show=False),
        Binding("4", "select_slot_4", "Slot 4", show=False),
        Binding("escape,q", "release_focus", "Back", show=False),
    ]

    def __init__(
        self,
        id_prefix: str,
        *,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self._id_prefix = id_prefix
        self._card_name: str = ""
        self._printings: list[PrintingInfo] = []
        self._compare_selected_slot: int = 1
        self._collection_manager: CollectionManager | None = None

    def set_collection_manager(self, manager: CollectionManager | None) -> None:
        """Set collection manager for owned status and quick-add."""
        self._collection_manager = manager

    def compose(self) -> ComposeResult:
        """Build multi-view layout."""
        # View toggle hidden - use keyboard shortcuts (g=gallery, f=focus, c=compare)
        yield ViewModeToggle(
            id=f"{self._id_prefix}-view-toggle",
            classes="view-toggle hidden",
        )

        yield LoadingIndicator(id=f"{self._id_prefix}-loading", classes="art-loading hidden")

        with Vertical(classes="gallery-container", id=f"{self._id_prefix}-gallery"):
            # Large preview image at top
            yield PreviewPanel(
                id=f"{self._id_prefix}-preview",
                classes="preview-panel",
            )
            # Filmstrip of thumbnails at bottom
            yield PrintingsGrid(
                id=f"{self._id_prefix}-grid",
                classes="printings-filmstrip",
            )

        yield FocusView(
            "",
            id=f"{self._id_prefix}-focus",
            classes="focus-view focus-hidden",
        )

        yield CompareView(
            id=f"{self._id_prefix}-compare",
            classes="compare-view compare-hidden",
        )

        yield Static(
            "",
            id=f"{self._id_prefix}-statusbar",
            classes="art-statusbar",
        )

    def on_mount(self) -> None:
        """Set up grid callback and initial statusbar."""
        grid = self.query_one(f"#{self._id_prefix}-grid", PrintingsGrid)
        grid.set_on_select(self._on_printing_selected)
        self._update_statusbar()

    def on_view_mode_toggle_mode_selected(self, event: ViewModeToggle.ModeSelected) -> None:
        """Handle mode button click."""
        self.current_view = event.mode

    def _update_statusbar(self) -> None:
        """Update statusbar text based on current view mode (QW1: Context-Sensitive)."""
        try:
            statusbar = self.query_one(f"#{self._id_prefix}-statusbar", Static)
            hint = _STATUSBAR_HINTS.get(self.current_view, "")
            if hint:
                statusbar.update(f"[dim]{hint}[/]")
        except NoMatches:
            pass

    def watch_is_loading(self, loading: bool) -> None:
        """Show/hide loading indicator."""
        try:
            indicator = self.query_one(f"#{self._id_prefix}-loading", LoadingIndicator)
            if loading:
                indicator.remove_class("hidden")
            else:
                indicator.add_class("hidden")
        except NoMatches:
            pass

    def show_loading(self, _message: str = "Loading...") -> None:
        """Show loading state."""
        self.is_loading = True

    def set_legalities(self, legalities: dict[str, str]) -> None:
        """Pass legalities to focus view."""
        try:
            focus = self.query_one(f"#{self._id_prefix}-focus", FocusView)
            focus.set_legalities(legalities)
        except NoMatches:
            pass

    async def load_printings(
        self,
        card_name: str,
        printings: list[PrintingInfo],
        flavor_name: str | None = None,
        start_index: int = 0,
    ) -> None:
        """Load printings into all views."""
        self.is_loading = True
        self._card_name = card_name
        self._printings = printings

        try:
            grid = self.query_one(f"#{self._id_prefix}-grid", PrintingsGrid)
            await grid.load_printings(card_name, printings)

            focus = self.query_one(f"#{self._id_prefix}-focus", FocusView)
            await focus.load_printings(
                card_name, printings, flavor_name=flavor_name, start_index=start_index
            )

            # Ensure focus mode is active after loading
            self.current_view = ViewMode.FOCUS
        finally:
            self.is_loading = False

    def watch_current_view(self, new_view: ViewMode) -> None:
        """Update display when view mode changes."""
        try:
            gallery = self.query_one(f"#{self._id_prefix}-gallery")
            focus = self.query_one(f"#{self._id_prefix}-focus", FocusView)
            compare = self.query_one(f"#{self._id_prefix}-compare", CompareView)
            toggle = self.query_one(f"#{self._id_prefix}-view-toggle", ViewModeToggle)

            if new_view == ViewMode.GALLERY:
                gallery.remove_class("gallery-hidden")
                focus.add_class("focus-hidden")
                compare.add_class("compare-hidden")
                # Set focus to grid
                grid = self.query_one(f"#{self._id_prefix}-grid", PrintingsGrid)
                grid.focus()
            elif new_view == ViewMode.FOCUS:
                gallery.add_class("gallery-hidden")
                focus.remove_class("focus-hidden")
                compare.add_class("compare-hidden")
                # Set focus to focus view
                focus.focus()
            elif new_view == ViewMode.COMPARE:
                gallery.add_class("gallery-hidden")
                focus.add_class("focus-hidden")
                compare.remove_class("compare-hidden")
                # Set focus to compare view
                compare.focus()

            toggle.set_mode(new_view)
            self._update_statusbar()
        except NoMatches:
            pass

    def _on_printing_selected(self, _index: int, printing: PrintingInfo) -> None:
        """Handle printing selection from grid."""
        preview = self.query_one(f"#{self._id_prefix}-preview", PreviewPanel)
        self.run_worker(preview.update_printing(self._card_name, printing))

    def action_browse_artist(self) -> None:
        """Browse other cards by the current artist."""
        from .messages import ArtistSelected

        # Get artist from current view
        artist = None
        if self.current_view == ViewMode.FOCUS:
            focus = self.query_one(f"#{self._id_prefix}-focus", FocusView)
            printing = focus.get_current_printing()
            if printing:
                artist = printing.artist
        elif self.current_view == ViewMode.GALLERY:
            grid = self.query_one(f"#{self._id_prefix}-grid", PrintingsGrid)
            printing = grid.get_current_printing()
            if printing:
                artist = printing.artist

        if artist:
            self.post_message(ArtistSelected(artist, self._card_name))
        else:
            self.notify("No artist information available", severity="warning", timeout=2)

    def action_switch_to_gallery(self) -> None:
        """Switch to gallery view."""
        self.current_view = ViewMode.GALLERY

    def action_switch_to_focus(self) -> None:
        """Switch to focus view and sync with gallery selection."""
        try:
            grid = self.query_one(f"#{self._id_prefix}-grid", PrintingsGrid)
            focus = self.query_one(f"#{self._id_prefix}-focus", FocusView)
            current_printing = grid.get_current_printing()

            if current_printing and self._printings:
                for i, p in enumerate(self._printings):
                    if (
                        p.set_code == current_printing.set_code
                        and p.collector_number == current_printing.collector_number
                    ):
                        self.run_worker(focus.sync_to_index(i))
                        break
        except NoMatches:
            pass

        self.current_view = ViewMode.FOCUS

    def action_switch_to_compare(self) -> None:
        """Switch to compare view."""
        self.current_view = ViewMode.COMPARE

    def action_toggle_art_crop(self) -> None:
        """Toggle art crop mode in current view."""
        try:
            if self.current_view == ViewMode.GALLERY:
                preview = self.query_one(f"#{self._id_prefix}-preview", PreviewPanel)
                preview.set_art_crop_mode(not preview.art_crop_enabled)
                mode = "Art crop" if preview.art_crop_enabled else "Full card"
                self.notify(mode, severity="information", timeout=1.5)
            else:
                focus = self.query_one(f"#{self._id_prefix}-focus", FocusView)
                focus.show_art_crop = not focus.show_art_crop
        except NoMatches:
            pass

    def action_navigate_left(self) -> None:
        """Navigate left in current view."""
        if self.current_view == ViewMode.GALLERY:
            grid = self.query_one(f"#{self._id_prefix}-grid", PrintingsGrid)
            grid.navigate("left")
        elif self.current_view == ViewMode.FOCUS:
            focus = self.query_one(f"#{self._id_prefix}-focus", FocusView)
            self.run_worker(focus.navigate("prev"))

    def action_navigate_right(self) -> None:
        """Navigate right in current view."""
        if self.current_view == ViewMode.GALLERY:
            grid = self.query_one(f"#{self._id_prefix}-grid", PrintingsGrid)
            grid.navigate("right")
        elif self.current_view == ViewMode.FOCUS:
            focus = self.query_one(f"#{self._id_prefix}-focus", FocusView)
            self.run_worker(focus.navigate("next"))

    def action_navigate_up(self) -> None:
        """Navigate up in grid."""
        if self.current_view == ViewMode.GALLERY:
            grid = self.query_one(f"#{self._id_prefix}-grid", PrintingsGrid)
            grid.navigate("up")

    def action_navigate_down(self) -> None:
        """Navigate down in grid."""
        if self.current_view == ViewMode.GALLERY:
            grid = self.query_one(f"#{self._id_prefix}-grid", PrintingsGrid)
            grid.navigate("down")

    def action_cycle_sort(self) -> None:
        """Cycle through sort orders in gallery view."""
        if self.current_view == ViewMode.GALLERY:
            grid = self.query_one(f"#{self._id_prefix}-grid", PrintingsGrid)
            grid.cycle_sort()

    def action_add_to_compare(self) -> None:
        """Add current selection to compare list."""

        async def _add_and_update() -> None:
            try:
                compare = self.query_one(f"#{self._id_prefix}-compare", CompareView)

                current_printing = None
                if self.current_view == ViewMode.GALLERY:
                    grid = self.query_one(f"#{self._id_prefix}-grid", PrintingsGrid)
                    current_printing = grid.get_current_printing()
                elif self.current_view == ViewMode.FOCUS:
                    focus = self.query_one(f"#{self._id_prefix}-focus", FocusView)
                    current_printing = focus.get_current_printing()

                if current_printing:
                    added = await compare.add_printing(current_printing)
                    if added:
                        if self.current_view == ViewMode.GALLERY:
                            grid = self.query_one(f"#{self._id_prefix}-grid", PrintingsGrid)
                            grid.mark_in_compare(current_printing)

                        # Auto-select next empty slot
                        current_count = len(compare.get_printings())
                        if current_count < CompareView.MAX_SLOTS:
                            self._compare_selected_slot = current_count + 1
                            compare.select_slot(self._compare_selected_slot)
                    else:
                        self.notify(
                            "Already in comparison or slots full", severity="warning", timeout=2
                        )
            except NoMatches:
                pass

        self.run_worker(_add_and_update())

    def action_remove_from_compare(self) -> None:
        """Remove selected slot from compare."""
        if self.current_view == ViewMode.COMPARE:
            try:
                compare = self.query_one(f"#{self._id_prefix}-compare", CompareView)
                self.run_worker(compare.remove_printing(self._compare_selected_slot))
            except NoMatches:
                pass

    def action_clear_compare(self) -> None:
        """Clear all comparison slots."""
        try:
            compare = self.query_one(f"#{self._id_prefix}-compare", CompareView)
            self.run_worker(compare.clear_all())
            grid = self.query_one(f"#{self._id_prefix}-grid", PrintingsGrid)
            grid.clear_compare_marks()
        except NoMatches:
            pass

    def action_select_slot_1(self) -> None:
        """Select comparison slot 1."""
        self._select_compare_slot(1)

    def action_select_slot_2(self) -> None:
        """Select comparison slot 2."""
        self._select_compare_slot(2)

    def action_select_slot_3(self) -> None:
        """Select comparison slot 3."""
        self._select_compare_slot(3)

    def action_select_slot_4(self) -> None:
        """Select comparison slot 4."""
        self._select_compare_slot(4)

    def _select_compare_slot(self, slot: int) -> None:
        """Select a comparison slot with visual feedback."""
        self._compare_selected_slot = slot
        try:
            compare = self.query_one(f"#{self._id_prefix}-compare", CompareView)
            compare.select_slot(slot)
        except NoMatches:
            pass

    def action_release_focus(self) -> None:
        """Handle escape - return to gallery or release focus to results list."""
        # If in Focus or Compare view, return to Gallery first
        if self.current_view in (ViewMode.FOCUS, ViewMode.COMPARE):
            self.current_view = ViewMode.GALLERY
            return

        # Already in Gallery - release focus to results list
        try:
            from textual.widgets import ListView

            results_list = self.app.query_one("#results-list", ListView)
            results_list.focus()
        except (LookupError, AttributeError):
            pass
