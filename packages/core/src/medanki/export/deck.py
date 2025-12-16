import hashlib

import genanki

from .models import get_cloze_model, get_vignette_model


class DeckBuilder:
    def __init__(self, name: str):
        self.name = name
        self.deck_id = self._generate_deck_id(name)
        self._notes: list[genanki.Note] = []
        self._cloze_model = get_cloze_model()
        self._vignette_model = get_vignette_model()

    @classmethod
    def from_hierarchy(cls, parts: list[str]) -> "DeckBuilder":
        name = "::".join(parts)
        return cls(name)

    def _generate_deck_id(self, name: str) -> int:
        hash_bytes = hashlib.sha256(name.encode()).digest()
        return int.from_bytes(hash_bytes[:8], byteorder="big") % (2**31)

    def generate_guid(self, card) -> str:
        content = card.text if hasattr(card, "text") else card.front
        hash_bytes = hashlib.sha256(content.encode()).hexdigest()[:20]
        return hash_bytes

    def add_cloze_card(self, card) -> None:
        guid = self.generate_guid(card)
        note = genanki.Note(
            model=self._cloze_model,
            fields=[card.text, card.extra, card.source_chunk_id],
            guid=guid,
            tags=card.tags if hasattr(card, "tags") else [],
        )
        self._notes.append(note)

    def add_vignette_card(self, card) -> None:
        guid = self.generate_guid(card)
        note = genanki.Note(
            model=self._vignette_model,
            fields=[
                card.front,
                card.answer,
                card.explanation,
                card.distinguishing_feature or "",
                card.source_chunk_id,
            ],
            guid=guid,
            tags=card.tags if hasattr(card, "tags") else [],
        )
        self._notes.append(note)

    def build(self) -> genanki.Deck:
        deck = genanki.Deck(self.deck_id, self.name)
        for note in self._notes:
            deck.add_note(note)
        return deck
