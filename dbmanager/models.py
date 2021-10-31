# --- Important note ---
# In the current version of this code, students accounts become @'localhost' on the managed SQL server while access
# tokens and proxy users are @'%'. This is because of an error on my part: a previous version of the code had all users
# @'localhost', which worked fine until moving the database_course Django web app to a different server than the one the
# database was hosted on! Unfortunately I didn't discover this limitation until after all the students in the current
# semester (Fall 2021) had created their accounts and set passwords; I don't want to make them all reset their passwords
# and the MySQL user password hash seems to be salted with the host, preventing me from simply copying their users to
# @'%' ones server-side, so I am leaving the code in this current kludge-y state.
#
# What should probably be done ASAP (e.g., Fall 2022 *before* students set their passwords, or at least the next time
# this web app is deployed) is to replace all @'localhost' with @'%', or provide some mechanism for scoping the MySQL
# user accounts to the appropriate host. (If we continue to be happy having students ssh tunnel into the server for DB
# access, maybe it's OK for student accounts to remain @'localhost', but at a minimum the main database manager user and
# proxy users need to be more accessible to allow the web app to run on a separate [virtual] host.)

from django.db import models
from django.contrib.auth import models as auth_models
from django.db.models.signals import pre_delete, pre_save
from django.dispatch.dispatcher import receiver
from django.db.transaction import atomic
from django.utils import timezone
from course.models import Person, Student, Course
import mysql.connector.errorcode as errorcode
import mysql.connector as mysql
import uuid

_db_connection = None
_db_depth = 0


def get_db():
    import dbmanager.settings
    #from dbmanager.settings import CONTROLLED_DB_PARAMS as DB_PARAMS
    db_host = dbmanager.settings.MANAGED_DB_HOST
    db_port = dbmanager.settings.MANAGED_DB_PORT
    admin_username = dbmanager.settings.MANAGED_DB_USER
    admin_password = dbmanager.settings.MANAGED_DB_PASSWORD

    class DBWrapper:
        def __enter__(self):
            global _db_depth
            global _db_connection

            if _db_connection is None:
                _db_connection = mysql.connect(host=db_host, port=db_port,
                                               user=admin_username, password=admin_password)
                _db_connection.start_transaction()
            elif not _db_connection.is_connected():
                _db_connection.reconnect(attempts=5, delay=3)
            _db_depth += 1

            return _db_connection

        def __exit__(self, type, value, traceback):
            global _db_connection
            global _db_depth

            _db_depth -= 1
            if _db_depth == 0:
                _db_connection.commit()
                #_db_connection.close()
                #_db_connection = None

    return DBWrapper()


def flush_privileges():
    with get_db() as db:
        c = db.cursor()
        c.execute('FLUSH PRIVILEGES')
        db.commit()

#
# # Create your models here.
# class Student(auth_models.User):
#     MAX_USERNAME_LENGTH = 20
#     student_id = models.CharField(max_length=8, default='', null=False, blank=True)
#     password_clear = models.CharField(max_length=32, null=True, default=None)
#
#     @staticmethod
#     def create(username, password, **kwargs):
#         import mysql.connector.errors
#         s = Student(username=username, **kwargs)
#         with get_db() as db:
#             cursor = db.cursor()
#             cursor.execute("""CREATE USER %s@'%' IDENTIFIED BY %s""",
#                            (username, password))
#         s.set_password(password)
#         s.save()
#         return s
#
#     def get_full_name(self):
#         return "{} {}".format(self.first_name, self.last_name)
#
#     def set_password(self, raw_password):
#         self.password_clear = raw_password
#         self.save()
#
#         with get_db() as db:
#             cursor = db.cursor()
#             cursor.execute("""ALTER USER %s@'%' IDENTIFIED BY %s""",
#                            (self.username, raw_password,))
#
#         return super().set_password(raw_password)
#


