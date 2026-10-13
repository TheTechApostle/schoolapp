from  django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    try:
        return dictionary.get(key)
    except:
        return None


@register.filter
def mul(value, arg):
    try:
        return float(value) * float(arg)
    except:
        return 0

@register.filter
def div(value, arg):
    try:
        return float(value) / float(arg)
    except:
        return 0
    
    

def dict_get(dictionary, key): 
    """Get value from dict in template"""
    return dictionary.get(key)