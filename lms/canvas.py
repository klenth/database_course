import requests
from django.utils.text import slugify
from lms import canvas_api_token as credentials
from .models import *
import re
import logging
import threading

_REQUEST_METHODS = {
    'get': requests.get,
    'post': requests.post,
    'put': requests.put,
}


def canvas_request(*, relative_url=None, absolute_url=None, data=None, method='get'):
    if relative_url is None and absolute_url is not None:
        url = absolute_url
    elif relative_url is not None and absolute_url is None:
        url = f'{credentials.base_url}/{relative_url}'
    else:
        raise ValueError('Must specify exactly one of relative_url and absolute_url')

    method = method.lower()
    if method not in _REQUEST_METHODS.keys():
        raise ValueError(f'Method must be one of {"/".join(_REQUEST_METHODS.keys())}')

    request_method = _REQUEST_METHODS[method]

    response = request_method(
        url=url,
        headers={'Authorization': f'Bearer {credentials.token}'},
        data=data,
    )

    response.raise_for_status()

    return response


def canvas_paginated_request(rel_url, data=None):
    results = []

    response = canvas_request(relative_url=rel_url, data=data)

    while True:
        results += response.json()

        if not (response.links and 'next' in response.links):
            break

        next_url = response.links['next']['url']
        response = canvas_request(absolute_url=next_url, data=data)

    return results


def download_courses():
    def term_of(course_data):
        if 'term' in course_data and 'name' in course_data['term']:
            return course_data['term']['name']
        else:
            return None

    course_data = canvas_paginated_request('courses?enrollment_type=teacher&include[]=term&include[]=total_students')
    courses = [
        {
            'canvas_id': str(course['id']),
            'title': course['name'],
            'handle': slugify(course['course_code']),
            'total_students': course['total_students'],
            'term': term_of(course),
        }
        for course in course_data
    ]

    term_pattern = re.compile(r'^(.*) ([0-9]{4})$')

    def term_key(term_name):
        if m := term_pattern.match(term_name):
            return -int(m.group(2)), m.group(1)
        else:
            return -9999, term_name

    courses.sort(key=lambda c: (term_key(c['term']), c['handle']))

    return courses


def download_assignments_for_course(canvas_course):
    logging.info(f'Downloading assignments for {canvas_course.course.title}')

    assignment_data = canvas_paginated_request(f'courses/{canvas_course.canvas_id}/assignments')
    assignments = [
        {
            'canvas_id': str(assignment['id']),
            'title': assignment['name'],
            'url': assignment['html_url'],
            'group_id': assignment['assignment_group_id'],
            'position_within_group': assignment['position'],
            'points_possible': assignment['points_possible'],
        }
        for assignment in assignment_data
    ]

    preexisting_canvas_ids = set()
    for preexisting_assignment in CanvasAssignment.objects.filter(lab__course__id=canvas_course.course.id):
        preexisting_canvas_ids.add(str(preexisting_assignment.canvas_id))

    assignments = list(filter(lambda a: a['canvas_id'] not in preexisting_canvas_ids, assignments))
    assignments.sort(key=lambda a: (a['group_id'], a['position_within_group']))

    return assignments


def update_enrollment(canvas_course):
    logging.info(f'Updating enrollment for {canvas_course.course.title}')
    student_data = canvas_paginated_request(f'courses/{canvas_course.canvas_id}/users?enrollment_type[]=student')

    known_students = {
        student.canvas_id: student
        for student in CanvasStudent.objects.all()
    }

    # To help us find a unique username in the case of clashes
    existing_usernames = set(user.username for user in auth_models.User.objects.all())
    # Look up students by email to see if we already have them in the database
    email_map = {
        student.email: student
        for student in Student.objects.all()
    }
    # IDs of students already enrolled in the course
    existing_enrollments = set(student.uuid for student in canvas_course.course.students.all())

    for student in student_data:
        canvas_id = str(student['id'])
        name, sortable_name = student['name'], student['sortable_name']
        login_id = student.get('login_id', None)
        email = student.get('email', None)

        if not login_id and email:
            login_id = email[:email.find('@')]
        elif not login_id:
            login_id = slugify(name)

        login_id = unique_username(login_id, existing=existing_usernames)

        # Three possibilities:
        #   - This is a totally new student (no existing Student object, as determined by email)
        #   - This student already exists in the Student table, but we don't have a Canvas record for them yet
        #   - This student already exists in both Student and in CanvasStudent

        student = None
        if canvas_id not in known_students and email not in email_map.keys():
            # Totally new student
            logging.info(f'\t→ Adding new Student and CanvasStudent {name} ({canvas_id}) / {login_id}')
            new_student = Student(name=name, sortable_name=sortable_name, username=login_id, email=email)
            new_student.save()
            student = new_student

        elif canvas_id not in known_students:
            # Student object exists but not CanvasStudent
            student = email_map[email]
            new_canvas_student = CanvasStudent(student=student, canvas_id=canvas_id)
            new_canvas_student.save()

        else:
            # Student already exists in both Student and CanvasStudent - nothing to do
            student = email_map[email]

        # If there isn't an enrollment, create one
        if student.uuid not in existing_enrollments:
            enrollment = Enrollment(
                student=student,
                course=canvas_course.course,
            )
            enrollment.save()


