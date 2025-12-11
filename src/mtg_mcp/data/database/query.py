"""Query builder for parameterized SQL queries."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .constants import VALID_FORMATS

if TYPE_CHECKING:
    from ..models.inputs import SearchCardsInput


@dataclass
class QueryBuilder:
    """Builds parameterized SQL queries for card searches."""

    conditions: list[str] = field(default_factory=list)
    params: list[Any] = field(default_factory=list)

    def add_like(self, column: str, value: str | None, pattern: str = "%{value}%") -> None:
        """Add a LIKE condition."""
        if value:
            self.conditions.append(f"{column} LIKE ?")
            self.params.append(pattern.format(value=value))

    def add_exact(self, column: str, value: Any, case_insensitive: bool = False) -> None:
        """Add an exact match condition."""
        if value is not None:
            if case_insensitive:
                self.conditions.append(f"LOWER({column}) = LOWER(?)")
            else:
                self.conditions.append(f"{column} = ?")
            self.params.append(value)

    def add_comparison(self, column: str, op: str, value: float | None) -> None:
        """Add a comparison condition (=, >=, <=, etc)."""
        if value is not None:
            self.conditions.append(f"{column} {op} ?")
            self.params.append(value)

    def add_not_like(self, column: str, value: str, nullable: bool = True) -> None:
        """Add a NOT LIKE condition, handling NULL if nullable."""
        if nullable:
            self.conditions.append(f"({column} IS NULL OR {column} NOT LIKE ?)")
        else:
            self.conditions.append(f"{column} NOT LIKE ?")
        self.params.append(f"%{value}%")

    def add_colors(self, colors: Sequence[str] | None) -> None:
        """Add color filter conditions (card must have all colors)."""
        if colors:
            for color in colors:
                self.add_like("c.colors", color)

    def add_color_identity(self, identity: Sequence[str] | None) -> None:
        """Add color identity filter (card must be subset of identity)."""
        if identity:
            # Card must NOT contain any colors outside the given identity
            excluded = [c for c in ["W", "U", "B", "R", "G"] if c not in identity]
            for color in excluded:
                self.add_not_like("c.colorIdentity", color)

    def add_format_legality(self, format_name: str | None) -> None:
        """Add format legality subquery condition."""
        if format_name and format_name.lower() in VALID_FORMATS:
            fmt = format_name.lower()
            self.conditions.append(f"""
                c.uuid IN (
                    SELECT uuid FROM cardLegalities
                    WHERE {fmt} = 'Legal' OR {fmt} = 'Restricted'
                )
            """)

    def add_keywords(self, keywords: list[str] | None) -> None:
        """Add keyword filter conditions."""
        if keywords:
            for keyword in keywords:
                self.add_like("c.keywords", keyword)

    def build_where(self) -> str:
        """Build the WHERE clause."""
        return " AND ".join(self.conditions) if self.conditions else "1=1"

    @classmethod
    def from_filters(cls, filters: SearchCardsInput) -> QueryBuilder:
        """Build a QueryBuilder from SearchCardsInput."""
        qb = cls()
        qb.add_like("c.name", filters.name)
        qb.add_colors(filters.colors)
        qb.add_color_identity(filters.color_identity)
        qb.add_like("c.type", filters.type)
        qb.add_like("c.subtypes", filters.subtype)
        qb.add_like("c.supertypes", filters.supertype)
        qb.add_exact("c.rarity", filters.rarity, case_insensitive=True)
        qb.add_exact("c.setCode", filters.set_code, case_insensitive=True)
        qb.add_comparison("c.manaValue", "=", filters.cmc)
        qb.add_comparison("c.manaValue", ">=", filters.cmc_min)
        qb.add_comparison("c.manaValue", "<=", filters.cmc_max)
        qb.add_exact("c.power", filters.power)
        qb.add_exact("c.toughness", filters.toughness)
        qb.add_like("c.text", filters.text)
        qb.add_keywords(filters.keywords)
        qb.add_format_legality(filters.format_legal)
        return qb