def _random_password():
    import random
    import string
    return ''.join([random.choice(string.ascii_letters + string.digits) for _ in range(64)])


class DatabaseProxyUser(models.Model):
    #student = models.ForeignKey(to=Student, null=False, on_delete=models.CASCADE, unique=True)
    student = models.OneToOneField(to=Student, null=False, on_delete=models.CASCADE, related_name='+')
    username = models.CharField(max_length=30, null=False, blank=False)
    password = models.CharField(max_length=64, null=False, blank=False, default=_random_password)

    def __str__(self):
        return f'{self.username} (proxy for {self.student.username})'

    @staticmethod
    def proxy_for(student):
        maybe_proxy = DatabaseProxyUser.objects.filter(student=student)
        if maybe_proxy.exists():
            return maybe_proxy.get()

        proxy = DatabaseProxyUser(
            student=student,
            username=f'proxy/{student.username}'
        )

        with get_db() as db:
            cursor = db.cursor()

            cursor.execute('''CREATE USER IF NOT EXISTS %s@'%' ''',
                           (proxy.username,))
            cursor.execute('''ALTER USER %s@'%' IDENTIFIED BY %s''',
                           (proxy.username, proxy.password,))

            for sdb in student.databases.all():
                cursor.execute(f'''GRANT ALL ON {sdb.name}.* TO %s@'%' ''',
                               (proxy.username,))

            for sdba in StudentDatabaseAccess.objects.filter(student=student):
                if sdba.write_permission:
                    cursor.execute(f'''GRANT ALL ON {sdba.database.name}.* TO %s@'%' ''',
                                   (proxy.username,))
                else:
                    cursor.execute(f'''GRANT SELECT ON {sdba.database.name}.* TO %s@'%' ''',
                                   (proxy.username,))

            db.commit()

        proxy.save()
        return proxy


class DatabaseDeletedError(Exception):
    def __init__(self, database, *args):
        super().__init__(*args)
        self.database = database


