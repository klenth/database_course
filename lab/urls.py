from django.contrib import admin
from django.urls import path
from . import views, student_views, instructor_views, ajax_views

urlpatterns = [
    path('', views.home, name='lab_home'),
    path('lab/<uuid:lab_id>', student_views.view_lab, name='student_view_lab'),
    path('lab/p/<uuid:problem_id>', student_views.view_problem, name='student_view_problem'),
    path('lab/p/<uuid:problem_id>/<uuid:attempt_id>', student_views.view_problem, name='student_view_problem_attempt'),

    path('i/student', instructor_views.dummy_home, name='instructor_dummy_home'),
    path('i/course/new', instructor_views.edit_course, name='instructor_new_course'),
    path('i/course/<slug:course_handle>/edit', instructor_views.edit_course, name='instructor_edit_course'),
    path('i/c/<slug:course_handle>/lab/new', instructor_views.edit_lab, name='instructor_new_lab'),
    path('i/c/<slug:course_handle>/lab/<uuid:lab_id>/edit', instructor_views.edit_lab, name='instructor_edit_lab'),
    path('i/lab/<uuid:lab_id>', instructor_views.view_lab, name='instructor_view_lab'),
    path('i/lab/<uuid:lab_id>/new_problem', instructor_views.new_problem, name='instructor_new_problem'),
    path('i/lab/p/<uuid:problem_id>', instructor_views.view_problem, name='instructor_view_problem'),
    path('i/lab/p/<uuid:problem_id>/schema', instructor_views.download_schema, name='instructor_download_schema'),
    path('i/lab/p/data/<uuid:table_data_id>', instructor_views.download_table_data, name='instructor_download_table_data'),
    path('i/lab/p/data/', instructor_views.download_table_data, name='instructor_download_table_data_dummy'),
    path('i/lab/p/<uuid:problem_id>/enable', instructor_views.enable_problem, name='instructor_enable_problem'),
    path('i/lab/p/<uuid:problem_id>/disable', instructor_views.disable_problem, name='instructor_disable_problem'),
    path('i/lab/p/<uuid:problem_id>/duplicate', instructor_views.duplicate_problem, name='instructor_duplicate_problem'),
    path('i/lab/p/<uuid:problem_id>/delete', instructor_views.delete_problem, name='instructor_delete_problem'),
    path('i/lab/<uuid:lab_id>/enable', instructor_views.enable_lab, name='instructor_enable_lab'),
    path('i/lab/<uuid:lab_id>/disable', instructor_views.disable_lab, name='instructor_disable_lab'),
    path('i/lab/<uuid:lab_id>/duplicate', instructor_views.duplicate_lab, name='instructor_duplicate_lab'),
    path('i/lab/<uuid:lab_id>/delete', instructor_views.delete_lab, name='instructor_delete_lab'),

    path('ajax/i/lab/p/<uuid:problem_id>', ajax_views.instructor_update_problem, name='ajax_instructor_update_problem'),
    path('ajax/i/lab/upload_schema', ajax_views.instructor_upload_schema, name='ajax_instructor_upload_schema'),
    path('ajax/i/lab/check_schema_status', ajax_views.instructor_check_schema_status, name='ajax_instructor_check_schema_status'),
    path('ajax/i/lab/p/<uuid:problem_id>/get_data_files', ajax_views.instructor_get_data_files, name='ajax_instructor_get_data_files'),
    path('ajax/i/lab/p/<uuid:problem_id>/upload_data_file', ajax_views.instructor_upload_data_file, name='ajax_instructor_upload_data_file'),
    path('ajax/i/lab/p/<uuid:problem_id>/remove_data_file', ajax_views.instructor_remove_data_file, name='ajax_instructor_remove_data_file'),
    path('ajax/i/lab/p/<uuid:problem_id>/get_test_cases', ajax_views.instructor_get_test_cases, name='ajax_instructor_get_test_cases'),
    path('ajax/i/lab/p/<uuid:problem_id>/add_test_case', ajax_views.instructor_add_test_case, name='ajax_instructor_add_test_case'),
    path('ajax/i/lab/p/<uuid:problem_id>/delete_test_case', ajax_views.instructor_delete_test_case, name='ajax_instructor_delete_test_case'),
    path('ajax/i/lab/p/<uuid:problem_id>/update_test_case', ajax_views.instructor_update_test_case, name='ajax_instructor_update_test_case'),
    path('ajax/i/lab/p/<uuid:problem_id>/validate', ajax_views.instructor_validate_problem, name='ajax_instructor_validate_problem'),
    path('ajax/i/lab/p/<uuid:problem_id>/view_markdown', ajax_views.instructor_view_markdown, name='ajax_instructor_view_markdown'),
]
