"""Set-related models."""

from pydantic import BaseModel, Field


class Set(BaseModel):
    """A Magic: The Gathering set."""

    code: str
    name: str
    type: str | None = None  # expansion, core, masters, etc.
    release_date: str | None = Field(default=None, alias="releaseDate")
    block: str | None = None
    base_set_size: int | None = Field(default=None, alias="baseSetSize", ge=0)
    total_set_size: int | None = Field(default=None, alias="totalSetSize", ge=0)
    is_online_only: bool | None = Field(default=None, alias="isOnlineOnly")
    is_foil_only: bool | None = Field(default=None, alias="isFoilOnly")
    keyrune_code: str | None = Field(default=None, alias="keyruneCode")

    class Config:
        populate_by_name = True
