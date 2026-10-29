from decimal import Decimal

from django import template
from django.utils.html import format_html, format_html_join
from django.utils.safestring import SafeString

register = template.Library()


@register.simple_tag
def stars(rating: Decimal | float | None) -> SafeString:
    """Five stars filled to the rounded rating plus the value; 'No ratings yet' for None."""
    if rating is None:
        return format_html(
            '<span class="stars"><span class="rating-value">No ratings yet</span></span>'
        )
    filled = round(float(rating))
    marks = format_html_join(
        "",
        '<span class="{}" aria-hidden="true">★</span>',
        (("star-full" if i < filled else "star-empty",) for i in range(5)),
    )
    return format_html(
        '<span class="stars" role="img" aria-label="Rated {} out of 5">{}'
        '<span class="rating-value">{}</span></span>',
        f"{float(rating):.1f}",
        marks,
        f"{float(rating):.1f}",
    )
