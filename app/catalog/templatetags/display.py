from django import template
from django.utils.html import format_html, format_html_join

from catalog import formatting

register = template.Library()


@register.simple_tag
def stars(rating):
    """Five stars filled to the rounded rating plus the value; 'No ratings yet' for None.
    Same markup and rounding as Stars in frontend/src/BrandCard.jsx."""
    if rating is None:
        return format_html(
            '<span class="stars"><span class="rating-value">No ratings yet</span></span>'
        )
    value = formatting.one_decimal(rating)
    filled = formatting.filled_stars(rating)
    marks = format_html_join(
        "",
        '<span class="{}" aria-hidden="true">★</span>',
        (("star-full" if i < filled else "star-empty",) for i in range(5)),
    )
    return format_html(
        '<span class="stars" role="img" aria-label="Rated {} out of 5">{}'
        '<span class="rating-value" aria-hidden="true">{}</span></span>',
        value,
        marks,
        value,
    )


@register.filter
def snippet(html):
    """Plain-text excerpt of an HTML body, as the API's snippets are made."""
    return formatting.snippet(html)
