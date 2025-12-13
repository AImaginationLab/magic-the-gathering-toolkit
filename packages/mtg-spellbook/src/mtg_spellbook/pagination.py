"""Pagination state management for results lists."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mtg_core.data.models.responses import CardDetail, CardSummary


@dataclass
class PaginationState:
    """Encapsulates pagination state for any list of items."""

    all_items: list[Any] = field(default_factory=list)
    current_page: int = 1
    page_size: int = 25
    page_cache: dict[int, list[CardDetail]] = field(default_factory=dict)
    is_loading: bool = False
    source_type: str = "search"  # "search" or "synergy"
    source_query: str = ""  # Original query for context

    @property
    def total_items(self) -> int:
        """Total number of items across all pages."""
        return len(self.all_items)

    @property
    def total_pages(self) -> int:
        """Total number of pages."""
        if self.total_items == 0:
            return 0
        return (self.total_items + self.page_size - 1) // self.page_size

    @property
    def start_index(self) -> int:
        """1-based start index for current page."""
        if self.total_items == 0:
            return 0
        return (self.current_page - 1) * self.page_size + 1

    @property
    def end_index(self) -> int:
        """1-based end index for current page."""
        return min(self.current_page * self.page_size, self.total_items)

    @property
    def has_next_page(self) -> bool:
        """Check if there's a next page."""
        return self.current_page < self.total_pages

    @property
    def has_prev_page(self) -> bool:
        """Check if there's a previous page."""
        return self.current_page > 1

    @property
    def current_page_items(self) -> list[Any]:
        """Get items for current page (summaries)."""
        start = (self.current_page - 1) * self.page_size
        end = start + self.page_size
        return self.all_items[start:end]

    def get_cached_details(self, page: int) -> list[CardDetail] | None:
        """Get cached card details for a page."""
        return self.page_cache.get(page)

    def cache_details(self, page: int, details: list[CardDetail]) -> None:
        """Cache card details for a page."""
        self.page_cache[page] = details

    def clear_cache(self) -> None:
        """Clear the page cache."""
        self.page_cache.clear()

    def go_to_page(self, page: int) -> bool:
        """Navigate to a specific page. Returns True if page changed."""
        if page < 1 or page > self.total_pages:
            return False
        if page == self.current_page:
            return False
        self.current_page = page
        return True

    def next_page(self) -> bool:
        """Go to next page. Returns True if page changed."""
        return self.go_to_page(self.current_page + 1)

    def prev_page(self) -> bool:
        """Go to previous page. Returns True if page changed."""
        return self.go_to_page(self.current_page - 1)

    def first_page(self) -> bool:
        """Go to first page. Returns True if page changed."""
        return self.go_to_page(1)

    def last_page(self) -> bool:
        """Go to last page. Returns True if page changed."""
        return self.go_to_page(self.total_pages)

    def format_page_info(self) -> str:
        """Format page info for display: '1-25 of 347'."""
        if self.total_items == 0:
            return "No results"
        return f"{self.start_index}-{self.end_index} of {self.total_items}"

    def format_page_position(self) -> str:
        """Format page position: 'Page 1/14'."""
        if self.total_pages == 0:
            return ""
        return f"Page {self.current_page}/{self.total_pages}"

    def format_header(self) -> str:
        """Format full header text."""
        if self.total_items == 0:
            return "No results"
        if self.total_pages == 1:
            return f"Results ({self.total_items})"
        return f"Results: {self.format_page_info()}"

    @classmethod
    def from_summaries(
        cls,
        summaries: list[CardSummary],
        source_type: str = "search",
        source_query: str = "",
        page_size: int = 25,
    ) -> PaginationState:
        """Create pagination state from search results."""
        return cls(
            all_items=list(summaries),
            current_page=1,
            page_size=page_size,
            source_type=source_type,
            source_query=source_query,
        )
