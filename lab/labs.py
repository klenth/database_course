import string

from django.core.files import storage

from . import models, errors
from lab import settings

from threading import Thread
import mysql.connector
from mysql.connector import errors as mysql_errors
import uuid
import subprocess
import random
import csv
from django.shortcuts import reverse
from django.core.mail import EmailMessage

__DB_CONNECTION = None


class QueryResults:
    def __init__(self, column_names, rows, incomplete=False):
        self.column_names = column_names
        self.rows = rows
        self.incomplete = incomplete

    def _str(self, x):
        return str(x) if x is not None else ''

    def rows_match(self, other):
        if self is other:
            return True
        elif len(self.rows) != len(other.rows):
            return False
        elif len(self.rows) == 0:
            return True
        else:
            for i in range(len(self.rows)):
                if len(self.rows[i]) != len(other.rows[i]) or \
                        any([self._str(self.rows[i][j]) != self._str(other.rows[i][j]) for j in range(len(self.rows[i]))]):
                    return False
            return True

    def columns_match(self, other):
        if self is other:
            return True
        elif len(self.column_names) != len(other.column_names) or \
                any([self._str(self.column_names[i]) != self._str(other.column_names[i]) for i in range(len(self.column_names))]):
            return False
        return True

    @staticmethod
    def from_cursor(cursor, fetch_data=True):
        column_names = cursor.column_names

        if fetch_data:
            # Fetch up to LAB_MAX_QUERY rows
            # TODO: make this work with set()s returned from the cursor (and maybe other data types?)
            rows = cursor.fetchmany(size=settings.LAB_MAX_QUERY_ROWS)
            incomplete = cursor.fetchone() is not None
        else:
            rows = []
            incomplete = False

        # Discard any remaining results
        while True:
            if not cursor.fetchone():
                break

        return QueryResults(column_names, rows, incomplete)

    @staticmethod
    def from_csv(file):
        if isinstance(file, str):
            return QueryResults.from_csv(open(file, 'r', newline=''))

        try:
            reader = csv.reader(file)
            column_names = tuple(next(reader))
            rows = list(tuple(row) for row in reader)

            return QueryResults(column_names, rows)
        finally:
            file.close()

    def save_csv(self, out):
        if isinstance(out, str):
            self.save_csv(open(out, 'w'))

        try:
            writer = csv.writer(out)
            writer.writerow(self.column_names)
            for row in self.rows:
                writer.writerow(row)
        finally:
            out.close()

    def save_csv_filefield(self, field, *, name):
        class Empty:
            def read(self, *args, **kwargs):
                return None

        field.save(name=name, content=Empty())
        self.save_csv(field.open('w'))


def path_for_uploaded_file(filename):
    from django.core.files import storage
    store = storage.DefaultStorage()
    return str(settings.MEDIA_ROOT / store.path(filename))


def get_database_connection(**kwargs):
    global __DB_CONNECTION
    if __DB_CONNECTION:
        if not __DB_CONNECTION.is_connected():
            try:
                __DB_CONNECTION.reconnect(attempts=5, delay=3)
            except mysql_errors.ProgrammingError:
                __DB_CONNECTION = None
                return get_database_connection()

        return __DB_CONNECTION
    else:
        __DB_CONNECTION = mysql.connector.connect(user=settings.LAB_DB_USER,
                                                  password=settings.LAB_DB_PASSWORD,
                                                  host=settings.LAB_DB_HOST,
                                                  allow_local_infile=True,
                                                  **kwargs)
        return __DB_CONNECTION


def unique_database_name(prefix):
    return prefix + ''.join([random.choice(string.ascii_lowercase) for _ in range(16)])


def create_database(db_name, *, cursor, error_if_exists=True):
    try:
        if not error_if_exists:
            cursor.execute(f'CREATE DATABASE IF NOT EXISTS `{db_name}`')
        else:
            cursor.execute(f'CREATE DATABASE `{db_name}`')
    except mysql_errors.Error as e:
        raise errors.SqlError(e.msg)


def drop_database(db_name, *, cursor, error_if_not_exists=True):
    try:
        if not error_if_not_exists:
            cursor.execute(f'DROP DATABASE IF EXISTS `{db_name}`')
        else:
            cursor.execute(f'DROP DATABASE `{db_name}`')
    except mysql_errors.Error as e:
        raise errors.SqlError(e.msg)


