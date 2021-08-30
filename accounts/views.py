from django.shortcuts import render, get_object_or_404, redirect
from django.http import Http404, HttpResponseRedirect
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth.models import User
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from course import util as course_util
from course.models import Student, Instructor

def password_reset_confirm(request, uidb64, token):
    uid = urlsafe_base64_decode(uidb64).decode()
    user = get_object_or_404(User, id=uid)
    token_generator = PasswordResetTokenGenerator()

    context = {
        'validlink': False,
        'errors': [],
    }

    if token == 'set-password':
        session_token = request.session.get('_password_reset_token')
        if token_generator.check_token(user, session_token):
            context['validlink'] = True

            if request.method == 'POST':
                pw1 = request.POST.get('password1')
                pw2 = request.POST.get('password2')

                if not pw1 or not pw2:
                    context['errors'].append('Must specify a password')
                elif pw1 != pw2:
                    context['errors'].append('Passwords do not match')
                elif not course_util.validate_password(pw1):
                    context['errors'].append('Password must be at least eight characters long and contain at least three of the following: lowercase letter, uppercase letter, digit, non-alphanumeric character, and alphabetic letter without case')
                else:
                    maybe_student = Student.objects.filter(id=user.id)
                    if maybe_student.exists() and (student := maybe_student.get()):
                        student.set_password(pw1)
                        student.save()
                    else:
                        maybe_instr = Instructor.objects.get(id=user.id)
                        if maybe_instr.exists() and (instr := maybe_instr.get()):
                            instr.set_password(pw1)
                            instr.save()
                        else:
                            user.set_password(pw1)
                            user.save()

                    return redirect('password_reset_complete')

    elif token_generator.check_token(user, token):
        request.session['_password_reset_token'] = token
        redirect_url = request.path.replace(token, 'set-password')
        return HttpResponseRedirect(redirect_url)

    return render(request, 'registration/password_reset_confirm.html', context)

