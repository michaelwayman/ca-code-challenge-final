"""Text and rating formatting shared by the API and the server-rendered pages, so both show
the same snippet and the same stars for the same data."""

from decimal import ROUND_HALF_UP, Decimal
from html.parser import HTMLParser

from django.utils.text import Truncator

SNIPPET_WORDS = 30


class _TextExtractor(HTMLParser):
    """Collects text outside tags with entities decoded. Unlike strip_tags + unescape,
    a bare ampersand ("AT&T") stays as written instead of becoming "AT&T;"."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def snippet(html: str, words: int = SNIPPET_WORDS) -> str:
    """Plain text of `html`, cut to `words` words."""
    parser = _TextExtractor()
    parser.feed(html)
    parser.close()
    return Truncator("".join(parser.parts)).words(words)


def one_decimal(rating) -> Decimal | None:
    """A rating rounded half-up to one decimal (2.25 -> 2.3), or None for no rating.

    Python's round() rounds halves to even; the React list uses Math.round (halves up).
    Rounding here, half-up, keeps the two in step.
    """
    if rating is None:
        return None
    return Decimal(str(rating)).quantize(Decimal("0.1"), ROUND_HALF_UP)


def filled_stars(rating) -> int:
    """How many of five stars to fill: the one-decimal rating rounded half-up (2.5 -> 3)."""
    return int(one_decimal(rating).quantize(Decimal("1"), ROUND_HALF_UP))
