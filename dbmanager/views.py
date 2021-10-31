from django.shortcuts import render, get_object_or_404, redirect, reverse
from django.http import Http404, HttpResponseRedirect, FileResponse
from dbmanager.models import *
import re
from django.contrib import auth
from django.contrib.auth.models import User
from django.utils import timezone
from course.models import *


def login_if_unauthenticated(to=None):
    """Decorator that redirects a view to the login page if the user is not authenticated. The to argument must be
    a string of the view name (as in urls.py) that the login should redirect to after completion; if omitted, the function's
    name is used. Function arguments are automatically forwarded to reverse() to form the redirect URL."""
    reverse_name = to if to is not None else to.__name__

    if callable(to):
        f = to
        reverse_name = f.__name__

        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return HttpResponseRedirect(reverse('login') + '?next=' + reverse(reverse_name, args=args,
                                                                                   kwargs=kwargs))
            else:
                return f(request, *args, **kwargs)

        return wrapper
    else:
        def delegate(f):

            def wrapper(request, *args, **kwargs):
                if not request.user.is_authenticated:
                    return HttpResponseRedirect(reverse('login')) + '?next=' + reverse(reverse_name, args=args,
                                                                                       kwargs=kwargs)
                else:
                    return f(request, *args, **kwargs)

        return delegate


def list_students(request, course_handle):
    if not request.user.is_superuser:
        raise Http404
    course = get_object_or_404(Course, handle=course_handle)

    context = {
        'course': course,
        'students': course.students.exclude(is_dummy=True).order_by('username'),
    }

    return render(request, 'dbmanager/list_students.html', context)


def student_details(request, username):
    if not request.user.is_superuser:
        raise Http404

    student = get_object_or_404(Student, username=username)

    context = {
        'student': student,
        'student_dbs': student.databases.all(),
        'other_dbs': student.other_databases.all(),
    }

    if request.method == 'POST':
        if 'action' in request.POST and request.POST['action'] == 'new_database':
            if 'db_name' in request.POST:
                db_name = request.POST['db_name']
                if StudentDatabase.is_valid_name(db_name):
                    try:
                        created_db = student.create_database(db_name)
                        if created_db:
                            context['created_db'] = created_db
                        else:
                            context['created_db_error'] = 'Database already exists'
                    except ValueError as e:
                        context['created_db_error'] = str(e)
                else:
                    context['created_db_error'] = 'Invalid database name'
            else:
                context['created_db_error'] = 'No database name specified'
        else:
            raise Http404

    return render(request, 'dbmanager/student_details.html', context)


# @login_if_unauthenticated
# def add_student(request, course_handle):
#     instructor = get_object_or_404(Instructor, id=request.user.id)
#     course = get_object_or_404(Course, handle=course_handle)
#
#     if course.instructor.id != instructor.id:
#         raise Http404
#
#     context = {
#         'course': course,
#         'errors': []
#     }
#
#     if request.method == 'POST':
#         if 'username' in request.POST and request.POST['username'] \
#                 and 'password' in request.POST and request.POST['password']:
#             username = request.POST['username']
#             password = request.POST['password']
#
#             valid_username_pattern = re.compile(r'^[\d\w_\-]+$')
#             if not valid_username_pattern.match(username) or len(username) > Student.MAX_USERNAME_LENGTH:
#                 context['errors'].append('Invalid username')
#
#             student = Student.create(username=username, password=password)
#             if 'first_name' in request.POST and request.POST['first_name']:
#                 student.first_name = request.POST['first_name']
#             if 'last_name' in request.POST and request.POST['last_name']:
#                 student.last_name = request.POST['last_name']
#             if 'student_id' in request.POST and request.POST['student_id']:
#                 student.student_id = request.POST['student_id']
#             if 'email' in request.POST and request.POST['email']:
#                 student.email = request.POST['email']
#
#             student.save()
#
#             if 'next' in request.POST and request.POST['next']:
#                 return redirect(request.POST['next'])
#         else:
#             raise Http404
#
#     return render(request, 'dbmanager/add_student.html', {})


@login_if_unauthenticated
def student_home(request):
    maybe_instructor = Instructor.objects.filter(id=request.user.id)
    if maybe_instructor.exists():
        return instructor_home(request)

    #student_query = Student.objects.filter(id=request.user.id)
    #student = student_query.get() if student_query.exists() else None
    student = get_object_or_404(Student, id=request.user.id)

    courses = Course.objects.filter(enrollment__student=student, enrollment__active=True)
    if len(courses) == 1:
        return redirect('student_course_home', course_handle=courses.get().handle)
    else:
        context = {
            'student': student,
            'courses': courses,
        }
        return render(request, 'dbmanager/student_home.html', context)


