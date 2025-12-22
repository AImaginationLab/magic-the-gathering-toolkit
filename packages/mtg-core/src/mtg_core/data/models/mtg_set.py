"""Set-related models."""

from pydantic import BaseModel, ConfigDict, Field


class Set(BaseModel):
    """A Magic: The Gathering set."""

    model_config = ConfigDict(populate_by_name=True)

    code: str
    name: str
    type: str | None = None  # expansion, core, masters, etc.
    release_date: str | None = Field(default=None, alias="releaseDate")
    block: str | None = None
    base_set_size: int | None = Field(default=None, alias="baseSetSize", ge=0)
    total_set_size: int | None = Field(default=None, alias="totalSetSize", ge=0)
    card_count: int | None = None  # Total cards in set (from Scryfall)
    is_online_only: bool | None = Field(default=None, alias="isOnlineOnly")
    is_foil_only: bool | None = Field(default=None, alias="isFoilOnly")
    keyrune_code: str | None = Field(default=None, alias="keyruneCode")
    icon_svg_uri: str | None = None  # Scryfall set icon URL
