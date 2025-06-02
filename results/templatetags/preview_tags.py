# results/templatetags/preview_tags.py
# Optional: Template tags for preview functionality

from django import template
from django.utils.safestring import mark_safe
import json

register = template.Library()

@register.simple_tag
def preview_config():
    """
    Generate JavaScript configuration for preview functionality
    """
    config = {
        'prize_types': ['1st', '2nd', '3rd', 'consolation', '4th', '5th', '6th', '7th', '8th', '9th', '10th'],
        'prize_names': {
            '1st': '1st Prize',
            '2nd': '2nd Prize', 
            '3rd': '3rd Prize',
            '4th': '4th Prize',
            '5th': '5th Prize',
            '6th': '6th Prize',
            '7th': '7th Prize',
            '8th': '8th Prize',
            '9th': '9th Prize',
            '10th': '10th Prize',
            'consolation': 'Consolation Prize'
        },
        'currency_symbol': '₹',
        'date_format': 'en-GB'
    }
    
    return mark_safe(f'<script>window.PREVIEW_CONFIG = {json.dumps(config)};</script>')

@register.inclusion_tag('admin/includes/preview_section.html')
def render_preview_section():
    """
    Render the preview section
    """
    return {}