@login_if_unauthenticated
def instructor_home(request):
    instructor = get_object_or_404(Instructor, id=request.user.id)

    context = {
        'courses': Course.objects.filter(instructor=instructor)
    }

    return render(request, 'dbmanager/instructor_home.html', context)


@login_if_unauthenticated
def student_course_home(request, course_handle):
    course = get_object_or_404(Course, handle=course_handle)
    student_query = Student.objects.filter(id=request.user.id)

    student = student_query.get() if student_query.exists() else None

    context = {
        'student': student,
        'course': course,
        #'exports': student.exports.order_by('request_time'),
        'max_db_name_length': StudentDatabase.MAX_NAME_LENGTH - (len(student.username) + 1),
        'new_db_errors': [],
    }

    if request.method == 'POST':
        if 'action' in request.POST and request.POST['action'] == 'new_database':
            if request.POST.get('database_name', None):
                db_name = student.username + '_' + request.POST['database_name']
                if StudentDatabase.objects.filter(name=db_name).exists():
                    context['new_db_errors'].append('Database {} already exists.'.format(db_name))
                elif StudentDatabase.is_valid_name(db_name):
                    # context['new_db'] = student.create_database(db_name)
                    context['new_db'] = StudentDatabase.create(student, course, db_name)
                    return redirect('student_course_home', course_handle=course.handle)
                else:
                    context['new_db_errors'].append("Invalid database name: {} (database names can be up to {} characters long and may be composed of only letters, digits, and underscores)".format(db_name, StudentDatabase.MAX_NAME_LENGTH))
            else:
                context['new_db_errors'].append("Missing database name.")
        else:
            raise Http404

    return render(request, 'dbmanager/student_course_home.html', context)


def logout(request):
    auth.logout(request)
    if 'next' in request.GET:
        return HttpResponseRedirect(request.GET['next'])
    else:
        return redirect('student_home')


def login(request):
    context = {
        'login_errors': [],
        'next': None
    }
    if request.method == 'POST' \
            and 'username' in request.POST \
            and 'password' in request.POST:
        u_q = User.objects.filter(username=request.POST['username'])
        if u_q.exists():
            u = get_object_or_404(User, username=request.POST['username'])
            if not u.is_active:
                context['login_errors'].append(f'The {u.username} user is inactive.')
            elif u.check_password(request.POST['password']):
                auth.login(request, u)
                if 'next' in request.POST:
                    return HttpResponseRedirect(request.POST['next'])
                else:
                    return redirect('student_home')
            else:
                context['username'] = request.POST['username']
                context['login_errors'].append('Username and password do not match.')
        else:
            context['login_errors'].append('Username and password do not match.')

    if request.method == 'POST' and 'next' in request.POST:
        context['next'] = request.POST['next']
    elif request.method == 'GET' and 'next' in request.GET:
        context['next'] = request.GET['next']

    return render(request, 'login.html', context)


@login_if_unauthenticated
def database_details(request, db_name):
    db = get_object_or_404(StudentDatabase, name=db_name)
    if request.user.is_superuser:
        student = db.owner
    else:
        student = get_object_or_404(Student, id=request.user.id)

    is_owner = db.owner.id == request.user.id
    is_shared = student in db.other_students.all()
    if not is_owner and not is_shared and not request.user.is_superuser:
        raise Http404

    context = {
        'student': student,
        'database': db,
        'is_owner': is_owner,
        'is_shared': is_shared,
        'change_share_errors': [],
    }

    if is_shared:
        context['is_readonly'] = not student.shared_databases.get(database=db).write_permission

    if request.method == 'POST':
        if 'action' in request.POST and request.POST['action'] == 'change_shares':
            share_index = 0
            while True:
                id_stem = 'access_{}'.format(share_index)
                if id_stem + '_student' not in request.POST:
                    break

                username = request.POST[id_stem + '_student']
                student_query = Student.objects.filter(username=username)
                if not student_query.exists():
                    context['change_share_errors'].append('No such user: {}'.format(username))
                else:
                    student = student_query.get()
                    write_permission = id_stem in request.POST and request.POST[id_stem] == 'rw'
                    unshare = id_stem + '_unshare' in request.POST
                    if unshare:
                        db.unshare_with(student)
                    else:
                        db.share_with(student, write_permission)

                share_index += 1

            if not context['change_share_errors']:
                return redirect('database_details', db_name=db_name)

        else:
            raise Http404

    already_shared_student_ids = list(db.other_students.values_list('id', flat=True)) + [db.owner.id]
    context['unshared_students'] = db.course.students.exclude(id__in=already_shared_student_ids)

    return render(request, 'dbmanager/database_details.html', context)


