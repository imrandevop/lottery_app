# Path: lottery_app/templatetags/custom_tags.py

from django import template

register = template.Library()

@register.filter
def split(value, delimiter):
    """
    Returns a list of strings after splitting the value by the delimiter.
    
    Usage: 
    {% for prize in "1st,2nd,3rd"|split:"," %}
        {{ prize }}
    {% endfor %}
    """
    return value.split(delimiter)