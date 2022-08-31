from django.shortcuts import render, get_object_or_404, redirect, reverse
from django.views.decorators import csrf as csrf_decorators
from django.http import Http404, HttpResponse
import django.contrib.auth.decorators as auth_decorators

import lms.canvas
from .models import *
from lms.models import CanvasCourse, CanvasAssignment
from django.apps import apps


def instructor_home(request, instructor):
    context = {
        'instructor': instructor,
    }

    return render(request, 'lab/instructor/instructor_home.html', context)


@auth_decorators.login_required
def dummy_home(request):
    from . import student_views
    instructor = get_object_or_404(Instructor, id=request.user.id)
    return student_views.student_home(request, instructor.dummy())


@auth_decorators.login_required
def edit_course(request, course_handle=None):
    course = get_object_or_404(Course, handle=course_handle) if course_handle else None
    instructor = get_object_or_404(Instructor, id=request.user.id)
    if course and course.instructor != instructor:
        raise Http404

    context = {
        'course': course,
        'errors': [],
    }

    if request.method == 'POST':
        if not course:
            course = Course(instructor=instructor)
        title = request.POST['title'].strip()

        if title == '':
            context['errors'].append('Course title cannot be blank')

        clashing_courses = Course.objects.filter(title=title, instructor=instructor)
        if course:
            clashing_courses = clashing_courses.exclude(pk=course.id)

        if clashing_courses.exists():
            context['errors'].append('You already have a course with that title')
            context['course_title'] = title

        if not context['errors']:
            course.title = request.POST['title']
            course.save()
            return redirect('lab_home')

    return render(request, 'lab/instructor/edit_course.html', context)


@auth_decorators.login_required
def edit_lab(request, course_handle, lab_id=None):
    course = get_object_or_404(Course, handle=course_handle)
    lab = get_object_or_404(Lab, pk=lab_id) if lab_id else None
    instructor = get_object_or_404(Instructor, id=request.user.id)
    if course.instructor != instructor \
            or lab and lab.course != course:
        raise Http404

    context = {
        'course': course,
        'lab': lab,
        'errors': [],
    }

    if request.method == 'POST':
        if not lab:
            lab = Lab(course=course)
        title = request.POST['title'].strip()

        if title == '':
            context['errors'].append('Lab title cannot be blank')

        clashing_labs = Lab.objects.filter(title=title, course=course)
        if lab:
            clashing_labs = clashing_labs.exclude(pk=lab.id)

        if clashing_labs.exists():
            context['errors'].append('This course already has a lab with that title')
            context['lab_title'] = title

        if not context['errors']:
            lab.title = request.POST['title']
            lab.save()
            return redirect('lab_home')

    return render(request, 'lab/instructor/edit_lab.html', context)


@auth_decorators.login_required
def view_lab(request, lab_id):
    instructor = get_object_or_404(Instructor, id=request.user.id)
    lab = get_object_or_404(Lab, pk=lab_id)

    if lab.course.instructor != instructor:
        raise Http404

    canvas_enabled = apps.is_installed('lms') and CanvasCourse.objects.filter(course=lab.course).exists()
    lab_problems = lab.problems.order_by('problemonlab__problem_number')

    context = {
        'lab': lab,
        'enabled_problems': lab_problems.filter(enabled=True),
        'disabled_problems': lab_problems.filter(enabled=False),
        'student_href': reverse('student_view_lab', kwargs={'lab_id': lab.id}),
        'canvas_integration_enabled': canvas_enabled,
    }

    if canvas_enabled:
        maybe_canvas_assignment = CanvasAssignment.objects.filter(lab=lab)
        context['canvas_assignment'] = maybe_canvas_assignment.get() if maybe_canvas_assignment.exists() else None

    return render(request, 'lab/instructor/view_lab.html', context)


@auth_decorators.login_required
def link_lab_to_canvas_assignment(request, lab_id):
    instructor = get_object_or_404(Instructor, id=request.user.id)
    lab = get_object_or_404(Lab, pk=lab_id)

    if lab.course.instructor != instructor:
        raise Http404

    canvas_course = apps.is_installed('lms') and CanvasCourse.objects.filter(course=lab.course).get()

    context = {
        'lab': lab,
        'canvas_course': canvas_course,
        'errors': [],
    }

    if request.method == 'POST':
        if 'unlink_canvas_assignment_id' in request.POST:
            maybe_canvas_assignment = CanvasAssignment.objects.filter(pk=request.POST['unlink_canvas_assignment_id'])
            if maybe_canvas_assignment.exists() and (canvas_assignment := maybe_canvas_assignment.get()).lab.id == lab.id:
                canvas_assignment.delete()
            return redirect('instructor_view_lab', lab_id=lab.id)

        elif 'canvas_assignment_id' not in request.POST:
            context['errors'].append('No Canvas assignment ID given')

        else:
            canvas_assignment = CanvasAssignment(
                lab=lab,
                canvas_id=request.POST['canvas_assignment_id']
            )
            canvas_assignment.save()

            return redirect('instructor_view_lab', lab_id=lab.id)

    else:
        assignments = lms.canvas.download_assignments_for_course(canvas_course)
        context['canvas_assignments'] = assignments

    return render(request, 'lab/instructor/link_lab_to_canvas_assignment.html', context)


