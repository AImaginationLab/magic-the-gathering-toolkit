"""Base protocol and command routing for the MTG Spellbook TUI."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from mtg_core.data.database import UnifiedDatabase
    from mtg_core.data.models.responses import CardDetail


class AppProtocol(Protocol):
    """Protocol for the App class that command mixins expect."""

    _db: UnifiedDatabase | None
    _current_results: list[CardDetail]
    _current_card: CardDetail | None

    def exit(self) -> None: ...
    def query_one(self, selector: str, expect_type: type[Any] = ...) -> Any: ...


class CommandRouterMixin:
    """Mixin providing command routing for the TUI app.

    This mixin routes commands to the appropriate handler methods.
    Handler methods are provided by other mixins.
    """

    if TYPE_CHECKING:
        _db: Any
        _current_results: list[Any]
        _current_card: Any
        _synergy_mode: bool
        _synergy_info: dict[str, Any]

        def exit(self) -> None: ...
        def lookup_random(self) -> None: ...
        def search_cards(self, query: str) -> None: ...
        def find_synergies(self, card_name: str) -> None: ...
        def find_combos(self, card_name: str) -> None: ...
        def browse_sets(self, query: str) -> None: ...
        def show_set(self, code: str) -> None: ...
        def show_set_detail(self, set_code: str) -> None: ...
        def show_stats(self) -> None: ...
        def load_rulings(self, card_name: str) -> None: ...
        def load_legalities(self, card_name: str) -> None: ...
        def show_price(self, card_name: str) -> None: ...
        def show_art(self, card_name: str) -> None: ...
        def show_help(self) -> None: ...
        def lookup_card(
            self,
            name: str,
            uuid: str | None = None,
            target_set: str | None = None,
            target_number: str | None = None,
        ) -> None: ...
        def show_artist(self, artist_name: str, select_card: str | None = None) -> None: ...
        def browse_artists(self, search_query: str = "") -> None: ...
        def random_artist(self) -> None: ...
        def browse_blocks(self) -> None: ...
        def show_recent_sets(self, limit: int = 10) -> None: ...
        def _show_message(self, message: str) -> None: ...

    def handle_command(self, query: str) -> None:
        """Parse and route a command to the appropriate handler."""
        parts = query.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if cmd in ("quit", "q", "exit"):
            self.exit()
        elif cmd == "random":
            self.lookup_random()
        elif cmd == "search":
            if args:
                self.search_cards(args)
            else:
                self._show_message("[yellow]Usage: search <query>[/]")
        elif cmd in ("synergy", "syn"):
            if args:
                self.find_synergies(args)
            else:
                self._show_message("[yellow]Usage: synergy <card name>[/]")
        elif cmd in ("combos", "combo"):
            if args:
                self.find_combos(args)
            else:
                self._show_message("[yellow]Usage: combos <card name>[/]")
        elif cmd == "sets":
            self.browse_sets(args)
        elif cmd == "set":
            if args:
                self.show_set_detail(args)
            else:
                self._show_message("[yellow]Usage: set <code>[/]")
        elif cmd == "setinfo":
            if args:
                self.show_set(args)
            else:
                self._show_message("[yellow]Usage: setinfo <code>[/]")
        elif cmd == "artist":
            if args:
                self.show_artist(args)
            else:
                self._show_message("[yellow]Usage: artist <name>[/]")
        elif cmd == "artists":
            self.browse_artists(args)
        elif cmd == "randomartist":
            self.random_artist()
        elif cmd == "blocks":
            self.browse_blocks()
        elif cmd in ("releases", "recent"):
            limit = int(args) if args.isdigit() else 10
            self.show_recent_sets(limit)
        elif cmd == "stats":
            self.show_stats()
        elif cmd in ("rulings", "r"):
            if args:
                self.load_rulings(args)
            else:
                self._show_message("[yellow]Usage: rulings <card name>[/]")
        elif cmd in ("legal", "l", "legality"):
            if args:
                self.load_legalities(args)
            else:
                self._show_message("[yellow]Usage: legal <card name>[/]")
        elif cmd in ("price", "p"):
            if args:
                self.show_price(args)
            else:
                self._show_message("[yellow]Usage: price <card name>[/]")
        elif cmd in ("art", "img", "image"):
            if args:
                self.show_art(args)
            else:
                self._show_message("[yellow]Usage: art <card name>[/]")
        elif cmd in ("help", "?"):
            self.show_help()
        elif cmd in ("card", "c"):
            if args:
                self.lookup_card(args)
            else:
                self._show_message("[yellow]Usage: card <name>[/]")
        else:
            self.lookup_card(query)
