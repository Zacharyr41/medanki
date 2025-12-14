
import genanki


class APKGExporter:
    def export(
        self,
        deck: genanki.Deck,
        output_path: str,
        media_files: list[str] | None = None,
    ) -> None:
        package = genanki.Package(deck)
        if media_files:
            package.media_files = media_files
        package.write_to_file(output_path)

    def export_multiple(
        self,
        decks: list[genanki.Deck],
        output_path: str,
        media_files: list[str] | None = None,
    ) -> None:
        package = genanki.Package(decks)
        if media_files:
            package.media_files = media_files
        package.write_to_file(output_path)