class StudentDatabase(models.Model):
    MAX_NAME_LENGTH = 64
    name = models.CharField(max_length=MAX_NAME_LENGTH, unique=True)    # note: schema name at most 64 characters (must include username!)
    course = models.ForeignKey(to=Course, null=False, on_delete=models.CASCADE)
    owner = models.ForeignKey(to=Student, related_name='databases', on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    other_students = models.ManyToManyField(to=Student, through='StudentDatabaseAccess', related_name='other_databases')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_table_names = None
        self._saved_is_deleted = None

    @staticmethod
    def create(student, course, db_name):
        db_query = StudentDatabase.objects.filter(name=db_name)
        db = db_query.get() if db_query.exists() else None
        if db and db.owner == student:
            return None
        elif db:
            raise ValueError("DB already exists and is owned by someone else")
        else:
            with get_db() as db:
                cursor = db.cursor()
                cursor.execute("""CREATE DATABASE IF NOT EXISTS {}""".format(db_name))
                cursor.execute(f"""GRANT ALL ON {db_name}.* TO %s@'localhost'""",
                               (student.username,))
                proxy = DatabaseProxyUser.proxy_for(student)
                cursor.execute(f"""GRANT ALL ON {db_name}.* TO %s@'localhost'""",
                               (proxy.username,))

            flush_privileges()

            db = StudentDatabase(name=db_name,
                                 course=course,
                                 owner=student)
            db.save()
            return db

    @staticmethod
    def is_valid_name(db_name):
        import re
        valid_name_pattern = re.compile(r'^[a-zA-Z_][0-9a-zA-Z_]*$')
        return valid_name_pattern.match(db_name) and len(db_name) <= StudentDatabase.MAX_NAME_LENGTH

    def delete(self, *args, **kwargs):
        with get_db() as db:
            cursor = db.cursor()
            cursor.execute("""DROP DATABASE IF EXISTS {}""".format(self.name))

        super().delete(*args, **kwargs)

    def get_shares(self):
        return [{'student': share.student, 'write_permission': share.write_permission}
                for share in self.shared_with_students.all()]

    def get_table_names(self):
        if self._saved_table_names:
            return self._saved_table_names
        with get_db() as db:
            cursor = db.cursor()
            try:
                cursor.execute("""USE {}""".format(self.name))
                cursor.execute("""SHOW TABLES""")
                self._saved_table_names = [row[0] for row in cursor]
            except mysql.ProgrammingError as e:
                # Check whether this database even exists
                if self.is_deleted():
                    self._saved_table_names = ['[database deleted from outside web app]']
                    raise DatabaseDeletedError(self)
                else:
                    print(e)
                    self._saved_table_names = ['?']

        return self._saved_table_names

    def get_table_names_safe(self):
        try:
            return self.get_table_names()
        except DatabaseDeletedError:
            return self.get_table_names()

    def is_deleted(self):
        if self._saved_is_deleted is not None:
            return self._saved_is_deleted
        with get_db() as db:
            cursor = db.cursor()
            cursor.execute("""SELECT COUNT(*) FROM information_schema.SCHEMATA WHERE SCHEMA_NAME = %s""",
                           (self.name,))
            for (count,) in cursor:
                self._saved_is_deleted = count == 0
                return self._saved_is_deleted

    def share_with(self, student, write_permission=False):
        proxy = DatabaseProxyUser.proxy_for(student)
        sdba_query = StudentDatabaseAccess.objects.filter(database=self, student=student)
        if sdba_query.exists():
            sdba = sdba_query.get()
            if sdba.write_permission != write_permission:
                sdba.write_permission = write_permission

                with get_db() as db:
                    cursor = db.cursor()
                    if write_permission:
                        cursor.execute("""GRANT ALL ON {}.* TO %s@'localhost'""".format(self.name),
                                       (student.username,))
                        cursor.execute("""GRANT ALL ON {}.* TO %s@'%'""".format(self.name),
                                       (proxy.username,))
                    else:
                        try:
                            cursor.execute("""REVOKE ALL ON {}.* FROM %s@'localhost'""".format(self.name),
                                           (student.username,))
                            cursor.execute("""REVOKE ALL ON {}.* FROM %s@'%'""".format(self.name),
                                           (proxy.username,))
                        except mysql.errors.ProgrammingError as e:
                            if e.errno != errorcode.ER_NONEXISTING_GRANT:
                                raise e
                        cursor.execute("GRANT SELECT ON {}.* TO %s@'localhost'".format(self.name),
                                       (student.username,))
                        cursor.execute("GRANT SELECT ON {}.* TO %s@'%'".format(self.name),
                                       (proxy.username,))

                sdba.save()
        else:
            sdba = StudentDatabaseAccess(database=self, student=student, write_permission=write_permission)
            with get_db() as db:
                cursor = db.cursor()
                cursor.execute("GRANT {} on {}.* TO %s@'localhost'".format("ALL" if write_permission else "SELECT", self.name),
                               (student.username,))
                cursor.execute("GRANT {} on {}.* TO %s@'%'".format("ALL" if write_permission else "SELECT", self.name),
                               (proxy.username,))

            sdba.save()

    def unshare_with(self, student):
        proxy = DatabaseProxyUser.proxy_for(student)
        sdba_query = StudentDatabaseAccess.objects.filter(database=self, student=student)
        if sdba_query.exists():
            with get_db() as db:
                cursor = db.cursor()
                try:
                    cursor.execute("""REVOKE ALL ON {}.* FROM %s@'localhost'""".format(self.name),
                                   (student.username,))
                    cursor.execute("""REVOKE ALL ON {}.* FROM %s@'%'""".format(self.name),
                                   (proxy.username,))
                except mysql.errors.ProgrammingError as e:
                    if e.errno != errorcode.ER_NONEXISTING_GRANT:
                        raise e
            sdba_query.delete()

    def export_to_file(self, sql_path, stdout_path, stderr_path, db_params=None, timeout=60):
        import subprocess
        #from cmpt307_dbmanager.settings import CONTROLLED_DB_PARAMS as DB_PARAMS
        import dbmanager.settings as settings

        if db_params is None:
            db_params = {
                'username': settings.MANAGED_DB_USER,
                'password': settings.MANAGED_DB_PASSWORD,
                'host': settings.MANAGED_DB_HOST,
                'port': settings.MANAGED_DB_PORT,
            }
        username, password = db_params['username'], db_params['password']
        host, port = db_params['host'], db_params['port']

        args = ('mysqldump',
                '-u', username,
                '--password={}'.format(password),
                '-h', host,
                '-P', str(port),
                '-r', sql_path,
                self.name)

        with open(stdout_path, 'w') as stdout, \
                open(stderr_path, 'w') as stderr, \
                subprocess.Popen(args, stdout=stdout, stderr=stderr) as process:
            try:
                process.wait(timeout=timeout)
                return process.returncode == 0
            except subprocess.TimeoutExpired:
                process.kill()
                return False

    def import_from_file(self, sql_path, stdout_path, stderr_path, db_params=None, timeout=60):
        import subprocess
        #from cmpt307_dbmanager.settings import CONTROLLED_DB_PARAMS as DB_PARAMS
        import dbmanager.settings as settings

        if db_params is None:
            db_params = {
                'username': settings.MANAGED_DB_USER,
                'password': settings.MANAGED_DB_PASSWORD,
                'host': settings.MANAGED_DB_HOST,
                'port': settings.MANAGED_DB_PORT,
            }
        username, password = db_params['username'], db_params['password']
        host, port = db_params['host'], db_params['port']

        args = ('mysql',
                '-u', username,
                '--password={}'.format(password),
                '-h', host,
                '-P', str(port),
                self.name)

        with open(sql_path, 'r') as stdin, \
                open(stdout_path, 'w') as stdout, \
                open(stderr_path, 'w') as stderr, \
                subprocess.Popen(args, stdin=stdin, stdout=stdout, stderr=stderr) as process:
            try:
                process.wait(timeout=timeout)
                return process.returncode == 0
            except subprocess.TimeoutExpired:
                process.kill()
                return False

    def can_read(self, student):
        return student == self.owner \
                or self.other_students.filter(student=student).exists()

    def can_write(self, student):
        return student == self.owner \
                or self.shared_with_students.filter(student=student, write_permission=True).exists()

    def create_token(self, write_permission=False):
        token = AccessToken.create_token(database=self, write_permission=write_permission)
        return token


class StudentDatabaseAccess(models.Model):
    student = models.ForeignKey(to=Student, on_delete=models.CASCADE, related_name='shared_databases')
    database = models.ForeignKey(to=StudentDatabase, on_delete=models.CASCADE, related_name='shared_with_students')
    write_permission = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('student', 'database'), name='unique_student_database')
        ]


