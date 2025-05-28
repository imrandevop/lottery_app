# lottery/templatetags/form_extras.py
from django import template
from django.forms import BoundField

register = template.Library()

@register.filter(name='add_class')
def add_class(field, css_class):
    """Add CSS class to form field"""
    if isinstance(field, BoundField):
        # Clone the widget attributes to avoid modifying the original
        attrs = field.field.widget.attrs.copy()
        
        # Add the new class to existing classes
        existing_classes = attrs.get('class', '')
        if existing_classes:
            attrs['class'] = f"{existing_classes} {css_class}"
        else:
            attrs['class'] = css_class
            
        # Return the field with updated attributes
        return field.as_widget(attrs=attrs)
    return field

@register.filter(name='add_attrs')
def add_attrs(field, attrs_string):
    """Add multiple attributes to form field"""
    if isinstance(field, BoundField):
        attrs_dict = {}
        for attr in attrs_string.split(','):
            if ':' in attr:
                key, value = attr.split(':', 1)
                attrs_dict[key.strip()] = value.strip()
        
        # Merge with existing attributes
        existing_attrs = field.field.widget.attrs.copy()
        existing_attrs.update(attrs_dict)
        
        return field.as_widget(attrs=existing_attrs)
    return field

@register.filter(name='split')
def split_string(value, separator):
    """Split string by separator and return list"""
    if isinstance(value, str):
        return value.split(separator)
    return []

@register.filter(name='get_prizes')
def get_prizes(lottery_draw, prize_level):
    """Get prizes for a specific level"""
    if not lottery_draw:
        return []
    
    # Map prize levels to their related names
    prize_mapping = {
        'sixth': 'sixthprize_set',
        'seventh': 'seventhprize_set', 
        'eighth': 'eighthprize_set',
        'ninth': 'ninthprize_set',
        'tenth': 'tenthprize_set',
    }
    
    related_name = prize_mapping.get(prize_level)
    if related_name and hasattr(lottery_draw, related_name):
        related_manager = getattr(lottery_draw, related_name)
        return related_manager.all()
    
    return []