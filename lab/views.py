from django.shortcuts import render, get_object_or_404, redirect
from django.http import Http404
import django.contrib.auth.decorators as auth_decorators
from .models import *
from . import instructor_views, student_views
from django.utils import timezone


@auth_decorators.login_required
def home(request):
    r = Person.resolve(request.user)
    if r[0] == 'Student':
        return student_views.student_home(request, r[1])
    elif r[0] == 'Instructor':
        return instructor_views.instructor_home(request, r[1])
    else:
        raise Http404
