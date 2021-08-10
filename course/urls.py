from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    # path('', views.home, name='lms_home'),
    path('courses', views.courses_home, name='courses_home'),
    path('courses/create', views.courses_home, name='create_course'),
    path('course/<slug:course_handle>', views.course_detail, name='course_detail'),
    path('students/<uuid:student_uuid>', views.student_detail, name='course_student_detail'),

    path('course/<slug:course_handle>/students/new', views.edit_student, name='course_new_student'),
    path('students/<uuid:student_uuid>/edit', views.edit_student, name='course_edit_student'),

    path('students/<uuid:student_uuid>/make_setup_link', views.create_account_setup_link, name='course_create_account_setup_link'),
    path('students/<uuid:student_uuid>/view_setup_link', views.view_account_setup_link, name='course_view_account_setup_link'),

    path('setup/<slug:link_id>', views.setup_account, name='setup_account'),
    path('setup_complete', views.setup_account_complete, name='setup_account_complete'),
]
