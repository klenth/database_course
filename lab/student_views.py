from django.shortcuts import render, redirect, reverse, get_object_or_404
from django.http import Http404
import django.contrib.auth.decorators as auth_decorators
from .models import *
from . import labs
from lms.models import *
from . import errors

def get_student(request):
    maybe_instructor = Instructor.objects.filter(id=request.user.id)
    if maybe_instructor.exists():
        return maybe_instructor.get().dummy()
    return get_object_or_404(Student, id=request.user.id)


def student_home(request, student):
    context = {
        'student': student,
        'courses': student.courses(),
    }

    # if student.is_dummy:
    #     context['alter_ego'] = student.alter_ego

    return render(request, 'lab/student/student_home.html', context)


@auth_decorators.login_required
def view_lab(request, lab_id):
    student = get_student(request)
    lab = get_object_or_404(Lab, pk=lab_id)

    if student not in lab.course.students.all() and not \
            (student.is_dummy and student.alter_ego.pk == lab.course.instructor.pk):
        raise Http404

    if not lab.enabled:
        raise Http404

    context = {
        'student': student,
        'lab': lab,
    }

    if student.is_dummy:
        context['instructor_href'] = reverse('instructor_view_lab', kwargs={'lab_id': lab_id})

    return render(request, 'lab/student/view_lab.html', context)


@auth_decorators.login_required
def view_problem(request, problem_id, attempt_id=None, as_username=None, as_uuid=None):
    from lms import canvas

    problem = get_object_or_404(Problem, pk=problem_id)
    lab = problem.lab()
    viewing_as = False

    student = get_student(request)

    # If a student (not a dummy) is trying to view the problem "as" a student, fail unless they are viewing it as
    # themselves. (And if they are, redirect to the not-"as" version.)
    if not student.is_dummy and (as_uuid or as_username):
        if as_uuid == student.uuid or as_username == student.username:
            if attempt_id:
                return redirect('student_view_problem_attempt', problem_id=problem.id, attempt_id=attempt_id)
            else:
                return redirect('student_view_problem', problem_id=problem.id)
        else:
            raise Http404

    # Otherwise, if we are viewing "as" a student, we'd better be an instructor! (And the instructor of this class, yet)
    if as_uuid or as_username:
        instructor = get_object_or_404(Instructor, id=request.user.id)
        if not lab.course.instructor == instructor:
            raise Http404

        if as_uuid:
            student = get_object_or_404(Student, pk=as_uuid)
        else:
            student = get_object_or_404(Student, username=as_username)

        viewing_as = True

    if student not in lab.course.students.all() and not \
            (student.is_dummy and student.alter_ego.pk == lab.course.instructor.pk):
        raise Http404

    current_score = student.score_on_problem(problem)

    if request.method == 'POST':
        text = request.POST.get('text', None)
        if text:
            attempt = ProblemAttempt(student=student, problem=problem, text=text, score=0)
            attempt.save()
            try:
                attempt.score = labs.score(attempt)
            except errors.StudentCodeError as e:
                attempt.score = 0
                attempt.error_text = str(e)
            except errors.ProblemError as e:
                attempt.score = 0
                attempt.error_text = f'''There was an error grading your attempt. This error is not your fault; there is
something wrong in the specification of the problem. Please contact your
instructor and pass along the following error message:

-----
f{str(e)}'''

            attempt.save()

            maybe_canvas_assignment = CanvasAssignment.objects.filter(lab=lab)
            maybe_canvas_student = CanvasStudent.objects.filter(student=student)
            if attempt.score > current_score \
                    and maybe_canvas_assignment.exists() \
                    and maybe_canvas_student.exists() \
                    and maybe_canvas_assignment.get().get_auto_update_grade():
                # lab_score = student.score_on_lab(lab)
                # canvas.update_grade_if_higher(
                #     canvas_student=canvas_student, canvas_assignment=canvas_assignment,
                #     grade=lab_score,
                # )
                canvas.submit_grade_update_task(canvas_student=maybe_canvas_student.get(), canvas_assignment=maybe_canvas_assignment.get())
        return redirect('student_view_problem', problem_id=problem_id)
    else:
        #attempts = list(student.attempts(problem))
        attempts = list(ProblemAttempt.objects.filter(student=student, problem=problem))

        selected_attempt = None
        if attempt_id:
            selected_attempt = get_object_or_404(ProblemAttempt, id=attempt_id)
            if selected_attempt.student != student:
                raise Http404
        elif attempts:
            selected_attempt = attempts[-1]

        context = {
            'problem': problem,
            'student': student,
            'attempts': attempts,
            'selected_attempt': selected_attempt,
            'recent_attempt_text': selected_attempt.text if selected_attempt else attempts[-1].text if attempts else problem.starter_code,
            'recent_attempt_error': selected_attempt.error_text if selected_attempt else attempts[-1].error_text if attempts else '',
            'current_percent': float(student.score_on_problem(problem)) * 100.0,
            'current_score': current_score,
            'viewing_as_other': viewing_as,
        }

        if student.is_dummy:
            context['instructor_href'] = reverse('instructor_view_problem', kwargs={'problem_id': problem_id})

        return render(request, 'lab/student/view_problem.html', context)


@auth_decorators.login_required
def request_help(request, problem_id):
    problem = get_object_or_404(Problem, pk=problem_id)
    lab = problem.lab()

    student = get_student(request)

    if student not in lab.course.students.all():
        raise Http404

    attempts = ProblemAttempt.objects.filter(student=student, problem=problem)
    attempt = attempts.last() if attempts else None

    help_url = labs.get_help_url(student=student, problem=problem, attempt=attempt, by_uuid=True)

    context = {
        'student': student,
        'problem': problem,
        'attempt': attempt,
        'help_url': help_url,
        'message': '',
        'email': student.email,
    }

    if request.method == 'POST':
        message = request.POST.get('message', '').strip()
        student_email = request.POST.get('email')

        errors = []
        context['errors'] = errors

        if not message:
            errors.append('You must include a message')
        if not student_email:
            errors.append('You must furnish an email address')
        elif '@' not in student_email:
            errors.append('You must furnish a valid email address')

        if not errors:
            labs.student_request_help(student=student, problem=problem, message=message, student_email=student_email)
            return render(request, 'lab/student/request_help_complete.html', context)
        else:
            context['message'] = message
            context['email'] = student_email

    return render(request, 'lab/student/request_help.html', context)

