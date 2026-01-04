"""Full-screen deck suggestions view."""

from __future__ import annotations

import contextlib
import hashlib
from dataclasses import dataclass
from typing import ClassVar

from pydantic import BaseModel
from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.css.query import NoMatches
from textual.widgets import Button, Checkbox, Input, ListItem, ListView, Select, Static

from mtg_core.tools.recommendations import (
    ComboSummary,
    DeckFilters,
    DeckSuggestion,
)
from mtg_core.tools.recommendations.constants import THEME_KEYWORDS, TRIBAL_TYPES

from ..screens import BaseScreen
from ..ui.theme import ui_colors

# Cache namespace for deck suggestions
SUGGESTIONS_CACHE_NAMESPACE = "deck_suggestions"
SUGGESTIONS_CACHE_TTL_DAYS = 1  # Suggestions expire after 1 day


class CachedComboSummary(BaseModel):
    """Pydantic version of ComboSummary for caching."""

    id: str
    cards: list[str]
    missing_cards: list[str]
    produces: list[str]
    bracket: str
    score: float
    completion_pct: float


class CachedDeckSuggestion(BaseModel):
    """Pydantic version of DeckSuggestion for caching."""

    name: str
    format: str
    commander: str | None = None
    archetype: str | None = None
    colors: list[str] = []
    key_cards_owned: list[str] = []
    key_cards_missing: list[str] = []
    completion_pct: float = 0.0
    estimated_cost: float = 0.0
    reasons: list[str] = []
    near_combos: list[CachedComboSummary] = []
    complete_combos: list[CachedComboSummary] = []
    combo_score: float = 0.0
    limited_bombs: list[str] = []
    filter_reasons: list[str] = []
    # Phase 10: Quality metrics
    curve_warnings: list[str] = []
    interaction_count: int = 0
    quality_score: float = 0.0
    mana_base_quality: str = ""
    fixing_land_count: int = 0
    win_condition_types: list[str] = []
    tribal_strength: str = ""
    theme_strength: str = ""


class CachedDeckSuggestions(BaseModel):
    """Container for caching deck suggestions."""

    suggestions: list[CachedDeckSuggestion]
    format: str
    collection_hash: str  # Hash of collection to detect changes
    filter_hash: str  # Hash of filters applied


def _collection_hash(card_names: set[str]) -> str:
    """Generate hash of collection for cache invalidation."""
    sorted_names = sorted(card_names)
    return hashlib.sha256("|".join(sorted_names).encode()).hexdigest()[:16]


def _filter_hash(filters: DeckFilters | None) -> str:
    """Generate hash of filters for cache key."""
    if not filters:
        return "none"
    parts = [
        ",".join(sorted(filters.colors or [])),
        filters.creature_type or "",
        filters.theme or "",
        filters.keyword or "",
        str(filters.owned_only),
    ]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:12]


def _to_cached_combo(combo: ComboSummary) -> CachedComboSummary:
    """Convert ComboSummary to cached version."""
    return CachedComboSummary(
        id=combo.id,
        cards=combo.cards,
        missing_cards=combo.missing_cards,
        produces=combo.produces,
        bracket=combo.bracket,
        score=combo.score,
        completion_pct=combo.completion_pct,
    )


def _to_cached_suggestion(s: DeckSuggestion) -> CachedDeckSuggestion:
    """Convert DeckSuggestion to cached version."""
    return CachedDeckSuggestion(
        name=s.name,
        format=s.format,
        commander=s.commander,
        archetype=s.archetype,
        colors=s.colors,
        key_cards_owned=s.key_cards_owned,
        key_cards_missing=s.key_cards_missing,
        completion_pct=s.completion_pct,
        estimated_cost=s.estimated_cost,
        reasons=s.reasons,
        near_combos=[_to_cached_combo(c) for c in s.near_combos],
        complete_combos=[_to_cached_combo(c) for c in s.complete_combos],
        combo_score=s.combo_score,
        limited_bombs=s.limited_bombs,
        filter_reasons=s.filter_reasons,
        # Phase 10 quality metrics
        curve_warnings=s.curve_warnings,
        interaction_count=s.interaction_count,
        quality_score=s.quality_score,
        mana_base_quality=s.mana_base_quality,
        fixing_land_count=s.fixing_land_count,
        win_condition_types=s.win_condition_types,
        tribal_strength=s.tribal_strength,
        theme_strength=s.theme_strength,
    )


def _from_cached_combo(c: CachedComboSummary) -> ComboSummary:
    """Convert cached combo back to ComboSummary."""
    return ComboSummary(
        id=c.id,
        cards=c.cards,
        missing_cards=c.missing_cards,
        produces=c.produces,
        bracket=c.bracket,
        score=c.score,
        completion_pct=c.completion_pct,
    )