def temporary_database(*, name=None, prefix=None, cursor, error_if_exists=True):
    class TempDatabase:
        def __init__(self, db_name):
            self.name = db_name

        def __enter__(self):
            create_database(name, cursor=cursor, error_if_exists=error_if_exists)
            return self

        def __exit__(self, type, value, traceback):
            drop_database(name, cursor=cursor, error_if_not_exists=False)

    if (name and prefix) or (not name and not prefix):
        raise RuntimeError('Must specify exactly one of name and prefix')
    name = name or unique_database_name(prefix)

    return TempDatabase(name)


def load_schema(schema, *, db_name):
    import sys
    if not schema:
        return

    #with open(path_for_uploaded_file(schema.file.name), 'rb') as schema_in:
    with schema.file.open('rb') as schema_in:
        completed_process = subprocess.run(
            (settings.MYSQL_EXECUTABLE,
             '-u', settings.LAB_DB_USER,
             f'--password={settings.LAB_DB_PASSWORD}',
             '-h', settings.LAB_DB_HOST,
             '-P', str(settings.LAB_DB_PORT),
             db_name
             ),
            stdin=schema_in,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE
        )

    if completed_process and completed_process.returncode != 0:
        print(f'Schema load process ended with return code {completed_process.returncode}', file=sys.stderr)
        print('=== stderr output ===')
        print(completed_process.stderr.decode('utf-8'), file=sys.stderr)
        print('=====================')
        raise errors.SqlError(f'Schema load process ended with return code {completed_process.returncode}')


def load_test_case_data(test_case, *, cursor):
    cursor.execute('SET FOREIGN_KEY_CHECKS=0')
    for mapping in test_case.table_data_set.all():
        filename = path_for_uploaded_file(mapping.table_data.data_file.name)
        cursor.execute(f'''
        LOAD DATA LOCAL
        INFILE %s
        INTO TABLE `{mapping.table_name}`
        FIELDS TERMINATED BY ','
            OPTIONALLY SEPARATED BY '"'
        ''', (filename,))

    cursor.execute('SET FOREIGN_KEY_CHECKS=1')


def compute_results(problem):
    with get_database_connection() as conn:
        c = conn.cursor()
        for test_case in problem.test_cases.all():
            if test_case.result_data_file:
                # We already have the results for this test case
                continue

            results = None
            fetch_data = (test_case.type == models.ProblemTestCase.TEST_CASE_TYPE_TABLE_DATA)

            with temporary_database(prefix='instr_run_', cursor=c) as db:
                conn.database = db.name
                try:
                    load_schema(test_case.problem.schema, db_name=db.name)
                    load_test_case_data(test_case, cursor=c)
                    conn.commit()

                    for result in c.execute(problem.solution, multi=True):
                        if result.with_rows:
                            results = QueryResults.from_cursor(result, fetch_data=fetch_data)
                    conn.commit()

                    if problem.after_code:
                        for result in c.execute(problem.after_code, multi=True):
                            if result.with_rows:
                                results = QueryResults.from_cursor(result, fetch_data=fetch_data)
                    conn.commit()

                    if results is None:
                        raise errors.ProblemError('No results from instructor query')
                    elif results.incomplete:
                        raise errors.ProblemError(f'Instructor query resulted in too many rows (more than {settings.LAB_MAX_QUERY_ROWS})')
                except mysql_errors.Error as e:
                    raise errors.ProblemError(e.msg)

            results.save_csv_filefield(test_case.result_data_file, name=str(uuid.uuid1()))
            test_case.save()


def score(attempt):
    return sum(score_test_case(attempt, test_case) for test_case in attempt.problem.test_cases.all())