@auth_decorators.login_required
def new_problem(request, lab_id):
    instructor = get_object_or_404(Instructor, id=request.user.id)
    lab = get_object_or_404(Lab, pk=lab_id)

    if lab.course.instructor != instructor:
        raise Http404

    if request.method != 'POST':
        raise Http404

    new_problem_number = lab.problems.count() + 1
    p = Problem(title=f'Problem {new_problem_number}')
    p.save()
    pol = ProblemOnLab(lab=lab, problem=p, problem_number=new_problem_number)
    pol.save()

    return redirect('instructor_view_problem', problem_id=p.id)

@auth_decorators.login_required
def enable_problem(request, problem_id, enabled=True):
    if request.method != 'POST':
        raise Http404

    instructor = get_object_or_404(Instructor, id=request.user.id)
    problem = get_object_or_404(Problem, pk=problem_id)
    lab = problem.lab()
    if lab.course.instructor.id != instructor.id:
        raise Http404

    problem.enabled = enabled
    problem.save()

    return redirect('instructor_view_lab', lab_id=lab.id)


def disable_problem(request, problem_id):
    return enable_problem(request, problem_id, enabled=False)


@auth_decorators.login_required
def enable_lab(request, lab_id, enabled=True):
    if request.method != 'POST':
        raise Http404

    instructor = get_object_or_404(Instructor, id=request.user.id)
    lab = get_object_or_404(Lab, pk=lab_id)
    if lab.course.instructor.id != instructor.id:
        raise Http404

    lab.enabled = enabled
    lab.save()

    return redirect('lab_home')


def disable_lab(request, lab_id):
    return enable_lab(request, lab_id, enabled=False)


@auth_decorators.login_required
def duplicate_problem(request, problem_id):
    if request.method != 'POST':
        raise Http404

    instructor = get_object_or_404(Instructor, id=request.user.id)
    problem = get_object_or_404(Problem, pk=problem_id)
    lab = problem.lab()
    if lab.course.instructor.id != instructor.id:
        raise Http404

    new_problem = problem.duplicate()
    # Add it to the same lab
    lab.add_problem(new_problem)

    return redirect('instructor_view_lab', lab_id=lab.id)


@auth_decorators.login_required
def duplicate_lab(request, lab_id):
    if request.method != 'POST':
        raise Http404

    instructor = get_object_or_404(Instructor, id=request.user.id)
    lab = get_object_or_404(Lab, pk=lab_id)

    if lab.course.instructor.id != instructor.id:
        raise Http404

    new_lab = lab.duplicate()

    return redirect('lab_home')


@auth_decorators.login_required
def delete_problem(request, problem_id):
    if request.method != 'POST':
        raise Http404

    instructor = get_object_or_404(Instructor, id=request.user.id)
    problem = get_object_or_404(Problem, pk=problem_id)
    lab = problem.lab()
    if lab.course.instructor.id != instructor.id:
        raise Http404

    problem.delete()

    return redirect('instructor_view_lab', lab_id=lab.id)


@auth_decorators.login_required
def delete_lab(request, lab_id):
    if request.method != 'POST':
        raise Http404

    instructor = get_object_or_404(Instructor, id=request.user.id)
    lab = get_object_or_404(Lab, pk=lab_id)
    if lab.course.instructor.id != instructor.id:
        raise Http404

    problems = list(lab.problems.all())
    for problem in problems:
        problem.delete()

    lab.delete()

    return redirect('lab_home')


@csrf_decorators.ensure_csrf_cookie
@auth_decorators.login_required
def view_problem(request, problem_id):
    instructor = get_object_or_404(Instructor, id=request.user.id)
    problem = get_object_or_404(Problem, pk=problem_id)

    if problem.lab().course.instructor != instructor:
        raise Http404

    context = {
        'problem': problem,
        'student_href': reverse('student_view_problem', kwargs={'problem_id': problem_id})
    }

    return render(request, 'lab/instructor/view_problem.html', context)


@auth_decorators.login_required
def download_schema(request, problem_id):
    instructor = get_object_or_404(Instructor, id=request.user.id)
    problem = get_object_or_404(Problem, pk=problem_id)

    if problem.lab().course.instructor != instructor:
        raise Http404

    if not problem.schema:
        raise Http404

    headers = {
        'Content-Type': 'text/plain'
    }

    if 'download' in request.GET or 'download' in request.POST:
        headers['Content-Type'] = 'application/sql'
        headers['Content-Disposition'] = f'attachment; filename="{problem.schema.filename}"'
        print(headers['Content-Disposition'])

    return HttpResponse(
        content=problem.schema.file,
        headers=headers
    )


@auth_decorators.login_required
def download_table_data(request, table_data_id):
    instructor = get_object_or_404(Instructor, id=request.user.id)
    table_data = get_object_or_404(ProblemTableData, pk=table_data_id)

    if table_data.problem.lab().course.instructor != instructor:
        raise Http404

    headers = {
        'Content-Type': 'text/plain'
    }

    if 'download' in request.GET or 'download' in request.POST:
        headers['Content-Type'] = 'application/sql'
        headers['Content-Disposition'] = f'attachment; filename="{table_data.data_filename}"'

    return HttpResponse(
        content=table_data.data_file,
        headers=headers
    )
