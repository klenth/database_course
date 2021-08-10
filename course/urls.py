from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    # path('', views.home, name='lms_home'),
    path('courses', views.courses_home, name='courses_home'),
    path('courses/create', views.courses_home, name='create_course'),
    path('course/<slug:course_handle>', views.course_detail, name='course_detail'),

    path('setup/<slug:link_id>', views.setup_account, name='setup_account'),
    path('setup_complete', views.setup_account_complete, name='setup_account_complete'),
]