def score_test_case(attempt, test_case):
    if not test_case.result_data_file:
        raise errors.ProblemError

    fetch_data = (test_case.type == models.ProblemTestCase.TEST_CASE_TYPE_TABLE_DATA)
    instr_results, student_results = None, None
    with get_database_connection() as conn:
        c = conn.cursor()
        with temporary_database(prefix='student_run_', cursor=c) as db:
            conn.database = db.name
            try:
                load_schema(test_case.problem.schema, db_name=db.name)
                load_test_case_data(test_case, cursor=c)
                conn.commit()
            except mysql_errors.Error as e:
                raise errors.ProblemError(e.msg)

            try:
                for result in c.execute(attempt.text, multi=True):
                    if result.with_rows:
                        student_results = QueryResults.from_cursor(result, fetch_data=fetch_data)
                conn.commit()

                if test_case.problem.after_code:
                    for result in c.execute(test_case.problem.after_code, multi=True):
                        if result.with_rows:
                            student_results = QueryResults.from_cursor(result, fetch_data=fetch_data)
                conn.commit()

                if student_results is None:
                    raise errors.StudentCodeError('No results from student query')
                elif student_results.incomplete:
                    raise errors.StudentCodeError(f'Student query resulted in too many rows (more than {settings.LAB_MAX_QUERY_ROWS})')
            except mysql_errors.Error as e:
                raise errors.StudentCodeError(e.msg)

    instr_results = QueryResults.from_csv(test_case.result_data_file.open('r'))

    if test_case.type == models.ProblemTestCase.TEST_CASE_TYPE_TABLE_DATA:
        test_case_score = test_case.points if student_results.rows_match(instr_results) else 0
    elif test_case.type == models.ProblemTestCase.TEST_CASE_TYPE_COLUMN_NAMES:
        test_case_score = test_case.points if student_results.columns_match(instr_results) else 0
    else:
        raise errors.ProblemError(f'Don\'t know how to handle test case type: {test_case.type}')

    ar = models.AttemptResults(attempt=attempt, test_case=test_case, score=test_case_score)
    student_results.save_csv_filefield(ar.data_file, name=str(uuid.uuid1()))

    ar.save()

    return test_case_score


def validate_schema(problem_schema):
    def work():
        with get_database_connection() as conn:
            c = conn.cursor()
            with temporary_database(prefix='schema_validate_', cursor=c) as db:
                # Execute mysql client on schema file
                completed_process = None
                try:
                    load_schema(problem_schema, db_name=db.name)
                    conn.database = db.name
                    c.execute('SHOW TABLES')
                    table_names = [row[0] for row in c]
                    table_names.sort()
                    schema_valid = True

                    problem_schema.status = 'V'
                    problem_schema.set_table_names(table_names)
                    problem_schema.save()
                except errors.SqlError:
                    problem_schema.status = 'I'
                    problem_schema.set_table_names(())
                    problem_schema.save()

    thread = Thread(name=f"schema_validate_{problem_schema.id}", target=work)
    thread.start()


def student_request_help(*, student, problem, message=None, student_email=None):
    from database_course.settings import SYSTEM_EMAIL
    from lab.models import ProblemAttempt

    attempts = ProblemAttempt.objects.filter(student=student, problem=problem)
    attempt = attempts.last() if attempts else None
    lab = problem.lab()
    course = lab.course
    instructor = course.instructor

    url = get_help_url(student=student, problem=problem, attempt=attempt, by_uuid=True)

    subject = f'{course.title}: Requesting help on {problem.title} ({student.name})'
    body = f'''{student.name} is requesting help on {problem.title} ({lab.title}).

Link:
    {url}

Message:
------
{message}
'''
    email = EmailMessage(
        subject=subject,
        body=body,
        from_email=SYSTEM_EMAIL,
        to=(instructor.email,),
        cc=(student_email,),
        headers={
            'Content-Type': 'text/plain; charset="UTF-8"',
        }
    )

    email.send(fail_silently=True)


def get_help_url(*, student, problem, attempt=None, by_uuid=False):
    from database_course.settings import SITE_BASE_URL

    args = {
        'problem_id': problem.id
    }

    if by_uuid:
        args['as_uuid'] = student.uuid
    else:
        args['as_username'] = student.username

    if attempt:
        args['attempt_id'] = attempt.id

    if by_uuid and attempt:
        help_url = reverse('as_uuid_student_view_problem_attempt', kwargs=args)
    elif by_uuid:
        help_url = reverse('as_uuid_student_view_problem', kwargs=args)
    elif attempt:
        help_url = reverse('as_student_view_problem_attempt', kwargs=args)
    else:
        help_url = reverse('as_student_view_problem', kwargs=args)

    return SITE_BASE_URL + help_url
