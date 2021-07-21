"""cmpt307_dbmanager URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
#    path('admin/', admin.site.urls),
    path('course/<slug:course_handle>/students', views.list_students, name='list_students'),
    path('student/<slug:username>', views.student_details, name='student_details'),
#    path('course/<slug:course_handle>/students/add', views.add_student, name='add_student'),
    path('database/<slug:db_name>', views.database_details, name='database_details'),
    path('database/<slug:db_name>/delete', views.delete_database, name='delete_database'),
    path('database/<slug:db_name>/create_token', views.create_token, name='create_token'),
    path('token/<slug:token_username>', views.token_details, name='token_details'),
    path('token/<slug:token_username>/alter', views.alter_token, name='alter_token'),
    path('profile/<slug:username>', views.view_profile, name='view_profile'),
    path('profile', views.view_profile, name='view_profile'),
    path('', views.student_home, name='student_home'),
    path('course/<slug:course_handle>', views.student_course_home, name='student_course_home'),
    path('login', views.login, name='login'),
    path('logout', views.logout, name='logout'),

    path('database/<slug:db_name>/export', views.export_database, name='export_database'),
    path('export/<uuid:id>', views.export_details, name='export_details'),
    path('export/<uuid:id>/download', views.download_export, name='download_export'),
    path('export/<uuid:id>/delete', views.delete_export, name='delete_export'),
    path('export/<uuid:export_id>/import', views.import_export, name='import_export'),
    path('import/<uuid:id>', views.import_details, name='import_details'),
    path('course/<slug:course_handle>/import', views.import_upload, name='import_upload'),
]

