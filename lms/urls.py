from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    # path('', views.home, name='lms_home'),
    path('import_canvas_courses', views.import_canvas_courses, name='import_canvas_courses'),
    path('set_course_auto_update/<int:assignment_id>', views.set_canvas_assignment_auto_update_grade, name='set_canvas_assignment_auto_update_grade'),
    path('push_grades/<int:assignment_id>', views.canvas_push_grades, name='canvas_push_grades'),
]
