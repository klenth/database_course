from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    # path('', views.home, name='lms_home'),
    path('import_canvas_courses', views.import_canvas_courses, name='import_canvas_courses'),
]
