from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import *
from . import canvas
from requests import HTTPError

@login_required
def import_canvas_courses(request):
    instructor = get_object_or_404(Instructor, id=request.user.id)

    errors = []
    context = {
        'courses': [],
        'errors': errors,
    }

    if request.method == 'POST':
        pass
    else:
        known_courses = CanvasCourse.objects.filter(course__instructor=instructor)
        known_course_canvas_ids = set(c.canvas_id for c in known_courses)

        try:
            course_data = canvas.download_courses()
            course_data = list(filter(lambda course: course['canvas_id'] not in known_course_canvas_ids, course_data))
            context['courses'] = course_data
        except HTTPError as e:
            errors.append(str(e))

        return render(request, 'lms/import_canvas_courses.html', context)
