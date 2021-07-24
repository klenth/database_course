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
        if (m := term_pattern.match(term_name)):
            return -int(m.group(2)), m.group(1)
        else:
            return (-9999, term_name)

    courses.sort(key=lambda c: (term_key(c['term']), c['handle']))

    return courses


def update_enrollment(canvas_course):
    logging.info(f'Updating enrollment for {canvas_course.course.title}')
    student_data = canvas_paginated_request(f'courses/{canvas_course.canvas_id}/users?enrollment_type[]=student')

    known_students = {
        student.canvas_id: student
        for student in canvas_course.canvas_students()
    }

    for student in student_data:
        #user_info = student["user"]
        print(student)
        canvas_id = str(student['id'])
        name, sortable_name = student['name'], student['sortable_name']
        login_id = student.get('login_id', None)
        email = student.get('email', None)

        if not login_id and email:
            login_id = email[:email.find('@')]
        elif not login_id:
            login_id = slugify(name)

        if canvas_id not in known_students:
            logging.info(f'\t→ Adding {name} ({canvas_id}) / {login_id}')
            new_student = Student(name=name, sortable_name=sortable_name, username=login_id, email=email)
            new_student.save()

            enrollment = Enrollment(
                student=new_student,
                course=canvas_course.course,
            )
            enrollment.save()

            new_canvas_student = CanvasStudent(student=new_student, canvas_id=canvas_id)
            new_canvas_student.save()
        else:
            logging.info(f'\t→ Skipping {name} ({canvas_id})')
