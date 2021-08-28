import markdown2
from django import template
from django.utils.html import conditional_escape, html_safe
from django.utils.safestring import mark_safe
from django.template.defaultfilters import stringfilter
from course.models import *

register = template.Library()


@register.filter(name='as_student')
def user_as_student(user):
    maybe_student = Student.objects.filter(id=user.id)
    return maybe_student.get() if maybe_student.exists() else None
