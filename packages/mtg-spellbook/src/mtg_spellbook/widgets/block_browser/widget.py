"""BlockBrowser widget for browsing MTG blocks with tree structure."""

from __future__ import annotations

from typing import ClassVar, cast

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.reactive import reactive
from textual.widgets import Static, Tree
from textual.widgets.tree import TreeNode

from mtg_core.data.models.responses import BlockSummary, SetSummary

from ...ui.theme import ui_colors
from .messages import BlockBrowserClosed, BlockSelected, SetFromBlockSelected


class BlockBrowser(Vertical, can_focus=True):
    """Browser for exploring MTG blocks organized by storyline."""

    BINDINGS: ClassVar[list[Binding]] = [  # type: ignore[assignment]
        Binding("escape,q", "close", "Close"),
        Binding("enter,space", "select_item", "Select/Expand"),
        Binding("up,k", "cursor_up", "Up", show=False),
        Binding("down,j", "cursor_down", "Down", show=False),
    ]

    is_loading: reactive[bool] = reactive(False)
    total_blocks: reactive[int] = reactive(0)

    def __init__(
        self,
        *,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self._blocks: list[BlockSummary] = []
        self._block_nodes: dict[str, TreeNode[BlockSummary]] = {}

    def compose(self) -> ComposeResult:
        with Vertical(classes="block-browser-container"):
            yield Static(
                self._render_header(),
                id="block-browser-title",
                classes="block-browser-title",
            )

            with Horizontal(classes="block-browser-content"):
                yield VerticalScroll(
                    Tree[BlockSummary | SetSummary](
                        "Blocks",
                        id="block-tree",
                        classes="block-tree",
                    ),
                    classes="block-tree-container",
                )
                yield VerticalScroll(
                    Static("", id="block-info", classes="block-info"),
                    classes="block-info-container",
                )

            yield Static(
                self._render_statusbar(),
                id="block-statusbar",
                classes="block-statusbar",
            )

    def on_mount(self) -> None:
        """Focus the tree on mount."""
        try:
            tree = self.query_one("#block-tree", Tree)
            tree.focus()
        except NoMatches:
            pass

    def _render_header(self) -> str:
        """Render header text."""
        return f"[bold {ui_colors.GOLD}]Block Browser[/]  [dim]({self.total_blocks} blocks)[/]"

    def _render_statusbar(self) -> str:
        """Render status bar."""
        parts = [
            f"[{ui_colors.TEXT_DIM}]jk/arrows: navigate[/]",
            f"[{ui_colors.GOLD}]Enter[/]: expand/select",
            f"[{ui_colors.GOLD}]Esc[/]: close",
        ]
        return "  |  ".join(parts)

    def _update_header(self) -> None:
        """Update header display."""
        try:
            title = self.query_one("#block-browser-title", Static)
            title.update(self._render_header())
        except NoMatches:
            pass

    async def load_blocks(self, blocks: list[BlockSummary]) -> None:
        """Load blocks and display in the tree."""
        self.is_loading = True
        self._blocks = blocks
        self.total_blocks = len(blocks)

        try:
            tree = self.query_one("#block-tree", Tree)
            tree.clear()
            tree.root.expand()

            # Group blocks by decade for better organization
            decades: dict[str, list[BlockSummary]] = {}
            for block in blocks:
                decade = block.first_release[:3] + "0s" if block.first_release else "Unknown"
                if decade not in decades:
                    decades[decade] = []
                decades[decade].append(block)

            # Add blocks sorted by decade (newest first)
            for decade in sorted(decades.keys(), reverse=True):
                decade_label = f"[bold {ui_colors.TEXT_DIM}]{decade}[/]"
                decade_node = tree.root.add(decade_label, expand=True)

                for block in decades[decade]:
                    # Create block label with stats
                    year_range = ""
                    if block.first_release and block.last_release:
                        start_year = block.first_release[:4]
                        end_year = block.last_release[:4]
                        if start_year == end_year:
                            year_range = f"({start_year})"
                        else:
                            year_range = f"({start_year}-{end_year})"

                    block_label = (
                        f"[bold]{block.name}[/]  "
                        f"[cyan]{block.set_count}[/] sets  "
                        f"[dim]{block.total_cards} cards[/]  "
                        f"[dim]{year_range}[/]"
                    )

                    block_node = decade_node.add(block_label, data=block)
                    self._block_nodes[block.name] = block_node

                    # Add sets as children (collapsed by default)
                    for set_summary in block.sets:
                        set_label = (
                            f"[cyan]{set_summary.code.upper()}[/] "
                            f"{set_summary.name}  "
                            f"[dim]({set_summary.release_date or '?'})[/]"
                        )
                        block_node.add_leaf(set_label, data=set_summary)

            self._update_header()

        finally:
            self.is_loading = False

    def on_tree_node_selected(self, event: Tree.NodeSelected[BlockSummary | SetSummary]) -> None:
        """Handle tree node selection."""
        node = event.node
        data = node.data

        if data is None:
            return

        # Check if it's a BlockSummary or SetSummary
        if hasattr(data, "sets"):
            # BlockSummary - show info panel
            block = cast(BlockSummary, data)
            self._show_block_info(block)
            self.post_message(BlockSelected(block))
        elif hasattr(data, "code"):
            # SetSummary - navigate to set
            set_summary: SetSummary = data
            # Find parent block name
            parent = node.parent
            block_name = ""
            while parent and parent.data is None:
                parent = parent.parent
            if parent and parent.data is not None and hasattr(parent.data, "name"):
                block_name = parent.data.name
            self.post_message(SetFromBlockSelected(set_summary, block_name))

    def on_tree_node_expanded(self, event: Tree.NodeExpanded[BlockSummary | SetSummary]) -> None:
        """Handle tree node expansion."""
        node = event.node
        data = node.data

        if data is not None and hasattr(data, "sets"):
            block = cast(BlockSummary, data)
            self._show_block_info(block)

    def _show_block_info(self, block: BlockSummary) -> None:
        """Show block information in the info panel."""
        try:
            info = self.query_one("#block-info", Static)

            lines = [
                f"[bold {ui_colors.GOLD}]{block.name}[/]",
                "",
                f"[{ui_colors.TEXT_DIM}]Sets:[/] {block.set_count}",
                f"[{ui_colors.TEXT_DIM}]Total Cards:[/] {block.total_cards}",
            ]

            if block.first_release:
                lines.append(f"[{ui_colors.TEXT_DIM}]First Release:[/] {block.first_release}")
            if block.last_release:
                lines.append(f"[{ui_colors.TEXT_DIM}]Last Release:[/] {block.last_release}")

            lines.append("")
            lines.append(f"[bold {ui_colors.GOLD_DIM}]Sets in Block:[/]")

            for set_summary in block.sets:
                lines.append(f"  [cyan]{set_summary.code.upper()}[/] {set_summary.name}")

            info.update("\n".join(lines))
        except NoMatches:
            pass

    def action_close(self) -> None:
        """Close the browser."""
        self.post_message(BlockBrowserClosed())

    def action_select_item(self) -> None:
        """Select or expand current item."""
        try:
            tree = self.query_one("#block-tree", Tree)
            node = tree.cursor_node
            if node:
                if node.is_expanded:
                    node.collapse()
                else:
                    node.expand()
        except NoMatches:
            pass

    def action_cursor_up(self) -> None:
        """Move cursor up."""
        try:
            tree = self.query_one("#block-tree", Tree)
            tree.action_cursor_up()
        except NoMatches:
            pass

    def action_cursor_down(self) -> None:
        """Move cursor down."""
        try:
            tree = self.query_one("#block-tree", Tree)
            tree.action_cursor_down()
        except NoMatches:
            pass