def _from_cached_suggestion(c: CachedDeckSuggestion) -> DeckSuggestion:
    """Convert cached suggestion back to DeckSuggestion."""
    return DeckSuggestion(
        name=c.name,
        format=c.format,
        commander=c.commander,
        archetype=c.archetype,
        colors=c.colors,
        key_cards_owned=c.key_cards_owned,
        key_cards_missing=c.key_cards_missing,
        completion_pct=c.completion_pct,
        estimated_cost=c.estimated_cost,
        reasons=c.reasons,
        near_combos=[_from_cached_combo(x) for x in c.near_combos],
        complete_combos=[_from_cached_combo(x) for x in c.complete_combos],
        combo_score=c.combo_score,
        limited_bombs=c.limited_bombs,
        filter_reasons=c.filter_reasons,
        # Phase 10 quality metrics
        curve_warnings=c.curve_warnings,
        interaction_count=c.interaction_count,
        quality_score=c.quality_score,
        mana_base_quality=c.mana_base_quality,
        fixing_land_count=c.fixing_land_count,
        win_condition_types=c.win_condition_types,
        tribal_strength=c.tribal_strength,
        theme_strength=c.theme_strength,
    )


@dataclass
class CollectionCardInfo:
    """Card info passed to deck suggestions."""

    name: str
    type_line: str | None = None
    colors: list[str] | None = None
    mana_cost: str | None = None
    text: str | None = None
    color_identity: list[str] | None = None
    set_code: str | None = None  # Set code for filtering art/token sets


@dataclass
class CreateDeckResult:
    """Result when creating a deck from suggestion."""

    deck_name: str
    card_names: list[str]  # Cards user owns
    cards_missing: list[str] | None = None  # Cards to acquire (e.g., basic lands)
    commander: str | None = None
    format_type: str = "commander"


class SuggestionListItem(ListItem):
    """ListItem that stores a deck suggestion."""

    def __init__(self, suggestion: DeckSuggestion, content: str) -> None:
        super().__init__()
        self.suggestion = suggestion
        self._content = content

    def compose(self) -> ComposeResult:
        yield Static(self._content)


