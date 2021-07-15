from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.apps import apps
from django.shortcuts import reverse
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
                    'href': course_settings.LAB_PREFIX + reverse('lab_home', urlconf=lab_urlconf),
                })

            if apps.is_installed('dbmanager') or True:
                links.append({
                    'text': 'Database manager',
                    'explanation': 'Create and manage your databases on the class database server',
                    'href': course_settings.DBMANAGER_PREFIX + reverse('student_course_home', urlconf=dbmanager_urlconf, kwargs={'course_handle': course.handle}),
                })

            courses_data.append(course_data)

        context = {
            'courses': courses_data,
        }

        return render(request, 'course/student_home.html', context)

    maybe_instructor = Instructor.objects.filter(id=request.user.id)
    if maybe_instructor.exists():
        instructor = maybe_instructor.get()
        raise Http404
