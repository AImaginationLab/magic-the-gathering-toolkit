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

    def add_name_search(self, value: str | None) -> None:
        """Add a name search that checks both name and flavorName columns.

        This allows finding cards like SpongeBob (stored as flavorName) when
        searching by their alternate/promotional names.
        """
        if value:
            pattern = f"%{value}%"
            self.conditions.append("(c.name LIKE ? OR c.flavor_name LIKE ?)")
            self.params.extend([pattern, pattern])

    def add_exact(self, column: str, value: Any, case_insensitive: bool = False) -> None:
        """Add an exact match condition."""
        if value is not None:
            if case_insensitive:
                self.conditions.append(f"LOWER({column}) = LOWER(?)")
            else:
                self.conditions.append(f"{column} = ?")
            self.params.append(value)

    # Valid SQL comparison operators
    VALID_OPERATORS: frozenset[str] = frozenset({"=", "!=", "<>", ">", "<", ">=", "<="})

    def add_comparison(self, column: str, op: str, value: float | None) -> None:
        """Add a comparison condition (=, >=, <=, etc)."""
        if value is not None:
            if op not in self.VALID_OPERATORS:
                raise ValueError(f"Invalid operator: {op}. Must be one of {self.VALID_OPERATORS}")
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
        """Add color filter conditions (card must have all colors).

        Special handling for "C" (colorless) - matches cards with empty/null colors.
        Colors are validated against allowed values to prevent SQL injection.
        """
        if colors:
            # Validate colors against allowed values
            valid_colors = {"W", "U", "B", "R", "G", "C"}
            safe_colors = [c for c in colors if c in valid_colors]

            has_colorless = "C" in safe_colors
            other_colors = [c for c in safe_colors if c != "C"]

            if has_colorless and not other_colors:
                # Only colorless requested - cards with no colors
                self.conditions.append("(c.colors IS NULL OR c.colors = '' OR c.colors = '[]')")
            elif has_colorless and other_colors:
                # Colorless OR specific colors (parameterized)
                color_conditions = ["(c.colors IS NULL OR c.colors = '' OR c.colors = '[]')"]
                for color in other_colors:
                    color_conditions.append("c.colors LIKE ?")
                    self.params.append(f'%"{color}"%')
                self.conditions.append(f"({' OR '.join(color_conditions)})")
            else:
                # Standard color filtering - must have all colors
                for color in other_colors:
                    self.conditions.append("c.colors LIKE ?")
                    self.params.append(f'%"{color}"%')

    def add_color_identity(self, identity: Sequence[str] | None) -> None:
        """Add color identity filter (card must be subset of identity)."""
        if identity:
            # Card must NOT contain any colors outside the given identity
            excluded = [c for c in ["W", "U", "B", "R", "G"] if c not in identity]
            for color in excluded:
                self.add_not_like("c.color_identity", color)

    def add_format_legality(self, format_name: str | None) -> None:
        """Add format legality condition using JSON legalities column."""
        if format_name and format_name.lower() in VALID_FORMATS:
            fmt = format_name.lower()
            # Legalities are stored as JSON in the legalities column
            # Use json_extract to check the format's legality value
            self.conditions.append(
                "(json_extract(c.legalities, ?) = 'legal' OR json_extract(c.legalities, ?) = 'restricted')"
            )
            json_path = f"$.{fmt}"
            self.params.extend([json_path, json_path])

    def add_keywords(self, keywords: list[str] | None) -> None:
        """Add keyword filter conditions."""
        if keywords:
            for keyword in keywords:
                self.add_like("c.keywords", keyword)

    def build_where(self) -> str:
        """Build the WHERE clause."""
        return " AND ".join(self.conditions) if self.conditions else "1=1"

    def add_format_legality_optimized(self, format_name: str | None) -> None:
        """Add format legality using generated columns (faster than JSON extract)."""
        if format_name:
            fmt = format_name.lower()
            # Use generated columns for common formats (much faster)
            if fmt == "commander":
                self.conditions.append("c.legal_commander = 1")
            elif fmt == "modern":
                self.conditions.append("c.legal_modern = 1")
            elif fmt == "standard":
                self.conditions.append("c.legal_standard = 1")
            elif fmt in VALID_FORMATS:
                # Fall back to JSON extract for other formats
                self.conditions.append(f"json_extract(c.legalities, '$.{fmt}') = 'legal'")

    @classmethod
    def from_filters(cls, filters: SearchCardsInput, use_table_prefix: bool = True) -> QueryBuilder:
        """Build a QueryBuilder from SearchCardsInput.

        Args:
            filters: Search filters to apply
            use_table_prefix: If True, prefix columns with 'c.' (default).
                              Set False for queries without table alias.
        """
        qb = cls()
        p = "c." if use_table_prefix else ""

        # Name search (checks both name and flavor_name)
        if filters.name:
            pattern = f"%{filters.name}%"
            qb.conditions.append(
                f"({p}name COLLATE NOCASE LIKE ? OR {p}flavor_name COLLATE NOCASE LIKE ?)"
            )
            qb.params.extend([pattern, pattern])

        # Color filters (validated against allowed values to prevent injection)
        if filters.colors:
            valid_colors = {"W", "U", "B", "R", "G", "C"}
            safe_colors = [c for c in filters.colors if c in valid_colors]

            has_colorless = "C" in safe_colors
            other_colors = [c for c in safe_colors if c != "C"]

            if has_colorless and not other_colors:
                qb.conditions.append(f"({p}colors IS NULL OR {p}colors = '' OR {p}colors = '[]')")
            elif has_colorless and other_colors:
                # Build OR condition with parameterized queries
                color_conditions = [f"({p}colors IS NULL OR {p}colors = '' OR {p}colors = '[]')"]
                for color in other_colors:
                    color_conditions.append(f"{p}colors LIKE ?")
                    qb.params.append(f'%"{color}"%')
                qb.conditions.append(f"({' OR '.join(color_conditions)})")
            else:
                for color in other_colors:
                    qb.conditions.append(f"{p}colors LIKE ?")
                    qb.params.append(f'%"{color}"%')

        # Color identity
        if filters.color_identity:
            for ci_color in filters.color_identity:
                qb.conditions.append(f"{p}color_identity LIKE ?")
                qb.params.append(f'%"{ci_color}"%')

        # Type line
        if filters.type:
            qb.conditions.append(f"{p}type_line LIKE ?")
            qb.params.append(f"%{filters.type}%")

        # Subtype (appears after "—" in type_line, e.g., "Creature — Dog")
        if filters.subtype:
            # Match subtype as a whole word after the em dash
            # Use word boundaries to avoid partial matches (e.g., "Dog" shouldn't match "Dogsnail")
            qb.conditions.append(
                f"({p}type_line LIKE ? OR {p}type_line LIKE ? OR {p}type_line LIKE ?)"
            )
            # Match: "— Dog" (at end), "— Dog " (followed by space), " Dog " (in middle of subtypes)
            qb.params.append(f"%— {filters.subtype}")  # At end of type line
            qb.params.append(f"%— {filters.subtype} %")  # Followed by another subtype
            qb.params.append(f"% {filters.subtype} %")  # In middle of subtypes

        # Supertype (appears before main type, e.g., "Legendary Creature")
        if filters.supertype:
            qb.conditions.append(f"{p}type_line LIKE ?")
            qb.params.append(f"%{filters.supertype}%")

        # Oracle text
        if filters.text:
            qb.conditions.append(f"{p}oracle_text LIKE ?")
            qb.params.append(f"%{filters.text}%")

        # Set code
        if filters.set_code:
            qb.conditions.append(f"{p}set_code COLLATE NOCASE = ?")
            qb.params.append(filters.set_code)

        # Rarity
        if filters.rarity:
            qb.conditions.append(f"{p}rarity COLLATE NOCASE = ?")
            qb.params.append(filters.rarity)

        # CMC filters
        if filters.cmc is not None:
            qb.conditions.append(f"{p}cmc = ?")
            qb.params.append(filters.cmc)
        if filters.cmc_min is not None:
            qb.conditions.append(f"{p}cmc >= ?")
            qb.params.append(filters.cmc_min)
        if filters.cmc_max is not None:
            qb.conditions.append(f"{p}cmc <= ?")
            qb.params.append(filters.cmc_max)

        # Power/toughness
        if filters.power:
            qb.conditions.append(f"{p}power = ?")
            qb.params.append(filters.power)
        if filters.toughness:
            qb.conditions.append(f"{p}toughness = ?")
            qb.params.append(filters.toughness)

        # Keywords (JSON array)
        if filters.keywords:
            for kw in filters.keywords:
                qb.conditions.append(f"{p}keywords LIKE ?")
                qb.params.append(f'%"{kw}"%')

        # Format legality (use optimized generated columns)
        if filters.format_legal:
            fmt = filters.format_legal.lower()
            if fmt == "commander":
                qb.conditions.append(f"{p}legal_commander = 1")
            elif fmt == "modern":
                qb.conditions.append(f"{p}legal_modern = 1")
            elif fmt == "standard":
                qb.conditions.append(f"{p}legal_standard = 1")
            elif fmt in VALID_FORMATS:
                qb.conditions.append(f"json_extract({p}legalities, '$.{fmt}') = 'legal'")

        # Artist
        if filters.artist:
            qb.conditions.append(f"{p}artist COLLATE NOCASE LIKE ?")
            qb.params.append(f"%{filters.artist}%")

        return qb
