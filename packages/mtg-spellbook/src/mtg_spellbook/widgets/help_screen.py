"""Enhanced interactive help screen with feature guide."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.screen import ModalScreen
from textual.widgets import Button, ListItem, ListView, Static

from ..ui.theme import ui_colors

if TYPE_CHECKING:
    pass


@dataclass
class HelpCategory:
    """A help category with icon, label, and content."""

    icon: str
    label: str
    short_desc: str
    content: str
    action_label: str | None = None
    action_command: str | None = None


HELP_CATEGORIES: list[HelpCategory] = [
    HelpCategory(
        icon="🔍",
        label="Search",
        short_desc="Find any card",
        content=f"""[bold {ui_colors.GOLD}]Search for Cards[/]

Search for any of 33,000+ cards by name or attributes.

[bold {ui_colors.GOLD_DIM}]Basic Search[/]
  Type any card name directly:
  [dim]lightning bolt[/]
  [dim]black lotus[/]

[bold {ui_colors.GOLD_DIM}]Advanced Syntax[/]
  [{ui_colors.GOLD}]t:[/]type      Card type (creature, instant, etc.)
  [{ui_colors.GOLD}]c:[/]colors    Card colors (w, u, b, r, g)
  [{ui_colors.GOLD}]ci:[/]colors   Color identity
  [{ui_colors.GOLD}]cmc:[/]N       Converted mana cost
  [{ui_colors.GOLD}]f:[/]format    Format legality
  [{ui_colors.GOLD}]r:[/]rarity    Rarity (common, rare, mythic)
  [{ui_colors.GOLD}]set:[/]CODE    Set code (e.g., set:MH3)
  [{ui_colors.GOLD}]kw:[/]keyword  Keyword ability
  [{ui_colors.GOLD}]o:[/]text      Oracle text contains

[bold {ui_colors.GOLD_DIM}]Examples[/]
  [dim]t:dragon c:r cmc:5[/]     Red dragons, 5 CMC
  [dim]t:instant f:modern[/]    Modern-legal instants
  [dim]kw:flying r:mythic[/]    Mythic flyers""",
        action_label="Try Search",
        action_command="focus_search",
    ),
    HelpCategory(
        icon="🎨",
        label="Browse",
        short_desc="Art & printings",
        content=f"""[bold {ui_colors.GOLD}]Browse Card Art & Printings[/]

MTG Spellbook has 3 viewing modes for exploring cards:

[bold {ui_colors.GOLD_DIM}]📋 Gallery View[/] [dim](press g)[/]
  Filmstrip of all printings with preview
  • Navigate with ←→ or h/l
  • Press [bold]s[/] to cycle sort order
  • See prices at a glance

[bold {ui_colors.GOLD_DIM}]🖼 Focus View[/] [dim](press f)[/]
  Full-screen single card display
  • Rich metadata and prices
  • Press [bold]a[/] to toggle art crop
  • Press [bold]Enter[/] on artist to explore

[bold {ui_colors.GOLD_DIM}]⚖ Compare View[/] [dim](press c)[/]
  Side-by-side comparison (up to 4)
  • Press [bold]Space[/] to add current card
  • Press [bold]1-4[/] to select slot
  • Press [bold]x[/] to remove

[bold {ui_colors.GOLD_DIM}]Artist Portfolios[/]
  In Focus view, press Enter on the artist
  name to browse all their cards.""",
        action_label="Random Card",
        action_command="random",
    ),
    HelpCategory(
        icon="🔗",
        label="Synergy",
        short_desc="Find combos",
        content=f"""[bold {ui_colors.GOLD}]Card Synergies & Combos[/]

Discover cards that work well together.

[bold {ui_colors.GOLD_DIM}]Find Synergies[/]
  With a card selected, press [bold]Ctrl+S[/]
  or type: [dim]synergy <card name>[/]

  Synergies are detected by:
  • Tribal/type connections
  • Keyword interactions
  • Ability text patterns
  • Mana cost synergies

[bold {ui_colors.GOLD_DIM}]Find Combos[/]
  Press [bold]Ctrl+O[/] or type: [dim]combos <card name>[/]

  Shows known infinite combos and
  powerful card interactions.

[bold {ui_colors.GOLD_DIM}]Synergy Scores[/]
  [green]███████████[/] Strong (0.7+)
  [{ui_colors.GOLD}]███████░░░░[/] Moderate (0.4-0.7)
  [dim]████░░░░░░░[/] Weak (<0.4)""",
        action_label=None,
        action_command=None,
    ),
    HelpCategory(
        icon="📦",
        label="Sets",
        short_desc="Browse sets",
        content=f"""[bold {ui_colors.GOLD}]Browse Card Sets[/]

Explore Magic's history through its sets.

[bold {ui_colors.GOLD_DIM}]Commands[/]
  [{ui_colors.GOLD}]sets[/]           List all sets
  [{ui_colors.GOLD}]set <code>[/]     View set details
  [{ui_colors.GOLD}]blocks[/]         Browse by block

