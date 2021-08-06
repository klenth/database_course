import markdown2
from django import template
from django.utils.html import conditional_escape, html_safe
from django.utils.safestring import mark_safe
from django.template.defaultfilters import stringfilter
from lms.models import *
from lab.models import *
from lms import canvas_api_token

register = template.Library()


@register.filter(name='canvas_assignment_url')
def canvas_assignment_url(assignment_or_lab):
    if isinstance(assignment_or_lab, CanvasAssignment):
        canvas_course = assignment_or_lab.lab.course.canvas_course
        return f'{canvas_api_token.canvas_site_base_url}/courses/{canvas_course.canvas_id}/assignments/{assignment_or_lab.canvas_id}'
    elif isinstance(assignment_or_lab, Lab):
        return canvas_assignment_url(assignment_or_lab.canvas_assignment)
    else:
        raise ValueError('Not a CanvasAssignment or Lab')
