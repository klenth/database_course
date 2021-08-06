from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.transaction import atomic
from django.http import Http404
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
        course_count = int(request.POST.get('course-count', 0))

        selected_course = int(request.POST.get('selected-course', 0))

        canvas_id = request.POST.get(f'course{selected_course}-canvas_id', None)
        title = request.POST.get(f'course{selected_course}-title', None)
        handle = request.POST.get(f'course{selected_course}-handle', None)

        if not canvas_id:
            errors.append('Canvas course ID is missing')
        if not title or not handle:
            errors.append('Must specify title and handle')

        if not errors:
            maybe_canvas_course = CanvasCourse.objects.filter(canvas_id=canvas_id)
            if maybe_canvas_course.exists():
                canvas_course = maybe_canvas_course.get()
            else:
                new_course = Course(title=title, handle=handle, instructor=instructor)
                new_course.save()
                new_canvas_course = CanvasCourse(course=new_course, canvas_id=canvas_id)
                new_canvas_course.save()
                canvas_course = new_canvas_course

            canvas.update_enrollment(canvas_course)

            return redirect('home')

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


@login_required
def set_canvas_assignment_auto_update_grade(request, assignment_id):
    instructor = get_object_or_404(Instructor, id=request.user.id)
    assignment = get_object_or_404(CanvasAssignment, pk=assignment_id)

    if assignment.lab.course.instructor != instructor:
        raise Http404

    if request.method != 'POST':
        raise Http404

    old_auto_update_grade = assignment.auto_update_grade
    new_auto_update_grade = 'auto-update' in request.POST

    if new_auto_update_grade != old_auto_update_grade:
        assignment.auto_update_grade = 'auto-update' in request.POST
        assignment.save()

    return redirect('instructor_view_lab', lab_id=assignment.lab.id)


@login_required
def canvas_push_grades(request, assignment_id):
    instructor = get_object_or_404(Instructor, id=request.user.id)
    assignment = get_object_or_404(CanvasAssignment, pk=assignment_id)

    if assignment.lab.course.instructor != instructor:
        raise Http404

    if request.method != 'POST':
        raise Http404

    grades = {
        canvas_student.canvas_id: {
            'score': canvas_student.student.score_on_lab(assignment.lab),
        }
        for canvas_student in CanvasStudent.objects.filter(student__enrollment__course=assignment.lab.course, student__enrollment__active=True)
    }

    canvas.update_grades_if_higher(canvas_assignment=assignment, student_grades=grades)

    return redirect('instructor_view_lab', lab_id=assignment.lab.id)