def assign_grade(*, canvas_student, canvas_assignment, grade, comment=None, canvas_course=None):
    if canvas_course is None:
        canvas_course = canvas_assignment.lab.course.canvas_course
        if canvas_course is None:
            raise ValueError('Assignment does not belong to a Canvas course')

    grade_data = {
        'submission[posted_grade]': str(grade),
    }

    if comment:
        grade_data['comment[text_comment]'] = comment

    canvas_request(
        relative_url=f'courses/{canvas_course.canvas_id}/assignments/{canvas_assignment.canvas_id}/submissions/{canvas_student.canvas_id}',
        data=grade_data,
        method='put',
    )


def update_grade_if_higher(*, canvas_student, canvas_assignment, grade, comment=None, canvas_course=None):
    canvas_course = canvas_course or canvas_assignment.lab.course.canvas_course
    if canvas_course is None:
        raise ValueError('Assignment does not belong to a Canvas course')

    # Download current grade
    response = canvas_request(
        relative_url=f'courses/{canvas_course.canvas_id}/students/submissions?student_ids[]={canvas_student.canvas_id}&assignment_ids[]={canvas_assignment.canvas_id}',
    )

    # The above returns a list of submissions. Under the assumption that the Canvas assignment does not actually take
    # submissions, I *think* we will only ever get exactly one submission result (whose score might be null/None if it
    # has not yet been graded).

    current_grade = None
    submissions = response.json()

    if len(submissions) > 1:
        logging.warning(f'Student {canvas_student.student.name} has multiple submissions for assignment {canvas_assignment.lab.title}; grade may be overwritten!')
    for submission in response.json():
        raw_score = submission['score']
        current_grade = None if raw_score is None else float(raw_score)

    # If it has not yet been graded or the new grade is higher, assign the new grade
    if current_grade is None or current_grade < grade:
        assign_grade(canvas_student=canvas_student, canvas_assignment=canvas_assignment, canvas_course=canvas_course,
                     grade=grade, comment=comment)
    else:
        logging.info(f'Not updating {canvas_student.student.name}\'s grade for {canvas_assignment.lab.title} to {grade} because the existing grade is higher: {current_grade}')


def update_grades_if_higher(*, canvas_assignment, student_grades, canvas_course=None):
    '''student_grades: dictionary where keys are student Canvas IDs and values are dictionaries:
        {
            'score': number,
            'comment': string [optional]
        }'''
    canvas_course = canvas_course or canvas_assignment.lab.course.canvas_course
    if canvas_course is None:
        raise ValueError('Assignment does not belong to a Canvas course')

    # Download current grades
    submissions = canvas_paginated_request(
        rel_url=f'courses/{canvas_course.canvas_id}/students/submissions?student_ids[]=all&assignment_ids[]={canvas_assignment.canvas_id}',
    )

    # Filter out any grades that are higher on Canvas
    grades_to_update = student_grades
    for submission in submissions:
        user_id = str(submission['user_id'])
        if user_id in student_grades:
            present_grade = submission['score']
            if present_grade is not None and grades_to_update[user_id]['score'] <= present_grade:
                del grades_to_update[user_id]

    if not grades_to_update:
        logging.info(f'In response to request to update grades, not updating anything because all grades in Canvas are higher')
        return
    else:
        logging.info(f'Updating grades for {len(grades_to_update)} students')

    data = {}
    for user_id in grades_to_update:
        data[f'grade_data[{user_id}][posted_grade]'] = grades_to_update[user_id]['score']
        if 'comment' in grades_to_update[user_id]:
            data[f'grade_data[{user_id}][text_comment]'] = grades_to_update[user_id]['comment']

    print(repr(data))
    canvas_request(
        relative_url=f'courses/{canvas_course.canvas_id}/assignments/{canvas_assignment.canvas_id}/submissions/update_grades',
        data=data,
        method='post'
    )


_pending_grade_update_cv = threading.Condition()


def submit_grade_update_task(*, canvas_student, canvas_assignment):
    global _grade_update_thread
    global _pending_grade_update_cv

    with _pending_grade_update_cv:
        if not PendingCanvasGradeUpdate.objects.filter(canvas_student=canvas_student, canvas_assignment=canvas_assignment).exists():
            update = PendingCanvasGradeUpdate(canvas_student=canvas_student, canvas_assignment=canvas_assignment)
            update.save()
        _pending_grade_update_cv.notify()


def _run_grade_updates():
    global _pending_grade_update_cv

    def pending_updates_query():
        return PendingCanvasGradeUpdate.objects.filter(status=PendingCanvasGradeUpdate.STATUS_UNATTEMPTED)

    while True:
        pending_updates_q = None

        with _pending_grade_update_cv:
            while True:
                pending_updates_q = pending_updates_query()
                if pending_updates_q.exists():
                    break
                _pending_grade_update_cv.wait()

        logging.info(f'Grade update thread awoken with {pending_updates_q.count()} updates to commit')
        for pending_update in list(pending_updates_q):
            c_student, c_assignment = pending_update.canvas_student, pending_update.canvas_assignment
            grade = c_student.student.score_on_lab(c_assignment.lab)
            try:
                update_grade_if_higher(canvas_student=c_student, canvas_assignment=c_assignment, grade=grade)
                pending_update.delete()
            except requests.HTTPError as e:
                logging.error(f'Unable to update grade for {c_student.student} on {c_assignment.lab}: {e}')
                pending_update.status = PendingCanvasGradeUpdate.STATUS_FAILED
                pending_update.save()


_grade_update_thread = threading.Thread(target=_run_grade_updates, daemon=True)
_grade_update_thread.start()