class DatabaseSnapshot(models.Model):
    TABLE_NAME_SEPARATOR = '|'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    request_time = models.DateTimeField(auto_now_add=False, null=True, default=None)
    completion_time = models.DateTimeField(null=True, default=None)
    student = models.ForeignKey(to=Student, on_delete=models.CASCADE, null=False, related_name='exports')
    database = models.ForeignKey(to=StudentDatabase, null=True, on_delete=models.SET_NULL, related_name='exports')
    course = models.ForeignKey(to=Course, null=False, on_delete=models.CASCADE, related_name='+')
    database_name = models.CharField(max_length=StudentDatabase.MAX_NAME_LENGTH, null=False, default='')
    table_names = models.TextField(null=False, default='')
    success = models.BooleanField(null=True, default=None)
    stdout = models.TextField(default='')
    stderr = models.TextField(default='')

    class Meta:
        ordering = ('request_time',)

    def __init__(self, *args, **kwargs):
        if 'database_name' not in kwargs and 'database' in kwargs:
            kwargs['database_name'] = kwargs['database'].name
        super().__init__(*args, **kwargs)

    def __str__(self):
        return f'Snapshot of {self.database_name} requested {self.request_time} by {self.student.name}'

    def is_active(self):
        return self.success is None

    def get_file_name(self):
        return str(self.id)

    def get_path(self):
        import os.path
        #import cmpt307_dbmanager.settings
        #return os.path.join(cmpt307_dbmanager.settings.PORT_DIR, self.get_file_name())
        import dbmanager.settings
        return str(dbmanager.settings.SNAPSHOT_DIR / self.get_file_name())

    def get_export_size(self):
        if not self.is_active() and self.success:
            import os
            import os.path
            try:
                return os.path.getsize(self.get_path())
            except OSError:
                return None

    def get_export_filename(self):
        db_name = self.database.name if self.database is not None else self.database_name
        return '{}_{}.sql'.format(db_name,
                                  timezone.localtime(self.request_time).strftime('%Y-%m-%d_%H:%M:%S'))

    def get_table_names(self):
        if not self.table_names:
            return []
        else:
            return self.table_names.split(DatabaseSnapshot.TABLE_NAME_SEPARATOR)

    def _get_stdout_path(self):
        return self.get_path() + '.stdout'

    def _get_stderr_path(self):
        return self.get_path() + '.stderr'

    def initiate(self):
        if self.request_time is not None:
            return
        import datetime
        self.request_time = timezone.now()
        self.completion_time = None
        self.table_names = DatabaseSnapshot.TABLE_NAME_SEPARATOR.join(self.database.get_table_names())
        self.save()

        import threading

        stdout_path, stderr_path = self._get_stdout_path(), self._get_stderr_path()

        def perform_export():
            stdout_path, stderr_path = self._get_stdout_path(), self._get_stderr_path()
            self.success = self.database.export_to_file(sql_path=self.get_path(),
                                                        stdout_path=stdout_path, stderr_path=stderr_path)
            self.completion_time = datetime.datetime.utcnow()

            with open(stdout_path, 'r') as stdout_in, \
                    open(stderr_path, 'r') as stderr_in:
                self.stdout = stdout_in.read()
                self.stderr = stderr_in.read()

            import os
            os.remove(stdout_path)
            os.remove(stderr_path)

            self.save()

        thread = threading.Thread(target=perform_export, name='export-{}/{}'.format(self.student.username, str(self.id)))
        thread.start()


