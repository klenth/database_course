import requests
from django.utils.text import slugify
from lms import canvas_api_token as credentials
from .models import *
import re
import logging


def canvas_paginated_request(rel_url, data=None):
    results = []

    current_url = f'{credentials.base_url}/{rel_url}'

    while True:
        response = requests.get(
            url=current_url,
            headers={'Authorization': f'Bearer {credentials.token}'},
            json=data
        )

        response.raise_for_status()

        results += response.json()

        if not (response.links and 'next' in response.links):
            break

        current_url = response.links['next']['url']

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
