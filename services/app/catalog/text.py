"""Plain-text helpers for rendered HTML."""

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


def snippet(html):
    parser = _TextExtractor()
    parser.feed(html)
    parser.close()
    return Truncator("".join(parser.parts)).words(SNIPPET_WORDS)