@receiver(pre_delete, sender=DatabaseSnapshot)
def _database_export_pre_delete(sender, instance, **kwargs):
    try:
        import os
        import os.path
        path = instance.get_path()
        if os.path.exists(path):
            os.remove(instance.get_path())
    except FileNotFoundError:
        pass


class DatabaseImport(models.Model):
    MAX_IMPORT_SIZE_BYTES = 100 * 2**20   # 100 MiB

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    request_time = models.DateTimeField(auto_now_add=False, null=True, default=None)
    completion_time = models.DateTimeField(null=True, default=None)
    student = models.ForeignKey(to=Student, on_delete=models.CASCADE, null=False, related_name='imports')
    database = models.ForeignKey(to=StudentDatabase, null=True, on_delete=models.SET_NULL, related_name='imports')
    course = models.ForeignKey(to=Course, null=False, on_delete=models.CASCADE, related_name='+')
    source_export = models.ForeignKey(to=DatabaseSnapshot, on_delete=models.CASCADE, null=True, default=None)
    source_file = models.CharField(max_length=40, null=False, default='')
    success = models.BooleanField(null=True, default=None)
    stdout = models.TextField(default='')
    stderr = models.TextField(default='')

    def __str__(self):
        return f'Import into database {self.database.name} from {"snapshot" if self.source_export else "file"}'

    @staticmethod
    def from_export(export, *args, **kwargs):
        if export is None:
            raise ValueError('export is None')
        imp = DatabaseImport(course=export.course, *args, **kwargs)
        imp.source_export = export
        imp.source_file = export.get_file_name()
        return imp

    @staticmethod
    def from_upload(file=None, *args, **kwargs):
        if 'source_export' in kwargs:
            raise ValueError('source_export specified for import from upload')
        elif 'source_file' in kwargs:
            raise ValueError('source_file specified for import from upload')
        imp = DatabaseImport(*args, **kwargs)
        imp.source_export = None
        imp.source_file = str(imp.id)

        if file:
            with open(imp.get_path(), 'wb') as out_file:
                for chunk in file.chunks():
                    out_file.write(chunk)

        return imp

    def is_active(self):
        return self.success is None

    def get_path(self):
        import os.path
        #import cmpt307_dbmanager.settings
        #return os.path.join(cmpt307_dbmanager.settings.PORT_DIR, self.source_file)
        import dbmanager.settings
        return str(dbmanager.settings.SNAPSHOT_DIR / self.source_file)

    def get_import_size(self):
        import os.path
        try:
            return os.path.getsize(self.get_path())
        except OSError:
            return None

    def _get_stdout_path(self):
        return self.get_path() + '.stdout'

    def _get_stderr_path(self):
        return self.get_path() + '.stderr'

    def initiate(self):
        if self.request_time is not None:
            return
        self.request_time = timezone.now()
        self.completion_time = None
        self.save()

        proxy = DatabaseProxyUser.proxy_for(self.student)

        with get_db() as db:
            cursor = db.cursor()
            cursor.execute(f'''GRANT ALL ON {self.database.name}.* TO %s@'%' ''',
                           (proxy.username,))

        flush_privileges()

        import threading

        stdout_path, stderr_path = self._get_stdout_path(), self._get_stderr_path()

        def perform_import():
            stdout_path, stderr_path = self._get_stdout_path(), self._get_stderr_path()
            #from cmpt307_dbmanager.settings import CONTROLLED_DB_PARAMS as DB_PARAMS
            #db_params = dict(DB_PARAMS)
            import dbmanager.settings
            db_params = {
                'host': dbmanager.settings.MANAGED_DB_HOST,
                'port': dbmanager.settings.MANAGED_DB_PORT,
                'username': proxy.username,
                'password': proxy.password
            }

            self.success = self.database.import_from_file(sql_path=self.get_path(),
                                                          stdout_path=stdout_path, stderr_path=stderr_path,
                                                          db_params=db_params)
            self.completion_time = timezone.now()

            with open(stdout_path, 'r') as stdout_in, \
                    open(stderr_path, 'r') as stderr_in:
                self.stdout = stdout_in.read()
                self.stderr = stderr_in.read()

            import os
            os.remove(stdout_path)
            os.remove(stderr_path)

            self.save()

        thread = threading.Thread(target=perform_import, name='import-{}/{}'.format(self.student.username, str(self.id)))
        thread.start()


