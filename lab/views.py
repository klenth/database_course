from django.shortcuts import render, get_object_or_404, redirect
from django.http import Http404
import django.contrib.auth.decorators as auth_decorators
from .models import *
from . import instructor_views, student_views
from django.utils import timezone
import datetime


@auth_decorators.login_required
def home(request):
    r = Person.resolve(request.user)
    if r[0] == 'Student':
        return student_views.student_home(request, r[1])
    elif r[0] == 'Instructor':
        return instructor_views.instructor_home(request, r[1])
    else:
        raise Http404


def setup_account(request, link_id):
    from django.contrib.auth.models import User

    link = get_object_or_404(AccountSetupLink, pk=link_id)
    student = link.student
    now = timezone.now()

    if now >= link.expiration:
        raise Http404

    if request.method == 'POST':
        name = request.POST.get('name', None)
        email = request.POST.get('email', None)
        username = request.POST.get('username', None)
        password1 = request.POST.get('password1', None)
        password2 = request.POST.get('password2', None)

        errors = []

        # Validate name
        if not name:
            errors.append('You must specify a name')

        # Validate email
        if not email:
            errors.append('You must specify an email address')
        elif '@' not in email:
            errors.append('Email address must contain an "@"')

        # Validate username
        if not username:
            errors.append('You must specify a username')
        elif '/' in username:
            errors.append('Invalid username')
        else:
            clashing_person = User.objects.filter(username=username).exclude(id=student.id)
            if clashing_person.exists():
                errors.append('That username is already taken; please choose another')

        # Validate password
        if not password1 or not password2:
            errors.append('You must specify a password')
        elif password1 != password2:
            errors.append('Passwords must match')
        elif not util.validate_password(password1):
            errors.append('Password must be at least eight characters long and contain at least three of the following: lowercase letter, uppercase letter, digit, non-alphanumeric character, and alphabetic letter without case')

        if errors:
            context = {
                'errors': errors,
                'student': link.student,
                'link': link,
                'name': name,
                'email': email,
                'username': username,
            }

            return render(request, 'setup_account.html', context)
        else:
            student.name = name
            student.email = email
            student.username = username
            student.set_password(password1)
            student.save()
            link.delete()

            return redirect('setup_account_complete')

    elif request.method == 'GET':
        context = {
            'student': link.student,
            'link': link,
            'name': None,
            'email': None,
            'username': None,
        }

        return render(request, 'setup_account.html', context)

    raise Http404


def setup_account_complete(request):
    return render(request, 'setup_account_complete.html', {})
