import re

from django import template
from django.template.defaultfilters import linebreaks_filter
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def bold(text):
    """Escape the answer, turn **text** into <strong>, then keep line breaks."""
    html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escape(text))
    return mark_safe(linebreaks_filter(html, autoescape=False))
