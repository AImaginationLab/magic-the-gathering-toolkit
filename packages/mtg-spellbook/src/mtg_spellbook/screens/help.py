"""Help screen for MTG knowledge base - keywords, concepts, and rules."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Input, Label, ListItem, ListView, Static

from .base import BaseScreen

if TYPE_CHECKING:
    pass


class TopicSelected(Message):
    """Message sent when a topic is selected."""

    def __init__(self, topic_id: str) -> None:
        self.topic_id = topic_id
        super().__init__()


class KeywordSelected(Message):
    """Message sent when a keyword is selected."""

    def __init__(self, keyword: dict[str, Any]) -> None:
        self.keyword = keyword
        super().__init__()


class ConceptSelected(Message):
    """Message sent when a concept is selected."""

    def __init__(self, concept: dict[str, Any]) -> None:
        self.concept = concept
        super().__init__()


class TopicList(Vertical):
    """Left column: Topics navigation using ListView for keyboard/mouse interaction."""

    TOPICS: ClassVar[list[tuple[str, str, str]]] = [
        ("keywords", "Keywords", "Searchable glossary of all MTG keywords"),
        ("concepts", "Game Concepts", "Core rules and mechanics explained"),
        ("formats", "Format Guide", "Rules for different play formats"),
    ]

    def compose(self) -> ComposeResult:
        yield Static("[bold #c9a227]TOPICS[/]", classes="column-header")
        with ListView(id="topic-listview"):
            for topic_id, name, desc in self.TOPICS:
                yield ListItem(
                    Label(f"[bold]{name}[/]\n[dim]{desc}[/]"),
                    id=f"topic-{topic_id}",
                )

    @on(ListView.Selected, "#topic-listview")
    def on_topic_selected(self, event: ListView.Selected) -> None:
        """Handle topic selection."""
        if event.item and event.item.id:
            topic_id = event.item.id.replace("topic-", "")
            self.post_message(TopicSelected(topic_id))


class KeywordGlossary(Vertical):
    """Middle column: Searchable keyword list."""

    # Use reactive only for category (less frequent changes)
    selected_category = reactive("all")

    CATEGORIES: ClassVar[list[tuple[str, str]]] = [
        ("all", "All"),
        ("evergreen", "Evergreen"),
        ("combat", "Combat"),
        ("protection", "Protection"),
        ("timing", "Timing"),
        ("graveyard", "Graveyard"),
        ("cost", "Cost"),
    ]

    SEARCH_DEBOUNCE_MS: ClassVar[int] = 150

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.keywords: list[dict[str, Any]] = []
        self.filtered_keywords: list[dict[str, Any]] = []
        self.search_query: str = ""  # Not reactive - use debouncing instead
        self._search_task: asyncio.Task[None] | None = None
        self._populate_task: asyncio.Task[None] | None = None

    def compose(self) -> ComposeResult:
        yield Static("[bold #c9a227]KEYWORD GLOSSARY[/]", classes="column-header")
        yield Input(placeholder="Search keywords...", id="keyword-search")
        with Horizontal(id="category-filters"):
            for cat_id, cat_name in self.CATEGORIES:
                classes = "category-chip"
                if cat_id == "all":
                    classes += " category-active"
                yield Static(f"[{cat_name}]", classes=classes, id=f"cat-{cat_id}")
        yield ListView(id="keyword-list")

    def set_keywords(self, keywords: list[dict[str, Any]]) -> None:
        """Set keywords and refresh display."""
        self.keywords = keywords
        self._filter_and_display()

    def watch_selected_category(self, category: str) -> None:
        """React to category filter changes."""
        # Update chip visual states
        for cat_id, _ in self.CATEGORIES:
            try:
                chip = self.query_one(f"#cat-{cat_id}", Static)
                chip.remove_class("category-active")
                if cat_id == category:
                    chip.add_class("category-active")
            except Exception:
                pass
        self._filter_and_display()

    @on(Input.Changed, "#keyword-search")
    def on_search_changed(self, event: Input.Changed) -> None:
        """Handle search input with debouncing (same pattern as dashboard search)."""
        query = event.value.strip()

        # Cancel any existing search task
        if self._search_task is not None:
            self._search_task.cancel()
            self._search_task = None

        # Start debounced search
        self._search_task = asyncio.create_task(self._debounced_search(query))

    async def _debounced_search(self, query: str) -> None:
        """Execute search after debounce delay."""
        try:
            await asyncio.sleep(self.SEARCH_DEBOUNCE_MS / 1000)
        except asyncio.CancelledError:
            return

        self.search_query = query
        self._filter_and_display()

    def _filter_and_display(self) -> None:
        """Filter keywords and trigger async list population."""
        query = self.search_query.lower()
        category = self.selected_category

        filtered = []
        for kw in self.keywords:
            # Category filter
            if category == "evergreen" and not kw.get("evergreen", False):
                continue
            if category != "all" and category != "evergreen" and kw.get("category", "") != category:
                continue

            # Search filter
            if query:
                name_match = query in kw.get("name", "").lower()
                summary_match = query in kw.get("summary", "").lower()
                if not (name_match or summary_match):
                    continue

            filtered.append(kw)

        self.filtered_keywords = filtered
        # Use call_later to run async populate on main thread (same pattern as sets screen)
        self.call_later(self._populate_list_deferred)

    def _populate_list_deferred(self) -> None:
        """Defer to async populate method."""
        # Cancel previous populate task if running
        if self._populate_task is not None:
            self._populate_task.cancel()
        self._populate_task = asyncio.create_task(self._populate_list_async())

    async def _populate_list_async(self) -> None:
        """Populate the keyword list asynchronously (same pattern as sets screen)."""
        try:
            list_view = self.query_one("#keyword-list", ListView)
            await list_view.clear()

            for kw in self.filtered_keywords:
                name = kw.get("name", "")
                star = " [#ffd700]★[/]" if kw.get("evergreen", False) else ""
                summary = kw.get("summary", "")

                label = f"[bold]{name}[/]{star}\n[dim]{summary[:50]}{'...' if len(summary) > 50 else ''}[/]"
                await list_view.append(ListItem(Label(label), id=f"kw-{name.replace(' ', '-')}"))
        except Exception:
            pass

    @on(ListView.Selected, "#keyword-list")
    def on_keyword_selected(self, event: ListView.Selected) -> None:
        """Handle keyword selection."""
        if event.item and event.item.id:
            # Extract keyword name from item id
            kw_name = event.item.id.replace("kw-", "").replace("-", " ")
            for kw in self.filtered_keywords:
                if kw.get("name", "").lower() == kw_name.lower():
                    self.post_message(KeywordSelected(kw))
                    break

    def on_click(self, event: Any) -> None:
        """Handle clicks on category chips."""
        if hasattr(event, "widget") and hasattr(event.widget, "id"):
            widget_id = event.widget.id
            if widget_id and widget_id.startswith("cat-"):
                category = widget_id.replace("cat-", "")
                self.selected_category = category


class DetailPanel(ScrollableContainer):
    """Right column: Keyword/concept/format details."""

    def compose(self) -> ComposeResult:
        yield Static(
            "[dim]Select an item to view details[/]",
            id="detail-content",
        )

    def clear(self) -> None:
        """Clear the detail panel."""
        try:
            detail = self.query_one("#detail-content", Static)
            detail.update("[dim]Select an item to view details[/]")
        except Exception:
            pass

    def show_keyword(self, kw: dict[str, Any]) -> None:
        """Display keyword details with rich visual formatting."""
        name = kw.get("name", "")
        category = kw.get("category", "").title()
        is_evergreen = kw.get("evergreen", False)
        summary = kw.get("summary", "")
        rules_text = kw.get("rules_text", "")
        reminder = kw.get("reminder_text", "")
        tips = kw.get("tips", "")
        related = kw.get("related_mechanics", [])
        cards = kw.get("common_cards", [])

        # Build header with badge
        badge = "[on #ffd700][#000] ★ EVERGREEN [/][/] " if is_evergreen else ""
        cat_color = {
            "combat": "#ff6b6b",
            "protection": "#4ecdc4",
            "graveyard": "#9b59b6",
            "timing": "#3498db",
            "cost": "#f1c40f",
        }.get(kw.get("category", ""), "#888")

        content = f"""{badge}[bold #c9a227 on #1a1a2e]  {name.upper()}  [/]
[{cat_color}]■[/] [dim italic]{category}[/]
[dim]{"─" * 40}[/]

[#87ceeb bold]📜 Summary[/]
{summary}

[#98d982 bold]📖 Rules Text[/]
{rules_text}
"""
        if reminder:
            content += f"\n[#b39ddb bold]💭 Reminder[/]\n[italic]{reminder}[/]\n"

        if tips:
            content += f"\n[#ffd54f bold]💡 Pro Tip[/]\n[#ffd54f]{tips}[/]\n"

        if cards:
            card_list = " [dim]•[/] ".join(f"[#64b5f6]{c}[/]" for c in cards)
            content += f"\n[#64b5f6 bold]🃏 Common Cards[/]\n{card_list}\n"

        if related:
            rel_list = " [dim]→[/] ".join(f"[#4db6ac]{r}[/]" for r in related)
            content += f"\n[#4db6ac bold]🔗 Related[/]\n{rel_list}\n"

        try:
            detail = self.query_one("#detail-content", Static)
            detail.update(content)
        except Exception:
            pass

    def _format_content_text(self, text: str) -> str:
        """Format content text with styled numbered lists and bullet points."""
        import re

        lines = text.split("\n")
        formatted_lines = []

        for line in lines:
            stripped = line.strip()

            # Format numbered list items: "1. Item" -> styled
            num_match = re.match(r"^(\d+)\.\s+(.+)$", stripped)
            if num_match:
                num, item_text = num_match.groups()
                # Bold the step name if it contains " - "
                if " - " in item_text:
                    parts = item_text.split(" - ", 1)
                    item_text = f"[bold #64b5f6]{parts[0]}[/] - {parts[1]}"
                formatted_lines.append(f"  [#ffd700]{num}.[/] {item_text}")
                continue

            # Format bullet points: "- Item" -> styled
            if stripped.startswith("- "):
                item_text = stripped[2:]
                formatted_lines.append(f"    [#4db6ac]▸[/] {item_text}")
                continue

            # Format section headers like "Key points:"
            if stripped.endswith(":") and len(stripped) < 30:
                formatted_lines.append(f"\n[#ffb74d bold]{stripped}[/]")
                continue

            formatted_lines.append(line)

        return "\n".join(formatted_lines)

    def show_concept(self, concept: dict[str, Any]) -> None:
        """Display concept details with rich visual formatting."""
        name = concept.get("name", "")
        category = concept.get("category", "").title()
        summary = concept.get("summary", "")
        content_text = concept.get("content", "")
        related = concept.get("related", [])

        # Category color mapping
        cat_color = {
            "turn structure": "#e91e63",
            "zones": "#9c27b0",
            "combat": "#ff5722",
            "card types": "#2196f3",
            "mana": "#4caf50",
        }.get(concept.get("category", ""), "#888")

        # Format the content text with styled lists
        formatted_content = self._format_content_text(content_text)

        content = f"""[bold #c9a227 on #1a1a2e]  {name.upper()}  [/]
[{cat_color}]●[/] [dim italic]{category}[/]
[dim]{"─" * 40}[/]

[#87ceeb bold]■ Overview[/]
{summary}

[#a5d6a7 bold]■ Details[/]
{formatted_content}
"""
        if related:
            rel_list = " [dim]→[/] ".join(f"[#ce93d8]{r}[/]" for r in related)
            content += f"\n[#ce93d8 bold]🔗 Related Concepts[/]\n{rel_list}\n"

        try:
            detail = self.query_one("#detail-content", Static)
            detail.update(content)
        except Exception:
            pass

    def show_format(self, fmt: dict[str, Any]) -> None:
        """Display format details with rich visual formatting."""
        name = fmt.get("name", "")
        summary = fmt.get("summary", "")
        deck_rules = fmt.get("deck_rules", {})
        banned = fmt.get("banned_cards", [])
        restricted = fmt.get("restricted_cards", [])
        tips = fmt.get("tips", "")

        # Format-specific colors
        format_colors = {
            "standard": "#4caf50",
            "modern": "#2196f3",
            "legacy": "#9c27b0",
            "vintage": "#ffd700",
            "commander": "#ff5722",
            "pioneer": "#00bcd4",
            "pauper": "#795548",
        }
        fmt_color = format_colors.get(name.lower(), "#888")

        content = f"""[bold #c9a227 on #1a1a2e]  {name.upper()}  [/]
[{fmt_color}]◆[/] [dim italic]Format[/]
[dim]{"─" * 40}[/]

[#87ceeb bold]📋 Overview[/]
{summary}

[#90caf9 bold]🎯 Deck Construction[/]
"""
        if deck_rules:
            min_cards = deck_rules.get("min_deck_size", "N/A")
            max_cards = deck_rules.get("max_deck_size", "No limit")
            copies = deck_rules.get("copies_allowed", 4)
            sideboard = deck_rules.get("sideboard_size", 15)
            content += f"  [#4db6ac]▸[/] Minimum: [bold]{min_cards}[/] cards\n"
            content += f"  [#4db6ac]▸[/] Maximum: [bold]{max_cards}[/]\n"
            content += f"  [#4db6ac]▸[/] Copies: [bold]{copies}[/] per card\n"
            content += f"  [#4db6ac]▸[/] Sideboard: [bold]{sideboard}[/] cards\n"

        if banned:
            content += f"\n[#ef5350 bold]🚫 Banned Cards[/] [dim]({len(banned)} total)[/]\n"
            if len(banned) <= 10:
                ban_list = " [dim]•[/] ".join(f"[#ef9a9a]{b}[/]" for b in banned)
            else:
                ban_list = " [dim]•[/] ".join(f"[#ef9a9a]{b}[/]" for b in banned[:8])
                ban_list += f" [dim]...and {len(banned) - 8} more[/]"
            content += f"{ban_list}\n"

        if restricted:
            content += f"\n[#ffb74d bold]⚠️ Restricted[/] [dim]({len(restricted)} cards)[/]\n"
            res_list = " [dim]•[/] ".join(f"[#ffe082]{r}[/]" for r in restricted)
            content += f"{res_list}\n"

        if tips:
            content += f"\n[#ffd54f bold]💡 Strategy Tips[/]\n[#ffd54f]{tips}[/]\n"

        try:
            detail = self.query_one("#detail-content", Static)
            detail.update(content)
        except Exception:
            pass


class ConceptsGlossary(Vertical):
    """Middle column: Concepts list."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.concepts: list[dict[str, Any]] = []

    def compose(self) -> ComposeResult:
        yield Static("[bold #c9a227]GAME CONCEPTS[/]", classes="column-header")
        yield ListView(id="concepts-list")

    def set_concepts(self, concepts: list[dict[str, Any]]) -> None:
        """Set concepts and refresh display."""
        self.concepts = concepts
        self._populate_list()

    def _populate_list(self) -> None:
        """Populate the concepts list."""
        try:
            list_view = self.query_one("#concepts-list", ListView)
            list_view.clear()

            for concept in self.concepts:
                name = concept.get("name", "")
                summary = concept.get("summary", "")
                label = (
                    f"[bold]{name}[/]\n[dim]{summary[:60]}{'...' if len(summary) > 60 else ''}[/]"
                )
                list_view.append(ListItem(Label(label), id=f"concept-{name.replace(' ', '-')}"))
        except Exception:
            pass

    @on(ListView.Selected, "#concepts-list")
    def on_concept_selected(self, event: ListView.Selected) -> None:
        """Handle concept selection."""
        if event.item and event.item.id:
            concept_name = event.item.id.replace("concept-", "").replace("-", " ")
            for concept in self.concepts:
                if concept.get("name", "").lower() == concept_name.lower():
                    self.post_message(ConceptSelected(concept))
                    break


class FormatsGuide(Vertical):
    """Middle column: Formats list."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.formats: list[dict[str, Any]] = []

    def compose(self) -> ComposeResult:
        yield Static("[bold #c9a227]FORMAT GUIDE[/]", classes="column-header")
        yield ListView(id="formats-list")

    def set_formats(self, formats: list[dict[str, Any]]) -> None:
        """Set formats and refresh display."""
        self.formats = formats
        self._populate_list()

    def _populate_list(self) -> None:
        """Populate the formats list."""
        try:
            list_view = self.query_one("#formats-list", ListView)
            list_view.clear()

            for fmt in self.formats:
                name = fmt.get("name", "")
                summary = fmt.get("summary", "")
                label = (
                    f"[bold]{name}[/]\n[dim]{summary[:50]}{'...' if len(summary) > 50 else ''}[/]"
                )
                list_view.append(ListItem(Label(label), id=f"format-{name.replace(' ', '-')}"))
        except Exception:
            pass

    @on(ListView.Selected, "#formats-list")
    def on_format_selected(self, event: ListView.Selected) -> None:
        """Handle format selection."""
        if event.item and event.item.id:
            format_name = event.item.id.replace("format-", "").replace("-", " ")
            for fmt in self.formats:
                if fmt.get("name", "").lower() == format_name.lower():
                    self.post_message(FormatSelected(fmt))
                    break


class FormatSelected(Message):
    """Message sent when a format is selected."""

    def __init__(self, format_data: dict[str, Any]) -> None:
        self.format_data = format_data
        super().__init__()


class HelpScreen(BaseScreen[None]):
    """Help screen for MTG knowledge base."""

    show_footer: ClassVar[bool] = True
    current_topic: reactive[str] = reactive("keywords")

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "close_help", "Close"),
        Binding("f10", "toggle_menu", "Menu", show=False),
        Binding("ctrl+m", "toggle_menu", "Menu", show=False),
        Binding("/", "focus_search", "Search", show=False),
        Binding("left,h", "focus_topics", "Topics", show=False),
        Binding("right,l", "focus_content", "Content", show=False),
        # Tab handling for cross-container navigation (same pattern as main app)
        Binding("tab", "next_focus", "Next", show=False, priority=True),
        Binding("shift+tab", "prev_focus", "Prev", show=False, priority=True),
    ]

    CSS = """
    HelpScreen #screen-content {
        layout: grid;
        grid-size: 1;
        grid-rows: 3 1fr;
    }

    #help-header {
        background: #1a1a2e;
        padding: 0 2;
        height: 3;
    }

    #help-header Static {
        width: 100%;
        content-align: center middle;
    }

    #help-container {
        layout: grid;
        grid-size: 3;
        grid-columns: 1fr 1.4fr 1.6fr;
        height: 100%;
    }

    .help-column {
        height: 100%;
        padding: 1 1;
        border-right: solid #333;
    }

    .help-column:last-child {
        border-right: none;
    }

    .column-header {
        height: 1;
        margin-bottom: 1;
    }

    TopicList {
        width: 100%;
        height: 100%;
    }

    #topic-listview {
        height: 1fr;
    }

    #topic-listview > ListItem {
        padding: 1;
        margin-bottom: 1;
    }

    #topic-listview > ListItem:hover {
        background: #2a2a4e;
    }

    KeywordGlossary, ConceptsGlossary, FormatsGuide {
        width: 100%;
        height: 100%;
    }

    /* Hide inactive middle panels */
    #concepts-glossary, #formats-guide {
        display: none;
    }

    #concepts-glossary.visible, #formats-guide.visible {
        display: block;
    }

    #keyword-glossary {
        display: block;
    }

    #keyword-glossary.hidden {
        display: none;
    }

    KeywordGlossary #keyword-search {
        margin-bottom: 1;
    }

    #category-filters {
        height: 1;
        margin-bottom: 1;
    }

    .category-chip {
        padding: 0 1;
        margin-right: 1;
    }

    .category-chip:hover {
        background: #333;
    }

    .category-active {
        background: #c9a227;
        color: #000;
    }

    KeywordGlossary #keyword-list,
    ConceptsGlossary #concepts-list,
    FormatsGuide #formats-list {
        height: 1fr;
    }

    KeywordGlossary #keyword-list > ListItem,
    ConceptsGlossary #concepts-list > ListItem,
    FormatsGuide #formats-list > ListItem {
        padding: 0 1;
    }

    KeywordGlossary #keyword-list > ListItem:hover,
    ConceptsGlossary #concepts-list > ListItem:hover,
    FormatsGuide #formats-list > ListItem:hover {
        background: #2a2a4e;
    }

    DetailPanel {
        width: 100%;
        height: 100%;
        padding: 1 2;
    }

    #detail-content {
        width: 100%;
    }
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.keywords: list[dict[str, Any]] = []
        self.concepts: list[dict[str, Any]] = []
        self.formats: list[dict[str, Any]] = []

    def compose_content(self) -> ComposeResult:
        with Vertical(id="help-header"):
            yield Static(
                "[bold #c9a227]MTG KNOWLEDGE BASE[/]  [dim]Tab to navigate, ←/→ columns, / search[/]"
            )

        with Horizontal(id="help-container"):
            with Vertical(classes="help-column"):
                yield TopicList(id="topic-list")

            with Vertical(classes="help-column", id="middle-column"):
                yield KeywordGlossary(id="keyword-glossary")
                yield ConceptsGlossary(id="concepts-glossary")
                yield FormatsGuide(id="formats-guide")

            with Vertical(classes="help-column"):
                yield DetailPanel(id="detail-panel")

    async def on_mount(self) -> None:
        """Load data on mount."""
        await super().on_mount()
        self._load_data()
        # Focus the topic list on mount
        self.call_later(self._focus_topics)

    def _focus_topics(self) -> None:
        """Focus the topics list."""
        try:
            topic_list = self.query_one("#topic-listview", ListView)
            topic_list.focus()
        except Exception:
            pass

    @work
    async def _load_data(self) -> None:
        """Load keywords, concepts, and formats from JSON files."""
        data_dir = Path(__file__).parent.parent / "data"

        # Load keywords
        keywords_file = data_dir / "keywords.json"
        if keywords_file.exists():
            try:
                data = json.loads(keywords_file.read_text())
                self.keywords = data.get("keywords", [])
                glossary = self.query_one("#keyword-glossary", KeywordGlossary)
                glossary.set_keywords(self.keywords)
            except Exception:
                pass

        # Load concepts
        concepts_file = data_dir / "concepts.json"
        if concepts_file.exists():
            try:
                data = json.loads(concepts_file.read_text())
                self.concepts = data.get("concepts", [])
                concepts_panel = self.query_one("#concepts-glossary", ConceptsGlossary)
                concepts_panel.set_concepts(self.concepts)
            except Exception:
                pass

        # Load formats
        formats_file = data_dir / "formats.json"
        if formats_file.exists():
            try:
                data = json.loads(formats_file.read_text())
                self.formats = data.get("formats", [])
                formats_panel = self.query_one("#formats-guide", FormatsGuide)
                formats_panel.set_formats(self.formats)
            except Exception:
                pass

    def watch_current_topic(self, topic: str) -> None:
        """Switch between middle panels based on selected topic."""
        panels = {
            "keywords": "#keyword-glossary",
            "concepts": "#concepts-glossary",
            "formats": "#formats-guide",
        }

        for panel_topic, selector in panels.items():
            try:
                panel = self.query_one(selector)
                if panel_topic == topic:
                    panel.add_class("visible")
                    panel.remove_class("hidden")
                else:
                    panel.remove_class("visible")
                    panel.add_class("hidden")
            except Exception:
                pass

        # Clear detail panel when switching topics
        try:
            detail = self.query_one("#detail-panel", DetailPanel)
            detail.clear()
        except Exception:
            pass

    @on(TopicSelected)
    def on_topic_selected(self, event: TopicSelected) -> None:
        """Handle topic selection from the left panel."""
        self.current_topic = event.topic_id

    @on(KeywordSelected)
    def on_keyword_selected(self, event: KeywordSelected) -> None:
        """Handle keyword selection."""
        try:
            detail = self.query_one("#detail-panel", DetailPanel)
            detail.show_keyword(event.keyword)
        except Exception:
            pass

    @on(ConceptSelected)
    def on_concept_selected(self, event: ConceptSelected) -> None:
        """Handle concept selection."""
        try:
            detail = self.query_one("#detail-panel", DetailPanel)
            detail.show_concept(event.concept)
        except Exception:
            pass

    @on(FormatSelected)
    def on_format_selected(self, event: FormatSelected) -> None:
        """Handle format selection."""
        try:
            detail = self.query_one("#detail-panel", DetailPanel)
            detail.show_format(event.format_data)
        except Exception:
            pass

    def action_close_help(self) -> None:
        """Close the help screen."""
        self.app.pop_screen()

    def action_focus_search(self) -> None:
        """Focus the search input (only works in keywords view)."""
        if self.current_topic == "keywords":
            try:
                search = self.query_one("#keyword-search", Input)
                search.focus()
            except Exception:
                pass

    def action_focus_topics(self) -> None:
        """Focus the topics list (left column)."""
        try:
            topic_list = self.query_one("#topic-listview", ListView)
            topic_list.focus()
        except Exception:
            pass

    def action_focus_content(self) -> None:
        """Focus the content list (middle column)."""
        try:
            if self.current_topic == "keywords":
                widget = self.query_one("#keyword-list", ListView)
            elif self.current_topic == "concepts":
                widget = self.query_one("#concepts-list", ListView)
            else:
                widget = self.query_one("#formats-list", ListView)
            widget.focus()
        except Exception:
            pass

    def action_next_focus(self) -> None:
        """Cycle focus: topics -> search (keywords) -> content list -> topics."""
        focused = self.app.focused
        try:
            topic_list = self.query_one("#topic-listview", ListView)
            search_input = self.query_one("#keyword-search", Input)
        except Exception:
            return

        # Topics -> search (if keywords) or content list
        if focused == topic_list:
            if self.current_topic == "keywords":
                search_input.focus()
            else:
                self.action_focus_content()
            return

        # Search -> content list
        if focused == search_input:
            self.action_focus_content()
            return

        # Content list -> topics
        self.action_focus_topics()

    def action_prev_focus(self) -> None:
        """Cycle focus backwards."""
        focused = self.app.focused
        try:
            topic_list = self.query_one("#topic-listview", ListView)
            search_input = self.query_one("#keyword-search", Input)
        except Exception:
            return

        # Topics -> content list
        if focused == topic_list:
            self.action_focus_content()
            return

        # Search -> topics
        if focused == search_input:
            self.action_focus_topics()
            return

        # Content list -> search (if keywords) or topics
        if self.current_topic == "keywords":
            search_input.focus()
        else:
            self.action_focus_topics()

    def select_keyword(self, keyword_name: str) -> None:
        """Select a keyword by name (for deep linking from search)."""
        # Make sure we're on the keywords topic
        self.current_topic = "keywords"
        for kw in self.keywords:
            if kw.get("name", "").lower() == keyword_name.lower():
                self.post_message(KeywordSelected(kw))
                break
