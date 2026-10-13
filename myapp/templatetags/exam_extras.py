# exam/templatetags/exam_extras.py
import re
from django import template

register = template.Library()

@register.filter
def clean_exam_title(title, classgroup_name=None):
    """
    Removes duplicated class names like '(SS1 H)' or 'SS1 H' 
    from exam titles such as 'SS1 H ENGLISH STUDIES Exam (SS1 H)'.
    """
    if not title:
        return title

    if classgroup_name:
        pattern = rf'\(?{re.escape(classgroup_name)}\)?'
        title = re.sub(pattern, '', title, flags=re.IGNORECASE).strip()

    title = re.sub(r'\s{2,}', ' ', title)
    return title.strip()
