from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.apps import apps
from django.http import Http404
from django.shortcuts import reverse
from django.utils.text import slugify
from .models import *
from lab import urls as lab_urlconf
from dbmanager import urls as dbmanager_urlconf
from database_course import settings as course_settings


@login_required
def home(request):
    maybe_student = Student.objects.filter(id=request.user.id)
    if maybe_student.exists():
        student = maybe_student.get()
        courses = Course.objects.filter(enrollment__student=student, enrollment__active=True)
        courses_data = []

        for course in courses:
            links = []
            course_data = {
                'id': course.id,
                'title': course.title,
                'links': links,
            }
            if apps.is_installed('lab') or True:
                links.append({
                    'text': 'Lab',
                    'explanation': 'Work on assigned SQL labs',
                    'href': reverse('lab_home', current_app='course'),
                })

            if apps.is_installed('dbmanager') or True:
                links.append({
                    'text': 'Database manager',
                    'explanation': 'Create and manage your databases on the class database server',
                    'href': reverse('student_course_home', current_app='course', kwargs={'course_handle': course.handle}),
                })

            courses_data.append(course_data)

        context = {
            'courses': courses_data,
        }

        return render(request, 'course/student_home.html', context)

    maybe_instructor = Instructor.objects.filter(id=request.user.id)
    if maybe_instructor.exists():
        instructor = maybe_instructor.get()
        links = []

        links.append({
            'text': 'Course management',
            'explanation': 'Add, modify, and manage courses in the system',
            'href': reverse('courses_home', current_app='course'),
        })

        if apps.is_installed('lab'):
            links.append({
                'text': 'SQL Lab',
                'explanation': 'SQL lab platform',
                'href': reverse('lab_home', current_app='course'),
            })

        if apps.is_installed('dbmanager'):
            links.append({
                'text': 'Database manager',
                'explanation': 'Manage student databases',
                'href': reverse('student_home', current_app='course'),
            })

        context = {
            'links': links,
        }

        return render(request, 'course/instructor_home.html', context)

    raise Http404


@login_required
def courses_home(request):
    instructor = get_object_or_404(Instructor, id=request.user.id)
    courses = instructor.courses.all()

    context = {
        'instructor': instructor,
        'courses': courses,
        'show_canvas_import': apps.is_installed('lms'),
    }

    if request.method == 'POST':
        errors = []
        context['errors'] = errors

        new_title = request.POST.get('new-course-title')
        new_handle = request.POST.get('new-course-handle')
        handle = slugify(new_handle)

        if not new_title:
            errors.append('Must specify a title')
        if not new_handle:
            errors.append('Must specify a handle')
        if handle != new_handle:
            errors.append('Course handle must consist of letters, digits, underscores, and/or hyphens')

        if not errors:
            new_course = Course(title=new_title, handle=handle, instructor=instructor)
            new_course.save()
            return redirect('course_detail', course_handle=new_course.handle)
        else:
            context['new_course_title'] = new_title
            context['new_course_handle'] = new_handle

    return render(request, 'course/courses_home.html', context)


@login_required
def course_detail(request, course_handle):
    instructor = get_object_or_404(Instructor, id=request.user.id)
    course = get_object_or_404(Course, handle=course_handle)

    active_students = course.students.filter(enrollment__active=True)
    inactive_students = course.students.exclude(enrollment__active=True)

    context = {
        'instructor': instructor,
        'course': course,
        'active_students': active_students,
        'inactive_students': inactive_students,
    }

    return render(request, 'course/course_detail.html', context)

