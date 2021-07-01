import markdown2
from django import template
from django.utils.html import conditional_escape, html_safe
from django.utils.safestring import mark_safe
from django.template.defaultfilters import stringfilter
from lab.labs import QueryResults
from django.utils import timezone
import datetime
from lab.errors import DataFileMissingError

register = template.Library()


@register.filter(name='loadcsv')
def load_csv(data_file):
    if not data_file or not data_file.name:
        raise DataFileMissingError
    else:
        return QueryResults.from_csv(data_file.open('r'))


@register.filter(name='datatable', needs_autoscape=True)
def data_table(qr, compare_to=None, autoescape=True):
    if autoescape:
        esc = conditional_escape
    else:
        esc = lambda x: x

    header = '<tr>'
    for j, col in zip(range(len(qr.column_names)), qr.column_names):
        if compare_to and (len(compare_to.column_names) <= j or qr.column_names[j] != compare_to.column_names[j]):
            header += '<th class="different">'
        else:
            header += '<th>'
        header += esc(str(qr.column_names[j])) or '&nbsp;'
        header += '</th>'
    header += '</tr>'

    body = ''
    for i, row in zip(range(len(qr.rows)), qr.rows):
        body += '<tr>'
        for j, col in zip(range(len(row)), row):
            if compare_to and (len(compare_to.rows) <= i or len(compare_to.rows[i]) <= j
                               or row[j] != compare_to.rows[i][j]):
                body += '<td class="different">'
            else:
                body += '<td>'
            body += esc(str(row[j])) or '&nbsp;'
            body += '</td>'
        body += '</tr>'

    return mark_safe(f'<thead>{header}</thead><tbody>{body}</tbody>')


@register.filter(name='friendlytime')
def friendly_time(then):
    tz = timezone.get_current_timezone()
    now = timezone.now()

    then = tz.normalize(then)
    now = tz.normalize(now)

    # Show as just a time if it's on the same day or within 6 hours
    if then.date() == now.date() \
            or now - then < datetime.timedelta(hours=6):
        return then.strftime('%-I:%M %p').lower()
    # Or, if it was yesterday, say so
    elif now.date() - then.date() == datetime.timedelta(days=1):
        return then.strftime('Yesterday at %-I:%M ') + then.strftime('%p').lower()
    # Or, if it was within the last six days, give day of week and time
    elif now.date() - then.date() < datetime.timedelta(days=6):
        return then.strftime('%A at %-I:%M ') + then.strftime('%p').lower()
    # Otherwise, just do date and time
    else:
        return then.strftime('%-m/%-d at %-I:%M %p').lower()


__markdown = None


def get_markdown():
    import markdown2
    global __markdown

    if not __markdown:
        __markdown = markdown2.Markdown(extras=('code-friendly', 'tables'))
    return __markdown


@register.filter(name='markdown')
@stringfilter
def markdown(source):
    return mark_safe(f'''
        <div class="markdown">
            {get_markdown().convert(source)}
        </div>''')


@register.filter(name='scoreonproblem')
def student_score_on_problem(student, problem):
    return mark_safe(str(student.score_on_problem(problem)))


@register.filter(name='scoreonlab')
def student_score_on_lab(student, lab):
    return mark_safe(str(student.score_on_lab(lab)))


@register.filter(name='enabledonly')
def enabled_items(items):
    return list(i for i in items if i.enabled)


@register.filter(name='disabledonly')
def disabled_items(items):
    return list(i for i in items if not i.enabled)
