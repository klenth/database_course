from django.shortcuts import reverse
from django.contrib.auth.models import User
from django.core.mail import send_mail
from database_course.settings import SITE_BASE_URL, SYSTEM_EMAIL


def validate_password(password):
    has_lower, has_upper, has_digit, has_nonalpha, has_noncased = (False,) * 5
    for c in password:
        if c.islower():
            has_lower = True
        if c.isupper():
            has_upper = True
        if '0' <= c <= '9':
            has_digit = True
        if not c.isalpha():
            has_nonalpha = True
        if c.isalpha() and not c.islower() and not c.isupper():
            has_noncased = True

    count = sum(map(lambda b: int(b), (has_lower, has_upper, has_digit, has_nonalpha, has_noncased)))
    return len(password) >= 8 and count >= 3


def validate_user_information(*, name, email, password1, password2, username=None, errorlist=None):
    if errorlist is None:
        errorlist = []

    # Validate name
    if not name:
        errorlist.append('You must specify a name')

    # Validate email
    if not email:
        errorlist.append('You must specify an email address')
    elif '@' not in email:
        errorlist.append('Email address must contain an "@"')

    # Validate username
    if username is not None:
        if not username:
            errorlist.append('You must specify a username')
        elif '/' in username:
            errorlist.append('Invalid username')
        else:
            clashing_person = User.objects.filter(username=username)
            if clashing_person.exists():
                errorlist.append('That username is already taken; please choose another')

    # Validate password
    if not password1 or not password2:
        errorlist.append('You must specify a password')
    elif password1 != password2:
        errorlist.append('Passwords must match')
    elif not validate_password(password1):
        errorlist.append(
            'Password must be at least eight characters long and contain at least three of the following: lowercase letter, uppercase letter, digit, non-alphanumeric character, and alphabetic letter without case')

    return errorlist


def email_account_setup_link(link, email, instructor=None):
    subject = 'Account setup link'
    setup_url = reverse('course_setup_account', kwargs={'link_id': link.id})

    body = f'Hello {link.student.name},\n\n'

    if instructor:
        body += f'{instructor.name} has invited you to set up an account.'
    else:
        body += 'You have been invited to set up an account.'

    body += f'''\n
Using this account, you will be able to manage your databases on the class
server and participate in labs.
     
Please click the link below to set up your account:
    {SITE_BASE_URL}{setup_url}
    '''

    if instructor:
        body += f'\n\nPlease contact {instructor.name} at {instructor.email} if you have any questions.'

    send_mail(subject=subject, message=body, from_email=SYSTEM_EMAIL, recipient_list=(email,), fail_silently=False)
