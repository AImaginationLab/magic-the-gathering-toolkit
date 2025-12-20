"""Messages for collection UI components."""

from textual.message import Message


class CollectionCardSelected(Message):
    """Posted when a card is selected in the collection."""

    def __init__(
        self,
        card_name: str,
        set_code: str | None = None,
        collector_number: str | None = None,
    ) -> None:
        super().__init__()
        self.card_name = card_name
        self.set_code = set_code
        self.collector_number = collector_number


class CardAddedToCollection(Message):
    """Posted when a card is added to the collection."""

    def __init__(self, card_name: str, quantity: int, foil: bool = False) -> None:
        super().__init__()
        self.card_name = card_name
        self.quantity = quantity
        self.foil = foil


class CardRemovedFromCollection(Message):
    """Posted when a card is removed from the collection."""

    def __init__(self, card_name: str) -> None:
        super().__init__()
        self.card_name = card_name


class CollectionQuantityChanged(Message):
    """Posted when card quantity changes in the collection."""

    def __init__(self, card_name: str, quantity: int, foil_quantity: int) -> None:
        super().__init__()
        self.card_name = card_name
        self.quantity = quantity
        self.foil_quantity = foil_quantity