@login_if_unauthenticated
def view_profile(request, username=None):
    if username is None:
        username = request.user.username

    student = get_object_or_404(Student, username=username)
    editable = student.id == request.user.id or request.user.is_superuser

    context = {
        'student': student,
        'editable': editable,
        'update_profile_errors': [],
        'update_profile_message': None,
    }

    if request.method == 'POST':
        if editable:
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            password = request.POST.get('password', '').strip()

            if not first_name:
                context['update_profile_errors'].append('Missing first name')
            if not last_name:
                context['update_profile_errors'].append('Missing last name')

            if '' not in (first_name, last_name):
                student.first_name = first_name
                student.last_name = last_name
                if password:
                    student.set_password(password)
                student.save()
                if request.user.id == student.id:
                    auth.login(request, student)
                context['update_profile_message'] = 'Profile updated.'
        else:
            raise Http404

    return render(request, 'dbmanager/view_profile.html', context)


@login_if_unauthenticated
def export_details(request, id, import_errors=None):
    export = get_object_or_404(DatabaseSnapshot, pk=id)
    if not export.student.id == request.user.id \
            and not request.user.is_superuser:
        raise Http404

    import_dbs = None
    if export.student.id == request.user.id:
        import_dbs = export.student.databases \
                .union(export.student.other_databases.all()) \
                .order_by('name')

    context = {
        'export': export,
        'import_dbs': import_dbs,
        'max_db_name_length': StudentDatabase.MAX_NAME_LENGTH - (len(export.student.username) + 1),
        'import_errors': import_errors
    }

    return render(request, 'dbmanager/export_details.html', context)


@login_if_unauthenticated
def download_export(request, id):
    # Better to let web server do this somehow!
    export = get_object_or_404(DatabaseSnapshot, pk=id)
    if not export.student.id == request.user.id \
            and not request.user.is_superuser:
        raise Http404

    if export.success:
        return FileResponse(open(export.get_path(), 'rb'),
                            as_attachment=True,
                            filename=export.get_export_filename(),
                            content_type='application/sql')
    else:
        return redirect('student_home')


@login_if_unauthenticated
def export_database(request, db_name):
    if request.method != 'POST':
        raise Http404
    database = get_object_or_404(StudentDatabase, name=db_name)
    student = get_object_or_404(Student, id=request.user.id)

    if not database.owner.pk == student.pk \
            and not database.other_students.filter(pk=student.pk).exists():
        raise Http404

    export = DatabaseSnapshot(student=student, database=database, course=database.course)
    export.initiate()

    return redirect('export_details', id=export.id)


@login_if_unauthenticated
def delete_export(request, id):
    export = get_object_or_404(DatabaseSnapshot, pk=id)
    if (not export.student.id == request.user.id
            and not request.user.is_superuser) \
            or request.method != 'POST':
        raise Http404

    db_name = export.database.name if export.database else None
    course = None
    if not db_name:
        course = export.course
    export.delete()

    if 'next' in request.POST:
        return HttpResponseRedirect(request.POST['next'])
    else:
        if db_name:
            return redirect('database_details', db_name=export.database.name)
        else:
            return redirect('student_course_home', course_handle=course.handle)


@login_if_unauthenticated
def delete_database(request, db_name):
    database = get_object_or_404(StudentDatabase, name=db_name)
    if not database.owner.id == request.user.id:
        raise Http404

    context = {
        'database': database,
    }

    if request.method == 'GET':
        return render(request, 'dbmanager/delete_database.html', context)
    elif request.method == 'POST':
        course = database.course
        database.delete()
        if 'next' in request.POST:
            return HttpResponseRedirect(request.POST['next'])
        else:
            return redirect('student_course_home', course_handle=course.handle)