class ClassDatabase(models.Model):
    MAX_NAME_LENGTH = 64
    course = models.ForeignKey(to=Course, null=False, on_delete=models.CASCADE)
    name = models.CharField(max_length=MAX_NAME_LENGTH, unique=True)    # note: schema name at most 64 characters (must include username!)
    published = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.name} [{"published" if self.published else "unpublished"}]'

    @staticmethod
    def create(name, published=False, fail_on_exists=True, **kwargs):
        with get_db() as db:
            cursor = db.cursor()
            if fail_on_exists:
                cursor.execute("""SHOW DATABASES LIKE %s""", (name,))
                if len(cursor.fetchall()) > 0:
                    raise ValueError('Database already exists')
            cursor.execute("""CREATE DATABASE IF NOT EXISTS `{}`""".format(name))

            for superuser in auth_models.User.objects.filter(is_superuser=True):
                cursor.execute("""GRANT ALL ON `{}`.* TO %s@'%'""".format(name),
                               (superuser.username,))

            cdb = ClassDatabase(name=name, published=published, **kwargs)

            if published:
                cdb.publish()

            cdb.save()
            return cdb

    def publish(self):
        self.published = True
        with get_db() as db:
            cursor = db.cursor()
            for student in self.course.students.all():
                cursor.execute("""GRANT SELECT ON `{}`.* TO %s@'localhost'""".format(self.name),
                               (student.username,))
                proxy = DatabaseProxyUser.proxy_for(student)
        self.save()

    def unpublish(self):
        self.published = False
        with get_db() as db:
            cursor = db.cursor()
            for student in self.course.students.all():
                cursor.execute("""REVOKE SELECT ON `{}`.* FROM %s@'localhost'""".format(self.name),
                               (student.username,))
        self.save()


