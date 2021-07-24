from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.transaction import atomic
from .models import *
from . import canvas
from requests import HTTPError

@login_required
@atomic
def import_canvas_courses(request):
    instructor = get_object_or_404(Instructor, id=request.user.id)

    errors = []
    context = {
        'courses': None,
        'errors': errors,
    }

    if request.method == 'POST':
        try:
            course_count = int(request.POST.get('course-count', 0))
            new_courses = []
            new_canvas_courses = []

            for i in range(course_count):
                if f'course{i}-selected' not in request.POST:
                    continue

                canvas_id = request.POST.get(f'course{i}-canvas_id', None)
                title = request.POST.get(f'course{i}-title', None)
                handle = request.POST.get(f'course{i}-handle', None)

                if not canvas_id:
                    errors.append('Canvas course ID is missing')
                if not title or not handle:
                    errors.append('Must specify title and handle')

                if not errors:
                    new_course = Course(title=title, handle=handle, instructor=instructor)
                    new_courses.append(new_course)
                    new_canvas_courses.append(CanvasCourse(course=new_course, canvas_id=canvas_id))

            if not errors:
                for i in range(len(new_courses)):
                    new_courses[i].save()
                    new_canvas_courses[i].save()
                    canvas.update_enrollment(new_canvas_courses[i])
                return redirect('home')
            else:
                def get_or_throw(key):
                    if key not in request.POST:
                        raise ValueError
                    return request.POST[key]

                try:
                    context['courses'] = [
                        {
                            'canvas_id': get_or_throw(f'course{i}-canvas_id'),
                            'title': get_or_throw(f'course{i}-title'),
                            'handle': get_or_throw(f'course{i}-handle'),
                            'term': get_or_throw(f'course{i}-term'),
                            'total_students': get_or_throw(f'course{i}-total_students'),
                        }
                        for i in range(course_count)
                    ]

                    return render(request, 'lms/import_canvas_courses.html', context)

                except ValueError:
                    pass

        except HTTPError as e:
            errors.append(str(e))

    if context['courses'] is None:
        known_courses = CanvasCourse.objects.filter(course__instructor=instructor)
        known_course_canvas_ids = set(c.canvas_id for c in known_courses)

        try:
            course_data = canvas.download_courses()
            course_data = list(filter(lambda course: course['canvas_id'] not in known_course_canvas_ids, course_data))
            context['courses'] = course_data
        except HTTPError as e:
            errors.append(str(e))

    return render(request, 'lms/import_canvas_courses.html', context)