@login_if_unauthenticated
def import_export(request, export_id):
    export = get_object_or_404(DatabaseSnapshot, pk=export_id)
    if (not export.student.id == request.user.id
            and not request.user.is_superuser) \
            or request.method != 'POST':
        raise Http404

    student = get_object_or_404(Student, id=request.user.id)

    if 'import_db' in request.POST:
        if request.POST['import_db'] == 'existing':
            db_id = request.POST.get('db_id', '')
            db = get_object_or_404(StudentDatabase, pk=db_id)
            # Do we have permission to write in this database?
            if db.can_write(student):
                dimport = DatabaseImport.from_export(export=export,
                                                     database=db,
                                                     student=student)
                dimport.initiate()

                return redirect('import_details', id=dimport.id)
        elif request.POST['import_db'] == 'new':
            new_db_name = request.POST.get('new_db_name', None)
            if not new_db_name:
                return export_details(request, id=export_id, import_errors=['Must specify new database name'])
            new_db_name = student.username + '_' + new_db_name
            if StudentDatabase.objects.filter(name=new_db_name).exists():
                return export_details(request, id=export_id,
                                      import_errors=['Database {} already exists'.format(new_db_name)])
            elif not StudentDatabase.is_valid_name(new_db_name):
                return export_details(request, id=export_id,
                                      import_errors=['Invalid database name {} (database names can be up to {} characters long and may be composed of only letters, digits, and underscores)'.format(new_db_name, StudentDatabase.MAX_NAME_LENGTH)])
            #new_db = student.create_database(new_db_name)
            new_db = StudentDatabase.create(student, export.course, new_db_name)
            dimport = DatabaseImport.from_export(export=export,
                                                 database=new_db,
                                                 student=student)
            dimport.initiate()

            return redirect('import_details', id=dimport.id)

    raise Http404


@login_if_unauthenticated
def import_details(request, id):
    dimport = get_object_or_404(DatabaseImport, pk=id)

    context = {
        'student': dimport.student,
        'database': dimport.database,
        'import': dimport,
    }

    return render(request, 'dbmanager/import_details.html', context)


@login_if_unauthenticated
def import_upload(request, course_handle):
    #if request.user.is_superuser:
    #    student = None
    #    databases = StudentDatabase.objects.order_by('owner__username', 'name')
    #else:
    student = get_object_or_404(Student, id=request.user.id)
    course = get_object_or_404(Course, handle=course_handle)
    databases = StudentDatabase.objects.filter(owner=student, course=course)

    context = {
        'student': student,
        'course': course,
        'databases': databases,
        'max_db_name_length': StudentDatabase.MAX_NAME_LENGTH - (len(student.username) + 1),
        'import_errors': [],
    }

    if request.method == 'POST':
        db_kind = request.POST.get('db_kind', None)
        if db_kind not in ('new', 'existing'):
            context['import_errors'].append('You must specify which database to import into')
        elif 'file' not in request.FILES:
            context['import_errors'].append('No file given')
        elif 'Content-Length' in request.headers \
                and int(request.headers['Content-Length']) > DatabaseImport.MAX_IMPORT_SIZE_BYTES:
            context['import_errors'].append('Upload too large; maximum allowed size is 100 MiB')
        else:
            # Get the database we're importing into
            db = None
            if db_kind == 'existing':
                db = get_object_or_404(StudentDatabase, name=request.POST.get('existing_db_name', None))
            elif 'new_db_name' in request.POST:
                db_name = student.username + '_' + request.POST.get('new_db_name').strip()
                db_q = StudentDatabase.objects.filter(name=db_name)
                if db_q.exists():
                    context['import_errors'].append('Database {} already exists'.format(db_name))
                elif not StudentDatabase.is_valid_name(db_name):
                    context['import_errors'].append('Invalid database name {} (database names can be up to {} characters long and may only be composed of letters, digits, and underscores)'.format(db_name, StudentDatabase.MAX_NAME_LENGTH))
                else:
                    db = StudentDatabase.create(student, course, db_name)

            if db is not None:
                f = request.FILES['file']
                dimport = DatabaseImport.from_upload(file=f,
                                                     student=student, database=db, course=course)
                dimport.initiate()
                return redirect('import_details', id=dimport.id)

    return render(request, 'dbmanager/import_upload.html', context)


@login_if_unauthenticated
def token_details(request, token_username):
    token = get_object_or_404(AccessToken, username=token_username)
    if request.user.id != token.database.owner.id:
        raise Http404

    context = {
        'token': token,
    }

    return render(request, 'dbmanager/token_details.html', context)


@login_if_unauthenticated
def alter_token(request, token_username):
    token = get_object_or_404(AccessToken, username=token_username)
    if request.user.id != token.database.owner.id:
        raise Http404

    if request.method == 'POST':
        action = request.POST.get('action', None)
        if action == 'set_permissions':
            perm = request.POST.get('permissions', None)
            if perm == 'ro':
                token.set_write_permission(False)
            elif perm == 'rw':
                token.set_write_permission(True)
            return redirect('token_details', token_username=token_username)
        elif action == 'cancel':
            token.delete()
            return redirect('database_details', db_name=token.database.name)

    raise Http404


@login_if_unauthenticated
def create_token(request, db_name):
    db = get_object_or_404(StudentDatabase, name=db_name)
    if request.user.id != db.owner.id:
        raise Http404

    if request.method == 'POST':
        token = db.create_token()
        return redirect('token_details', token_username=token.username)

    raise Http404
