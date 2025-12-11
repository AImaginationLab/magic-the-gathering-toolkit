"""Custom exceptions for MTG MCP server."""


class MTGError(Exception):
    """Base exception for MTG MCP errors."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class CardNotFoundError(MTGError):
    """Raised when a card is not found."""

    def __init__(self, identifier: str):
        super().__init__(f"Card not found: {identifier}")
        self.identifier = identifier


class SetNotFoundError(MTGError):
    """Raised when a set is not found."""

    def __init__(self, code: str):
        super().__init__(f"Set not found: {code}")
        self.code = code


class ValidationError(MTGError):
    """Raised when input validation fails."""

    pass


class DatabaseNotAvailableError(MTGError):
    """Raised when a required database is not available."""

    def __init__(self, database: str):
        super().__init__(f"{database} database not available")
        self.database = database


class DeckValidationError(MTGError):
    """Raised when deck validation fails."""

    def __init__(self, message: str, issues: list[str] | None = None):
        super().__init__(message)
        self.issues = issues or []
