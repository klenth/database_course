from django import template

register = template.Library()


@register.filter(name='exports')
def student_exports(student, course=None):
    if course:
        return student.exports.filter(course=course)
    else:
        return student.exports.all()


@register.filter(name='databases')
def student_databases(student, course=None):
    if course:
        return student.databases.filter(course=course)
    else:
        return student.databases.all()


@register.filter(name='databases_shared_with')
def student_databases_shared_with(student, course=None):
    if course:
        return student.shared_databases.filter(database__course=course)
    else:
        return student.shared_databases.all()