def _choose_access_token_username(num_digits=4):
    import random
    import string
    import math

    # If more than 10% of the possible tokens are taken, increase num_digits accordingly.
    # This will probably never happen (unlikely to have more than 6500 tokens!) but we might as well make it
    # robust, right?
    token_count = AccessToken.objects.count()
    if token_count * 10 > 16 ** num_digits:
        num_digits = int(math.ceil(math.log(token_count, 16))) + 1

    while True:
        username = 'token_' + ''.join([random.choice(string.hexdigits) for _ in range(num_digits)]).lower()
        if not AccessToken.objects.filter(username=username).exists():
            return username


def _choose_access_token_password():
    import random
    import string
    return ''.join([random.choice(string.ascii_letters + string.digits + '_') for _ in range(16)])


class AccessToken(models.Model):
    database = models.ForeignKey(to=StudentDatabase, on_delete=models.CASCADE, related_name='tokens', null=False)
    write_permission = models.BooleanField(default=False, null=False)
    username = models.CharField(max_length=64, null=False, default=_choose_access_token_username)
    password = models.CharField(max_length=64, null=False, default=_choose_access_token_password)

    def __str__(self):
        return f'Token {self.username} for {self.database.name}'

    @staticmethod
    def create_token(database, write_permission=False, **kwargs):
        token = AccessToken(database=database, write_permission=write_permission, **kwargs)
        with get_db() as db:
            cursor = db.cursor()
            cursor.execute('''CREATE USER %s@'%' IDENTIFIED BY %s''',
                           (token.username, token.password))
            cursor.execute('''GRANT {} ON `{}`.* TO %s@'%' '''.format(
                'ALL' if write_permission else 'SELECT', database.name
            ), (token.username,))
        token.save()
        return token

    def set_write_permission(self, write_permission):
        if write_permission == self.write_permission:
            return
        with get_db() as db:
            cursor = db.cursor()
            if write_permission:
                cursor.execute('''GRANT ALL ON `{}`.* TO %s@'%' '''.format(self.database.name),
                               (self.username,))
            else:
                cursor.execute('''REVOKE ALL ON `{}`.* FROM %s@'%' '''.format(self.database.name),
                               (self.username,))
                cursor.execute('''GRANT SELECT ON `{}`.* TO %s@'%' '''.format(self.database.name),
                               (self.username,))
        self.write_permission = write_permission
        self.save()


@receiver(pre_delete, sender=AccessToken)
def _access_token_pre_delete(sender, instance, **kwargs):
    with get_db() as db:
        cursor = db.cursor()
        try:
            cursor.execute('''DROP USER %s@'%' ''', (instance.username,))
        except mysql.ProgrammingError as e:
            print(e)


@Person.password_change_listener
def _on_password_change(person, new_password):
    with get_db() as db:
        cursor = db.cursor()
        cursor.execute('''CREATE USER IF NOT EXISTS %s@'localhost' ''', (person.username,))
        cursor.execute('''ALTER USER %s@'localhost' IDENTIFIED BY %s''',
                       (person.username, new_password,))