[bold {ui_colors.GOLD_DIM}]Set Details Include[/]
  • Release date and card count
  • Set symbol and type
  • All cards in the set
  • Price statistics

[bold {ui_colors.GOLD_DIM}]Navigation[/]
  Use ↑↓ to browse sets
  Press Enter to view details
  Press Esc to go back

[bold {ui_colors.GOLD_DIM}]Set Types[/]
  • Core Sets (M21, M20, etc.)
  • Expansion Sets (MH3, ONE, etc.)
  • Masters Sets (2XM, MMA, etc.)
  • Commander Products
  • Secret Lair Drops""",
        action_label="Browse Sets",
        action_command="sets",
    ),
    HelpCategory(
        icon="🎲",
        label="Random",
        short_desc="Discover cards",
        content=f"""[bold {ui_colors.GOLD}]Random Card Discovery[/]

Get inspired with random cards!

[bold {ui_colors.GOLD_DIM}]Quick Random[/]
  Press [bold]Ctrl+R[/] anywhere
  or type: [dim]random[/]

[bold {ui_colors.GOLD_DIM}]Use Cases[/]
  • Discover forgotten cards
  • Find deck inspiration
  • Learn new interactions
  • Challenge yourself

[bold {ui_colors.GOLD_DIM}]After Random Card[/]
  • Press [bold]g[/] for gallery view
  • Press [bold]Ctrl+S[/] for synergies
  • Press [bold]Ctrl+E[/] to add to deck

[dim]Tip: Random cards are great for
breaking out of deckbuilding ruts![/]""",
        action_label="Random Card",
        action_command="random",
    ),
    HelpCategory(
        icon="🗂",
        label="Decks",
        short_desc="Build decks",
        content=f"""[bold {ui_colors.GOLD}]Deck Building[/]

Build and manage your deck collections.

[bold {ui_colors.GOLD_DIM}]Quick Actions[/]
  [bold]Ctrl+D[/]  Toggle deck panel
  [bold]Ctrl+E[/]  Add current card to deck

[bold {ui_colors.GOLD_DIM}]Deck Panel Features[/]
  • Create new decks
  • Set format (Commander, Modern, etc.)
  • View mana curve
  • Check color distribution
  • See total price

[bold {ui_colors.GOLD_DIM}]Deck Analysis[/]
  • Mana curve visualization
  • Color balance chart
  • Card type breakdown
  • Format legality check

[bold {ui_colors.GOLD_DIM}]Export Formats[/]
  • Plain text list
  • Moxfield compatible
  • MTGO format
  • Arena format""",
        action_label="Open Decks",
        action_command="toggle_deck",
    ),
    HelpCategory(
        icon="📚",
        label="Collection",
        short_desc="Track cards",
        content=f"""[bold {ui_colors.GOLD}]Collection Tracking[/]

Track your owned cards and wishlist.

[bold {ui_colors.GOLD_DIM}]Quick Actions[/]
  [bold]Ctrl+C[/]  Open collection view
  [bold]w[/]       Add to wishlist

[bold {ui_colors.GOLD_DIM}]Collection Features[/]
  • Track regular and foil copies
  • Multiple printings per card
  • Search your collection
  • Filter by set, color, type

[bold {ui_colors.GOLD_DIM}]Import/Export[/]
  • Import from CSV
  • Export to spreadsheet
  • Moxfield sync
  • Backup collection

[bold {ui_colors.GOLD_DIM}]Statistics[/]
  • Total collection value
  • Cards by color/type
  • Completion percentage
  • Missing cards for decks""",
        action_label="View Collection",
        action_command="collection",
    ),
    HelpCategory(
        icon="⌨",
        label="Keys",
        short_desc="All shortcuts",
        content=f"""[bold {ui_colors.GOLD}]Keyboard Shortcuts[/]

[bold {ui_colors.GOLD_DIM}]Global[/]
  [bold]Esc[/]       Focus search / go back
  [bold]Ctrl+C[/]    Quit application
  [bold]Ctrl+L[/]    Clear display
  [bold]?[/]         This help screen

[bold {ui_colors.GOLD_DIM}]Navigation[/]
  [bold]↑↓[/] or [bold]j/k[/]   Move up/down
  [bold]←→[/] or [bold]h/l[/]   Move left/right
  [bold]Enter[/]     Select / confirm
  [bold]Tab[/]       Switch panels

[bold {ui_colors.GOLD_DIM}]Card Actions[/]
  [bold]Ctrl+S[/]    Find synergies
  [bold]Ctrl+O[/]    Find combos
  [bold]Ctrl+A[/]    Art gallery
  [bold]Ctrl+P[/]    Price info
  [bold]Ctrl+R[/]    Random card
  [bold]Ctrl+E[/]    Add to deck

