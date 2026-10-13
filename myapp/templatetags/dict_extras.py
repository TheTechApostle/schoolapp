from django import template

register = template.Library()

@register.filter
def dict_get(dictionary, key):
    """Get value from dict in template"""
    return dictionary.get(key)
