from django import template

register = template.Library()

@register.filter(name='add_class')
def add_class(field, css_class):
    """Add CSS class to form field"""
    if hasattr(field, 'as_widget'):
        return field.as_widget(attrs={'class': css_class})
    return field

@register.filter(name='add_attrs')
def add_attrs(field, attrs):
    """Add multiple attributes to form field"""
    attrs_dict = {}
    for attr in attrs.split(','):
        key, value = attr.split(':')
        attrs_dict[key.strip()] = value.strip()
    
    if hasattr(field, 'as_widget'):
        return field.as_widget(attrs=attrs_dict)
    return field

@register.filter(name='split')
def split_string(value, separator):
    """Split string by separator and return list"""
    if isinstance(value, str):
        return value.split(separator)
    return []

@register.filter(name='get_prizes')
def get_prizes(obj, prize_level):
    """Get prizes for a specific level"""
    if not obj:
        return []
    
    prize_attr = f"{prize_level}_prizes"
    if hasattr(obj, prize_attr):
        prizes = getattr(obj, prize_attr)
        if hasattr(prizes, 'all'):
            return prizes.all()
        return prizes
    return []