class DeckSuggestionsScreen(BaseScreen[CreateDeckResult | None]):
    """Full-screen deck suggestions based on collection.

    Shows what decks can be built from the user's collection.
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape,q", "close", "Back", show=True),
        Binding("g", "generate", "Generate", show=True),
        Binding("c", "show_commander", "Commander", show=True),
        Binding("s", "show_standard", "Standard", show=True),
        Binding("space", "toggle_expand", "Expand", show=True),
        Binding("enter", "create_deck", "Create", show=True),
        Binding("up,k", "nav_up", "Up", show=False),
        Binding("down,j", "nav_down", "Down", show=False),
        Binding("pageup", "page_up", show=False),
        Binding("pagedown", "page_down", show=False),
    ]

    # Don't show footer - this screen has its own status bar
    show_footer: ClassVar[bool] = False

    CSS = """
    DeckSuggestionsScreen {
        background: #0d0d0d;
    }

    /* Override screen-content to use grid for proper height distribution */
    DeckSuggestionsScreen #screen-content {
        layout: grid;
        grid-size: 1;
        grid-rows: 3 3 auto 1fr 2;  /* header, format-bar, filter-bar, list, statusbar */
    }

    #suggestions-header {
        background: #0a0a14;
        border-bottom: heavy #c9a227;
        padding: 0 2;
        content-align: center middle;
    }

    #format-bar {
        background: #121218;
        padding: 0 2;
        border-bottom: solid #2a2a4e;
    }

    .format-btn {
        width: 14;
        height: 3;
        margin: 0 1 0 0;
        background: #1a1a2e;
        border: solid #3d3d3d;
    }

    .format-btn:hover {
        background: #2a2a4e;
    }

    .format-btn.-active {
        background: #c9a227;
        color: #0a0a14;
        text-style: bold;
    }

    /* Filter bar */
    #filter-bar {
        background: #0f0f18;
        padding: 1 2;
        border-bottom: solid #2a2a4e;
        height: auto;
    }

    #filter-row-1, #filter-row-2 {
        height: auto;
        margin-bottom: 1;
    }

    #filter-row-1, #filter-row-2 {
        height: auto;
        align: left middle;
    }

    #filter-row-1 {
        margin-bottom: 1;
    }

    .filter-label {
        width: auto;
        height: 3;
        content-align: left middle;
        padding: 0 1;
    }

    .color-toggle {
        width: 5;
        height: 3;
        min-width: 5;
        margin: 0;
        padding: 0;
        background: #2a2a3e;
        border: solid #444;
        text-align: center;
        content-align: center middle;
    }
    .color-toggle:hover { background: #3a3a4e; }
    .color-toggle.-on { border: solid $primary; text-style: bold; }
    .color-toggle.-W.-on { background: #f8f6d8; color: #1a1a1a; }
    .color-toggle.-U.-on { background: #0e68ab; color: white; }
    .color-toggle.-B.-on { background: #3a3a3a; color: white; }
    .color-toggle.-R.-on { background: #d3202a; color: white; }
    .color-toggle.-G.-on { background: #00733e; color: white; }

    #tribal-select {
        width: 24;
        height: 3;
        margin-left: 1;
    }

    #theme-select {
        width: 20;
        height: 3;
        margin-left: 1;
    }

    #keyword-input {
        width: 20;
        height: 3;
        margin-left: 1;
    }

    #apply-filters-btn {
        width: 10;
        height: 3;
        margin-left: 2;
        background: #c9a227;
        color: #0a0a14;
    }

    #clear-filters-btn {
        width: 8;
        height: 3;
        margin-left: 1;
        background: #333;
    }

    #suggestions-list {
        width: 100%;
        height: 1fr;
        scrollbar-color: #c9a227;
    }

    #suggestions-list > ListItem {
        height: auto;
        min-height: 4;
        padding: 1 2;
        background: #121212;
        border-bottom: solid #2a2a4e;
    }

    #suggestions-list > ListItem:hover {
        background: #1a1a2e;
    }

    #suggestions-list > ListItem.-highlight {
        background: #2a2a4e;
        border-left: heavy #c9a227;
    }

    #suggestions-statusbar {
        padding: 0 2;
        background: #1a1a1a;
        border-top: solid #3d3d3d;
        content-align: left middle;
    }

    #empty-state {
        width: 100%;
        height: 100%;
        content-align: center middle;
        text-align: center;
    }
    """

    def __init__(
        self,
        card_info_list: list[CollectionCardInfo],
        existing_deck_names: set[str] | None = None,
    ) -> None:
        super().__init__()
        self._card_info_list = card_info_list
        self._collection_cards = {c.name for c in card_info_list}
        self._collection_hash = _collection_hash(self._collection_cards)
        self._existing_deck_names = existing_deck_names or set()
        self._current_format = "commander"
        self._suggestions: list[DeckSuggestion] = []
        self._selected_suggestion: DeckSuggestion | None = None
        # Filter state
        self._active_colors: set[str] = set()
        self._selected_tribal: str | None = None
        self._selected_theme: str | None = None
        self._keyword: str = ""
        self._owned_only: bool = True  # Default: only suggest owned cards
        # Loading state
        self._is_generating: bool = False
        self._has_loaded_cache: bool = False
        # Expansion state - tracks which suggestions are expanded (by name)
        self._expanded_suggestions: set[str] = set()

    def compose_content(self) -> ComposeResult:
        yield Static(
            f"[bold {ui_colors.GOLD}]SUGGEST DECKS[/]  "
            f"[{ui_colors.TEXT_DIM}]({len(self._card_info_list)} cards in collection)[/]",
            id="suggestions-header",
        )

        with Horizontal(id="format-bar"):
            yield Button("Commander", id="btn-commander", classes="format-btn -active")
            yield Button("Standard", id="btn-standard", classes="format-btn")

        # Filter bar
        with Vertical(id="filter-bar"):
            with Horizontal(id="filter-row-1"):
                yield Static("Colors:", classes="filter-label")
                yield Button("W", id="color-W", classes="color-toggle -W")
                yield Button("U", id="color-U", classes="color-toggle -U")
                yield Button("B", id="color-B", classes="color-toggle -B")
                yield Button("R", id="color-R", classes="color-toggle -R")
                yield Button("G", id="color-G", classes="color-toggle -G")

                yield Static("Tribal:", classes="filter-label")
                tribal_options = [("Any", None)] + [(t, t) for t in TRIBAL_TYPES]
                yield Select(
                    tribal_options,
                    id="tribal-select",
                    prompt="Any",
                    allow_blank=True,
                )

            with Horizontal(id="filter-row-2"):
                yield Static("Theme:", classes="filter-label")
                theme_options = [("Any", None)] + [(t, t) for t in THEME_KEYWORDS]
                yield Select(
                    theme_options,
                    id="theme-select",
                    prompt="Any",
                    allow_blank=True,
                )

                yield Static("Keyword:", classes="filter-label")
                yield Input(placeholder="e.g. flying, dies", id="keyword-input")

                yield Checkbox("Owned only", id="owned-only-checkbox", value=True)

                yield Button("Apply", id="apply-filters-btn")
                yield Button("Clear", id="clear-filters-btn")

        yield ListView(id="suggestions-list")

        yield Static(self._render_statusbar(), id="suggestions-statusbar")

    async def on_mount(self) -> None:
        """Try to load cached suggestions on mount, otherwise show empty state."""
        try:
            list_view = self.query_one("#suggestions-list", ListView)
            list_view.focus()
        except NoMatches:
            pass

        # Try to load from cache - don't auto-generate
        self._load_cached_suggestions()

    def _get_cache_key(self) -> str:
        """Generate cache key based on format and collection."""
        return f"{self._current_format}_{self._collection_hash}"

    def _get_current_filters(self) -> DeckFilters:
        """Build filters from current UI state."""
        return DeckFilters(
            colors=list(self._active_colors) if self._active_colors else None,
            creature_type=self._selected_tribal,
            theme=self._selected_theme,
            keyword=self._keyword if self._keyword else None,
            owned_only=self._owned_only,
        )

    def _load_cached_suggestions(self) -> None:
        """Try to load suggestions from cache."""
        from mtg_core.cache import get_cached

        cache_key = self._get_cache_key()
        cached = get_cached(
            SUGGESTIONS_CACHE_NAMESPACE,
            cache_key,
            CachedDeckSuggestions,
            ttl_days=SUGGESTIONS_CACHE_TTL_DAYS,
        )

        if cached and cached.collection_hash == self._collection_hash:
            # Cache hit - convert back to DeckSuggestion
            suggestions = [_from_cached_suggestion(s) for s in cached.suggestions]
            # Filter out suggestions that match existing deck names
            if self._existing_deck_names:
                self._suggestions = [
                    s for s in suggestions if s.name not in self._existing_deck_names
                ]
            else:
                self._suggestions = suggestions
            self._has_loaded_cache = True
            self._populate_list()
        else:
            # No valid cache - show empty state with generate button
            self._suggestions = []
            self._has_loaded_cache = False
            self._populate_list()

    def _save_to_cache(self) -> None:
        """Save current suggestions to cache."""
        from mtg_core.cache import set_cached

        if not self._suggestions:
            return

        cache_key = self._get_cache_key()
        filters = self._get_current_filters()

        cached = CachedDeckSuggestions(
            suggestions=[_to_cached_suggestion(s) for s in self._suggestions],
            format=self._current_format,
            collection_hash=self._collection_hash,
            filter_hash=_filter_hash(filters),
        )

        set_cached(SUGGESTIONS_CACHE_NAMESPACE, cache_key, cached)

    @work(exclusive=True, group="generate_suggestions")
    async def _generate_suggestions(self) -> None:
        """Generate deck suggestions in background task."""
        from mtg_core.tools.recommendations import CardData, get_deck_finder

        if self._is_generating:
            return

        self._is_generating = True
        self._update_loading_state()
        self.notify(
            f"Generating {self._current_format} suggestions...",
            title="Analyzing Collection",
            timeout=3,
        )

        try:
            finder = get_deck_finder()

            # Convert card info to CardData
            card_data = [
                CardData(
                    name=c.name,
                    type_line=c.type_line,
                    colors=c.colors,
                    mana_cost=c.mana_cost,
                    text=c.text,
                    color_identity=c.color_identity,
                    set_code=c.set_code,
                )
                for c in self._card_info_list
            ]

            filters = self._get_current_filters()

            suggestions = await finder.find_buildable_decks(
                self._collection_cards,
                format=self._current_format,
                card_data=card_data,
                min_completion=0.1,
                limit=20,
                filters=filters,
            )

            # Filter out suggestions that match existing deck names
            if self._existing_deck_names:
                self._suggestions = [
                    s for s in suggestions if s.name not in self._existing_deck_names
                ]
            else:
                self._suggestions = suggestions

            # Save to cache for next time
            self._save_to_cache()
            self._has_loaded_cache = True

        finally:
            self._is_generating = False

        self._populate_list()

    def _update_loading_state(self) -> None:
        """Update UI to show loading state."""
        try:
            list_view = self.query_one("#suggestions-list", ListView)
            list_view.clear()
            list_view.append(
                ListItem(
                    Static(
                        f"[{ui_colors.GOLD}]⟳[/] Generating {self._current_format} suggestions...\n\n"
                        f"[{ui_colors.TEXT_DIM}]Analyzing collection, synergies, combos, and 17Lands data...[/]",
                        id="loading-state",
                    )
                )
            )
        except NoMatches:
            pass

    def _populate_list(self) -> None:
        """Populate the suggestions list."""
        try:
            list_view = self.query_one("#suggestions-list", ListView)
            # Clear existing items
            list_view.clear()

            if not self._suggestions:
                if self._is_generating:
                    # Show loading state
                    return

                if not self._has_loaded_cache:
                    # No cache loaded - show generate button
                    list_view.append(
                        ListItem(
                            Static(
                                f"\n[bold {ui_colors.GOLD}]Ready to Generate Suggestions[/]\n\n"
                                f"[{ui_colors.TEXT_DIM}]Press [bold]g[/] or click the button below to analyze your collection\n"
                                f"and find {self._current_format} decks you can build.[/]\n\n"
                                f"[{ui_colors.TEXT_DIM}]This may take a few seconds...[/]\n",
                                id="empty-state",
                            )
                        )
                    )
                else:
                    # Cache was loaded but no suggestions found
                    list_view.append(
                        ListItem(
                            Static(
                                f"[{ui_colors.TEXT_DIM}]No {self._current_format} decks found.\n\n"
                                "Try adjusting filters or add more cards to your collection!\n"
                                "Press [bold]g[/] to regenerate suggestions.[/]",
                                id="empty-state",
                            )
                        )
                    )
                self._selected_suggestion = None
                return

            for suggestion in self._suggestions:
                is_expanded = suggestion.name in self._expanded_suggestions
                content = self._format_suggestion(suggestion, expanded=is_expanded)
                item = SuggestionListItem(suggestion, content)
                list_view.append(item)

            # Force refresh
            list_view.refresh(layout=True)

            if self._suggestions:
                list_view.index = 0
                self._selected_suggestion = self._suggestions[0]

        except Exception as e:
            self.notify(f"ERROR populating list: {e}", severity="error", timeout=10)

    def _format_suggestion(self, s: DeckSuggestion, expanded: bool = False) -> str:
        """Format a suggestion for display.

        Args:
            s: The deck suggestion to format
            expanded: If True, show full details; if False, show compact view
        """
        # Color indicators
        color_str = " ".join(s.colors) if s.colors else ""

        # Completion percentage (capped at 100%)
        pct = min(100, int(s.completion_pct * 100))

        # Score color
        if s.completion_pct >= 0.7:
            score_color = ui_colors.SYNERGY_STRONG
        elif s.completion_pct >= 0.5:
            score_color = ui_colors.SYNERGY_MODERATE
        elif s.completion_pct >= 0.3:
            score_color = ui_colors.SYNERGY_WEAK
        else:
            score_color = ui_colors.TEXT_DIM

        # Power level (1-10)
        power = self._calculate_power_level(s)
        power_color = "red" if power >= 8 else "orange1" if power >= 5 else "green"

        # Quality grade (A-F based on quality_score)
        quality_grade, quality_color = self._get_quality_grade(s.quality_score)

        # Card counts
        owned_count = len(s.key_cards_owned) if s.key_cards_owned else 0
        missing_count = len(s.key_cards_missing) if s.key_cards_missing else 0

        # Combo counts
        complete_count = len(s.complete_combos) if s.complete_combos else 0
        near_count = len(s.near_combos) if s.near_combos else 0

        # Check for warnings
        has_warnings = bool(s.curve_warnings) or s.mana_base_quality in ("poor", "critical")

        lines = []

        # Line 1: ALL key metrics (name, colors, %, power, quality, own/need)
        expand_indicator = "▼" if expanded else "▶"
        line1 = f"[dim]{expand_indicator}[/] [bold {ui_colors.GOLD}]{s.name}[/]"
        if color_str:
            line1 += f"  {color_str}"
        line1 += f"  [{score_color}]{pct}%[/]"
        line1 += f"  [{power_color}]PWR {power}[/]"
        # Add quality grade badge
        if s.quality_score > 0:
            line1 += f"  [{quality_color}]{quality_grade}[/]"
        line1 += f"  [green]✓{owned_count}[/]"
        if missing_count > 0:
            line1 += f" [yellow]⚠{missing_count}[/]"
        lines.append(line1)

        # Line 2: Compact badges (combo + bombs + warnings + commander)
        badges = []
        # Single unified combo badge showing complete+near counts
        if complete_count > 0 or near_count > 0:
            combo_color = "red" if s.combo_score >= 0.7 else "cyan"
            if complete_count > 0 and near_count > 0:
                badges.append(f"[{combo_color}]⚡ {complete_count}+{near_count} combos[/]")
            elif complete_count > 0:
                badges.append(f"[{combo_color}]⚡ {complete_count} combo(s)[/]")
            else:
                badges.append(f"[dim]◐ {near_count} near[/]")
        if s.limited_bombs:
            badges.append(f"[yellow]💣 {len(s.limited_bombs)}[/]")
        # Show warnings indicator in collapsed view
        if not expanded and has_warnings:
            badges.append("[red]⚠ Issues[/]")
        # Show commander in collapsed view
        if not expanded and s.commander and s.commander != s.name:
            badges.append(f"[green]★ {s.commander}[/]")
        # Show estimated cost if available (collapsed view)
        if not expanded and s.estimated_cost > 0:
            badges.append(f"[dim]${s.estimated_cost:.0f}[/]")
        if badges:
            lines.append("  " + "  ".join(badges))

        # COLLAPSED VIEW: Stop here with hint
        if not expanded:
            lines.append(f"  [{ui_colors.TEXT_DIM}]Press space to expand...[/]")
            return "\n".join(lines)

        # EXPANDED VIEW: Full details below
        # Filter reasons (why this matches user's search)
        if s.filter_reasons:
            filter_str = " | ".join(s.filter_reasons)
            lines.append(f"  [cyan]🏷️ {filter_str}[/]")

        # Commander or archetype
        if s.commander and s.commander != s.name:
            lines.append(f"  [green]★ Commander:[/] {s.commander}")
        elif s.archetype:
            lines.append(f"  [{ui_colors.TEXT_DIM}]{s.archetype}[/]")

        # Card sections - simplified headers (counts shown in line 1)
        lines.append("")
        lines.append("  [bold green]✓ OWNED[/]")
        if s.key_cards_owned:
            shown = s.key_cards_owned[:5]
            for card in shown:
                lines.append(f"    [{ui_colors.TEXT_DIM}]{card}[/]")
            if len(s.key_cards_owned) > 5:
                lines.append(f"    [{ui_colors.TEXT_DIM}]... +{len(s.key_cards_owned) - 5} more[/]")

        if missing_count > 0:
            lines.append("")
            lines.append("  [bold yellow]⚠ NEEDED[/]")
            from collections import Counter

            missing_counts = Counter(s.key_cards_missing)
            for card, qty in list(missing_counts.items())[:5]:
                qty_str = f" x{qty}" if qty > 1 else ""
                lines.append(f"    [{ui_colors.TEXT_DIM}]{card}{qty_str}[/]")
            if len(missing_counts) > 5:
                lines.append(f"    [{ui_colors.TEXT_DIM}]... +{len(missing_counts) - 5} more[/]")

        # Combo section (Commander Spellbook integration)
        if s.complete_combos or s.near_combos:
            lines.append("")

            if s.complete_combos:
                lines.append(f"  [bold magenta]⚡ COMPLETE COMBOS ({len(s.complete_combos)})[/]")
                for combo in s.complete_combos[:2]:
                    produces_str = combo.produces[0] if combo.produces else "Combo"
                    bracket_color = self._bracket_color(combo.bracket)
                    lines.append(f"    [{bracket_color}][{combo.bracket}][/] {produces_str}")

            if s.near_combos:
                lines.append(f"  [bold cyan]◐ NEAR COMBOS ({len(s.near_combos)})[/]")
                for combo in s.near_combos[:3]:
                    produces_str = combo.produces[0] if combo.produces else "Combo"
                    missing = ", ".join(combo.missing_cards[:2])
                    bracket_color = self._bracket_color(combo.bracket)
                    lines.append(
                        f"    [{bracket_color}][{combo.bracket}][/] {produces_str}"
                        f" [dim](need: {missing})[/]"
                    )

        # Limited bombs section (17Lands S/A tier cards)
        if s.limited_bombs:
            lines.append("")
            lines.append(f"  [bold yellow]💣 LIMITED BOMBS ({len(s.limited_bombs)})[/]")
            for bomb in s.limited_bombs[:3]:
                lines.append(f"    [{ui_colors.TEXT_DIM}]{bomb}[/]")
            if len(s.limited_bombs) > 3:
                lines.append(f"    [{ui_colors.TEXT_DIM}]... +{len(s.limited_bombs) - 3} more[/]")

        # Deck Quality Analysis section (Phase 10/11)
        lines.append("")
        lines.append(f"  [bold {ui_colors.GOLD}]📊 DECK QUALITY[/]")

        # Quality grade with breakdown
        quality_parts = []
        if s.quality_score > 0:
            quality_parts.append(f"[{quality_color}]Grade: {quality_grade}[/]")
        if s.interaction_count > 0:
            interaction_color = (
                "green"
                if s.interaction_count >= 10
                else "yellow"
                if s.interaction_count >= 6
                else "red"
            )
            quality_parts.append(f"[{interaction_color}]Interaction: {s.interaction_count}[/]")
        if quality_parts:
            lines.append(f"    {' │ '.join(quality_parts)}")

        # Mana base quality
        if s.mana_base_quality:
            mana_color = (
                "green"
                if s.mana_base_quality == "excellent"
                else "yellow"
                if s.mana_base_quality == "good"
                else "red"
            )
            mana_str = f"[{mana_color}]Mana Base: {s.mana_base_quality.title()}[/]"
            if s.fixing_land_count > 0:
                mana_str += f" ({s.fixing_land_count} fixing lands)"
            lines.append(f"    {mana_str}")

        # Win conditions
        if s.win_condition_types:
            win_str = ", ".join(s.win_condition_types[:3])
            lines.append(f"    [cyan]Win Cons:[/] {win_str}")

        # Synergy strengths
        strength_parts = []
        if s.tribal_strength and s.tribal_strength != "minimal":
            tribal_color = (
                "green"
                if s.tribal_strength == "strong"
                else "yellow"
                if s.tribal_strength == "viable"
                else "dim"
            )
            strength_parts.append(f"[{tribal_color}]Tribal: {s.tribal_strength.title()}[/]")
        if s.theme_strength and s.theme_strength != "minimal":
            theme_color = (
                "green"
                if s.theme_strength == "strong"
                else "yellow"
                if s.theme_strength == "viable"
                else "dim"
            )
            strength_parts.append(f"[{theme_color}]Theme: {s.theme_strength.title()}[/]")
        if strength_parts:
            lines.append(f"    {' │ '.join(strength_parts)}")

        # Curve warnings
        if s.curve_warnings:
            lines.append("")
            lines.append("  [bold red]⚠ WARNINGS[/]")
            for warning in s.curve_warnings[:3]:
                lines.append(f"    [red]• {warning}[/]")

        # Power level breakdown (transparent calculation)
        lines.append("")
        lines.append(f"  [bold {ui_colors.GOLD}]⚔ POWER BREAKDOWN[/]")
        combo_pts = s.combo_score * 5
        completion_pts = s.completion_pct * 3
        bombs_pts = min(len(s.limited_bombs), 5) * 0.4
        lines.append(f"    Combo potential: {combo_pts:.1f}/5.0")
        lines.append(f"    Deck completion: {completion_pts:.1f}/3.0")
        lines.append(f"    Limited bombs:   {bombs_pts:.1f}/2.0")
        lines.append(f"    [bold]Total: PWR {power}[/]")

        # Estimated cost
        if s.estimated_cost > 0:
            lines.append("")
            cost_color = (
                "green" if s.estimated_cost < 50 else "yellow" if s.estimated_cost < 200 else "red"
            )
            lines.append(f"  [{cost_color}]💰 Est. Cost: ${s.estimated_cost:.2f}[/]")

        return "\n".join(lines)

    def _bracket_color(self, bracket: str) -> str:
        """Get display color for bracket tag."""
        colors = {
            "R": "red",  # Ruthless/cEDH
            "S": "orange1",  # Spicy
            "P": "yellow",  # Precon
            "PA": "yellow",  # Precon Approachable
            "C": "green",  # Casual
        }
        return colors.get(bracket, "white")

    def _calculate_power_level(self, s: DeckSuggestion) -> int:
        """Calculate power level (1-10) from deck metrics."""
        # Components: combo potential (50%), completion (30%), bombs (20%)
        combo_component = s.combo_score * 5  # 0-5 points
        completion_component = s.completion_pct * 3  # 0-3 points
        bombs_component = min(len(s.limited_bombs), 5) * 0.4  # 0-2 points
        total = combo_component + completion_component + bombs_component
        return max(1, min(10, int(total) + 1))

    def _get_quality_grade(self, quality_score: float) -> tuple[str, str]:
        """Get letter grade and color for quality score.

        Args:
            quality_score: 0.0 to 1.0 quality rating

        Returns:
            Tuple of (grade, color) for display
        """
        if quality_score >= 0.9:
            return "A+", "green"
        elif quality_score >= 0.8:
            return "A", "green"
        elif quality_score >= 0.7:
            return "B+", "cyan"
        elif quality_score >= 0.6:
            return "B", "cyan"
        elif quality_score >= 0.5:
            return "C+", "yellow"
        elif quality_score >= 0.4:
            return "C", "yellow"
        elif quality_score >= 0.3:
            return "D", "orange1"
        else:
            return "F", "red"

    def _render_statusbar(self) -> str:
        """Render status bar with power and quality guides."""
        keys = [
            f"[{ui_colors.GOLD}]g[/]:Generate",
            f"[{ui_colors.GOLD}]Space[/]:Expand",
            f"[{ui_colors.GOLD}]Enter[/]:Create",
            f"[{ui_colors.GOLD}]Esc[/]:Back",
        ]
        power_guide = "[dim]PWR:[/] [green]1-3[/] Casual [orange1]4-7[/] Tuned [red]8-10[/] cEDH"
        quality_guide = "[dim]Quality:[/] [green]A[/] [cyan]B[/] [yellow]C[/] [red]D/F[/]"
        return "  ".join(keys) + "  │  " + power_guide + "  │  " + quality_guide

    @on(ListView.Highlighted, "#suggestions-list")
    def on_suggestion_highlighted(self, event: ListView.Highlighted) -> None:
        """Track selected suggestion."""
        if isinstance(event.item, SuggestionListItem):
            self._selected_suggestion = event.item.suggestion

    @on(ListView.Selected, "#suggestions-list")
    def on_suggestion_selected(self, event: ListView.Selected) -> None:
        """Create deck when Enter pressed on suggestion."""
        if isinstance(event.item, SuggestionListItem):
            self._selected_suggestion = event.item.suggestion
            self.action_create_deck()

    @on(Button.Pressed, "#btn-commander")
    def on_commander_btn(self) -> None:
        self._switch_format("commander")

    @on(Button.Pressed, "#btn-standard")
    def on_standard_btn(self) -> None:
        self._switch_format("standard")

    # Color filter toggle buttons
    @on(Button.Pressed, "#color-W")
    def on_color_w(self) -> None:
        self._toggle_color("W")

    @on(Button.Pressed, "#color-U")
    def on_color_u(self) -> None:
        self._toggle_color("U")

    @on(Button.Pressed, "#color-B")
    def on_color_b(self) -> None:
        self._toggle_color("B")

    @on(Button.Pressed, "#color-R")
    def on_color_r(self) -> None:
        self._toggle_color("R")

    @on(Button.Pressed, "#color-G")
    def on_color_g(self) -> None:
        self._toggle_color("G")

    def _toggle_color(self, color: str) -> None:
        """Toggle a color filter on/off."""
        btn = self.query_one(f"#color-{color}", Button)
        if color in self._active_colors:
            self._active_colors.discard(color)
            btn.remove_class("-on")
        else:
            self._active_colors.add(color)
            btn.add_class("-on")

    @on(Select.Changed, "#tribal-select")
    def on_tribal_changed(self, event: Select.Changed) -> None:
        """Handle tribal select change."""
        value = event.value
        self._selected_tribal = str(value) if value not in (None, Select.BLANK) else None

    @on(Select.Changed, "#theme-select")
    def on_theme_changed(self, event: Select.Changed) -> None:
        """Handle theme select change."""
        value = event.value
        self._selected_theme = str(value) if value not in (None, Select.BLANK) else None

    @on(Checkbox.Changed, "#owned-only-checkbox")
    def on_owned_only_changed(self, event: Checkbox.Changed) -> None:
        """Handle owned-only checkbox change."""
        self._owned_only = event.value

    @on(Button.Pressed, "#apply-filters-btn")
    def on_apply_filters(self) -> None:
        """Apply current filters and regenerate suggestions."""
        try:
            keyword_input = self.query_one("#keyword-input", Input)
            self._keyword = keyword_input.value.strip()
        except NoMatches:
            pass
        # Filters changed - regenerate (don't just load cache)
        self._generate_suggestions()

    @on(Button.Pressed, "#clear-filters-btn")
    def on_clear_filters(self) -> None:
        """Clear all filters and try cache or show empty state."""
        self._active_colors.clear()
        self._selected_tribal = None
        self._selected_theme = None
        self._keyword = ""
        self._owned_only = True  # Reset to default

        # Reset UI
        try:
            for color in ["W", "U", "B", "R", "G"]:
                btn = self.query_one(f"#color-{color}", Button)
                btn.remove_class("-on")
            self.query_one("#tribal-select", Select).value = Select.BLANK
            self.query_one("#theme-select", Select).value = Select.BLANK
            self.query_one("#keyword-input", Input).value = ""
            self.query_one("#owned-only-checkbox", Checkbox).value = True
        except NoMatches:
            pass

        # Try to load from cache with cleared filters
        self._load_cached_suggestions()

    def _switch_format(self, fmt: str) -> None:
        """Switch format and try to load from cache."""
        if self._current_format == fmt:
            return

        self._current_format = fmt

        try:
            cmd_btn = self.query_one("#btn-commander", Button)
            std_btn = self.query_one("#btn-standard", Button)

            if fmt == "commander":
                cmd_btn.add_class("-active")
                std_btn.remove_class("-active")
            else:
                std_btn.add_class("-active")
                cmd_btn.remove_class("-active")
        except NoMatches:
            pass

        # Try cache first for this format
        self._load_cached_suggestions()

    def action_close(self) -> None:
        """Close screen."""
        self.dismiss(None)

    def action_show_commander(self) -> None:
        self._switch_format("commander")

    def action_show_standard(self) -> None:
        self._switch_format("standard")

    def action_generate(self) -> None:
        """Generate deck suggestions."""
        if self._is_generating:
            self.notify("Already generating suggestions...", severity="warning")
            return
        self._generate_suggestions()

    def action_nav_up(self) -> None:
        with contextlib.suppress(NoMatches):
            self.query_one("#suggestions-list", ListView).action_cursor_up()

    def action_nav_down(self) -> None:
        with contextlib.suppress(NoMatches):
            self.query_one("#suggestions-list", ListView).action_cursor_down()

    def action_page_up(self) -> None:
        with contextlib.suppress(NoMatches):
            self.query_one("#suggestions-list", ListView).action_page_up()

    def action_page_down(self) -> None:
        with contextlib.suppress(NoMatches):
            self.query_one("#suggestions-list", ListView).action_page_down()

    def action_toggle_expand(self) -> None:
        """Toggle expansion of the selected suggestion."""
        if not self._selected_suggestion:
            return

        name = self._selected_suggestion.name

        # Toggle expansion state
        if name in self._expanded_suggestions:
            self._expanded_suggestions.discard(name)
        else:
            self._expanded_suggestions.add(name)

        # Update just the current item in the list
        try:
            list_view = self.query_one("#suggestions-list", ListView)
            if list_view.highlighted_child and isinstance(
                list_view.highlighted_child, SuggestionListItem
            ):
                # Re-render the content
                is_expanded = name in self._expanded_suggestions
                new_content = self._format_suggestion(
                    self._selected_suggestion, expanded=is_expanded
                )
                # Update the Static widget inside the ListItem
                static = list_view.highlighted_child.query_one(Static)
                static.update(new_content)
                list_view.highlighted_child._content = new_content
        except NoMatches:
            pass

    def action_create_deck(self) -> None:
        """Create deck from selected suggestion."""
        if not self._selected_suggestion:
            self.notify("Select a deck first", severity="warning")
            return

        s = self._selected_suggestion

        if not s.key_cards_owned and not s.key_cards_missing:
            self.notify("No cards in this suggestion", severity="warning")
            return

        result = CreateDeckResult(
            deck_name=s.name,
            card_names=s.key_cards_owned,
            cards_missing=s.key_cards_missing if s.key_cards_missing else None,
            commander=s.commander,
            format_type=self._current_format,
        )
        self.dismiss(result)
