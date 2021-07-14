from django.shortcuts import render, redirect, get_object_or_404
from django.http import Http404
import django.contrib.auth.decorators as auth_decorators
from .models import *
from . import labs


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

    if student.is_dummy:
        context['alter_ego'] = student.alter_ego

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
        context['alter_ego'] = student.alter_ego

    return render(request, 'lab/student/view_lab.html', context)


@auth_decorators.login_required
def view_problem(request, problem_id, attempt_id=None):
    problem = get_object_or_404(Problem, pk=problem_id)
    student = get_student(request)

    if student not in problem.lab().course.students.all() and not \
            (student.is_dummy and student.alter_ego.pk == problem.lab().course.instructor.pk):
        raise Http404

    if request.method == 'POST':
        text = request.POST.get('text', None)
        if text:
            attempt = ProblemAttempt(student=student, problem=problem, text=text, score=0)
            attempt.save()
            attempt.score = labs.score(attempt)
            attempt.save()
        return redirect('student_view_problem', problem_id=problem_id)
    else:
        #attempts = list(student.attempts(problem))
        attempts = list(ProblemAttempt.objects.filter(student=student, problem=problem))

        selected_attempt = None
        if attempt_id:
            selected_attempt = get_object_or_404(ProblemAttempt, id=attempt_id)
        elif attempts:
            selected_attempt = attempts[-1]

        context = {
            'problem': problem,
            'student': student,
            'attempts': attempts,
            'selected_attempt': selected_attempt,
            'recent_attempt_text': selected_attempt.text if selected_attempt else attempts[-1].text if attempts else problem.starter_code,
            'current_percent': float(student.score_on_problem(problem)) * 100.0,
            'current_score': student.score_on_problem(problem),
        }

        if student.is_dummy:
            context['alter_ego'] = student.alter_ego

        return render(request, 'lab/student/view_problem.html', context)
