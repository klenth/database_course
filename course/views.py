from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.apps import apps
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import reverse
from django.utils.text import slugify
from django.utils import timezone
from .models import *
from . import util


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


@login_required
def student_detail(request, student_uuid=None):
    instructor = get_object_or_404(Instructor, id=request.user.id)
    student = get_object_or_404(Student, pk=student_uuid)

    context = {
        'student': student,
        'instructor': instructor,
    }

    return render(request, 'course/student_detail.html', context)


@login_required
def edit_student(request, student_uuid=None, course_handle=None):
    student = get_object_or_404(Student, pk=student_uuid) if student_uuid else None
    course = get_object_or_404(Course, handle=course_handle) if course_handle else None

    access_allowed = False

    maybe_student = Student.objects.filter(id=request.user.id)
    # If the logged-in user is a student, the only student they can edit is themselves
    if maybe_student.exists():
        access_allowed = (student == maybe_student.get())

    # If the logged-in user is an instructor, the student must be enrolled in one of their classes
    else:
        maybe_instructor = Instructor.objects.filter(id=request.user.id)
        if maybe_instructor.exists():
            instructor = maybe_instructor.get()
            if student is None or Enrollment.objects.filter(course__instructor=instructor, student=student).exists():
                access_allowed = True

    if not access_allowed:
        raise Http404

    context = {
        'student': student,
    }

    if course_handle:
        context['course_handle'] = course_handle

    if 'next' in request.GET:
        context['next'] = request.GET['next']
    elif student_uuid is None and course_handle is not None:
        context['next'] = reverse('course_detail', kwargs={'course_handle': course_handle})

    if student:
        context['name'] = student.name
        context['email'] = student.email

    if request.method == 'POST':
        if 'next' in request.POST:
            context['next'] = request.POST['next']

        # The username should only be there if we are creating a new student
        username = (request.POST.get('username') or '') if not student else None
        name = request.POST.get('name')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        errors = util.validate_user_information(name=name, email=email, password1=password1, password2=password2, username=username)

        if errors:
            context['errors'] = errors
        else:
            student = student or Student(username=username)
            student.name = name
            student.email = email
            student.set_password(password1)
            student.save()

            if course:
                e = Enrollment(course=course, student=student)
                e.save()

            if 'next' in request.POST:
                return HttpResponseRedirect(request.POST['next'])
            else:
                return redirect('home')

    return render(request, 'course/edit_student.html', context)


@login_required
def create_account_setup_link(request, student_uuid):
    import datetime
    student = get_object_or_404(Student, pk=student_uuid)
    instructor = get_object_or_404(Instructor, id=request.user.id)

    if not Enrollment.objects.filter(course__instructor=instructor, student=student).exists():
        raise Http404

    context = {
        'student': student,
        'expiry_days': 7,
        'email': student.email,
        'send_email': False,
    }

    if request.method == 'POST':
        expiry_days = request.POST.get('expiry-days')
        send_email = 'send-email' in request.POST
        email = request.POST.get('email')

        context['expiry_days'] = expiry_days
        context['send_email'] = send_email
        context['email'] = email

        errors = []
        context['errors'] = errors

        try:
            expiry_days = int(expiry_days)
        except ValueError:
            errors.append('Days until expiration must be a whole number')

        if expiry_days < 1:
            errors.append('Days until expiration must be at least 1')

        if send_email and (not email or not '@' in email):
            errors.append('Must specify a valid email address')

        if not errors:
            expiry_date = timezone.now() + datetime.timedelta(days=expiry_days)

            # Cancel any existing links for this student
            for existing_link in AccountSetupLink.objects.filter(student=student):
                existing_link.delete()

            link = AccountSetupLink(student=student, expiration=expiry_date)
            link.save()

            if send_email:
                util.email_account_setup_link(link, email, instructor=instructor)

            return redirect('course_view_account_setup_link', student_uuid=student.uuid)

    return render(request, 'course/create_account_setup_link.html', context)


@login_required
def view_account_setup_link(request, student_uuid):
    from database_course.settings import SITE_BASE_URL
    instructor = get_object_or_404(Instructor, id=request.user.id)
    student = get_object_or_404(Student, pk=student_uuid)

    if not Enrollment.objects.filter(student=student, course__instructor=instructor).exists():
        # Student is not in a class taught by the instructor who is logged in
        raise Http404

    link = get_object_or_404(AccountSetupLink, student=student)

    context = {
        'student': student,
        'link': link,
        'setup_url': SITE_BASE_URL + reverse('course_setup_account', kwargs={'link_id': link.id}),
    }

    return render(request, 'course/view_account_setup_link.html', context)


def setup_account(request, link_id):
    link = get_object_or_404(AccountSetupLink, pk=link_id)
    student = link.student
    now = timezone.now()

    if now >= link.expiration:
        raise Http404

    if request.method == 'POST':
        name = request.POST.get('name', None)
        email = request.POST.get('email', None)
        password1 = request.POST.get('password1', None)
        password2 = request.POST.get('password2', None)

        errors = util.validate_user_information(name=name, email=email, password1=password1, password2=password2)

        if errors:
            context = {
                'errors': errors,
                'student': link.student,
                'link': link,
                'name': name,
                'email': email,
                'account_setup': True,
            }

            return render(request, 'course/edit_student.html', context)
        else:
            student.name = name
            student.email = email
            student.set_password(password1)
            student.save()
            link.delete()

            return redirect('setup_account_complete')

    elif request.method == 'GET':
        context = {
            'student': link.student,
            'link': link,
            'name': student.name,
            'email': student.email,
            'account_setup': True,
        }

        return render(request, 'course/edit_student.html', context)

    raise Http404


def setup_account_complete(request):
    return render(request, 'course/setup_account_complete.html', {})