[bold {ui_colors.GOLD_DIM}]View Modes[/]
  [bold]g[/]         Gallery view
  [bold]f[/]         Focus view
  [bold]c[/]         Compare view
  [bold]a[/]         Toggle art crop""",
        action_label=None,
        action_command=None,
    ),
]


class HelpCategoryItem(ListItem):
    """A help category list item."""

    def __init__(self, category: HelpCategory, index: int) -> None:
        super().__init__()
        self.category = category
        self.category_index = index

    def compose(self) -> ComposeResult:
        yield Static(
            f"{self.category.icon} {self.category.label}",
            classes="help-category-label",
        )
        yield Static(
            f"[dim]{self.category.short_desc}[/]",
            classes="help-category-desc",
        )


class HelpScreen(ModalScreen[str | None]):
    """Enhanced interactive help screen."""

    BINDINGS: ClassVar[list[Binding]] = [  # type: ignore[assignment]
        Binding("escape,q", "close", "Close"),
        Binding("enter", "try_action", "Try It", show=False),
    ]

    CSS = """
    HelpScreen {
        align: center middle;
    }

    #help-dialog {
        width: 90%;
        height: 85%;
        max-width: 100;
        max-height: 40;
        background: $surface;
        border: thick $primary;
    }

    #help-header {
        width: 100%;
        height: 3;
        background: $primary-darken-2;
        padding: 0 2;
        content-align: center middle;
    }

    #help-content {
        width: 100%;
        height: 1fr;
    }

    #help-categories {
        width: 20;
        height: 100%;
        border-right: solid $primary-darken-1;
        padding: 0;
    }

    #help-categories ListView {
        width: 100%;
        height: 100%;
        background: transparent;
    }

    #help-categories ListItem {
        padding: 0 1;
        height: 3;
    }

    #help-categories ListItem:hover {
        background: $primary-darken-1;
    }

    #help-categories ListItem.-highlight {
        background: $primary;
    }

    .help-category-label {
        width: 100%;
        height: 1;
    }

    .help-category-desc {
        width: 100%;
        height: 1;
    }

    #help-detail {
        width: 1fr;
        height: 100%;
        padding: 1 2;
    }

    #help-detail-content {
        width: 100%;
        height: 1fr;
    }

    #help-detail-scroll {
        width: 100%;
        height: 100%;
    }

    #help-action-bar {
        width: 100%;
        height: 3;
        align: center middle;
        padding: 0 1;
    }

    #help-action-bar Button {
        margin: 0 1;
    }

    #help-footer {
        width: 100%;
        height: 2;
        background: $primary-darken-2;
        content-align: center middle;
        padding: 0 2;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._selected_index = 0

    def compose(self) -> ComposeResult:
        with Vertical(id="help-dialog"):
            yield Static(
                f"[bold {ui_colors.GOLD}]❓ Help & Features[/]",
                id="help-header",
            )
            with Horizontal(id="help-content"):
                with Vertical(id="help-categories"):
                    yield ListView(
                        *[HelpCategoryItem(cat, i) for i, cat in enumerate(HELP_CATEGORIES)],
                        id="help-list",
                    )
                with Vertical(id="help-detail"):
                    with VerticalScroll(id="help-detail-scroll"):
                        yield Static(
                            HELP_CATEGORIES[0].content,
                            id="help-detail-content",
                        )
                    with Horizontal(id="help-action-bar"):
                        if HELP_CATEGORIES[0].action_label:
                            yield Button(
                                f"{HELP_CATEGORIES[0].action_label} →",
                                variant="primary",
                                id="help-action-btn",
                            )
            yield Static(
                "[dim]↑↓ Navigate | Enter: Try it | Esc: Close[/]",
                id="help-footer",
            )

    def on_mount(self) -> None:
        """Focus the list on mount."""
        list_view = self.query_one("#help-list", ListView)
        list_view.focus()

    @on(ListView.Selected)
    def on_category_selected(self, event: ListView.Selected) -> None:
        """Update detail pane when category is selected."""
        if isinstance(event.item, HelpCategoryItem):
            self._selected_index = event.item.category_index
            self._update_detail(event.item.category)

    @on(ListView.Highlighted)
    def on_category_highlighted(self, event: ListView.Highlighted) -> None:
        """Update detail pane when category is highlighted."""
        if isinstance(event.item, HelpCategoryItem):
            self._selected_index = event.item.category_index
            self._update_detail(event.item.category)

    def _update_detail(self, category: HelpCategory) -> None:
        """Update the detail pane with category content."""
        content = self.query_one("#help-detail-content", Static)
        content.update(category.content)

        # Update action button visibility and text
        try:
            btn = self.query_one("#help-action-btn", Button)
            if category.action_label:
                btn.label = f"{category.action_label} →"
                btn.display = True
            else:
                btn.display = False
        except NoMatches:
            pass

    @on(Button.Pressed, "#help-action-btn")
    def on_action_pressed(self) -> None:
        """Handle action button press."""
        self._execute_action()

    def action_try_action(self) -> None:
        """Execute the current category's action."""
        self._execute_action()

    def _execute_action(self) -> None:
        """Execute the action for the current category."""
        category = HELP_CATEGORIES[self._selected_index]
        if category.action_command:
            self.dismiss(category.action_command)
        else:
            self.app.notify("No action for this category", severity="information")

    def action_close(self) -> None:
        """Close the help screen."""
        self.dismiss(None)
