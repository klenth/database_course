from django.db import models
from course.models import *
from lab.models import *


class CanvasCourse(models.Model):
    course = models.OneToOneField(to=Course, null=False, on_delete=models.CASCADE, related_name='canvas_course')
    canvas_id = models.CharField(max_length=32)
    auto_update_assignment_grades = models.BooleanField(null=False, default=False)

    def __str__(self):
        return f'Course {self.canvas_id} for {self.course.title}'

    def canvas_students(self):
        return CanvasStudent.objects.filter(student__enrollment__course=self.course)


class CanvasStudent(models.Model):
    student = models.OneToOneField(to=Student, null=False, on_delete=models.CASCADE, related_name='canvas_student')
    canvas_id = models.CharField(max_length=32)

    def __str__(self):
        return f'Student {self.canvas_id} ({self.student.name})'


class CanvasAssignment(models.Model):
    lab = models.OneToOneField(to=Lab, null=False, on_delete=models.CASCADE, related_name='canvas_assignment')
    canvas_id = models.CharField(max_length=32)
    auto_update_grade = models.BooleanField(null=True, default=None)

    def __str__(self):
        return f'Assignment {self.canvas_id} ({self.lab.title})'

    def get_auto_update_grade(self):
        if self.auto_update_grade is not None:
            return self.auto_update_grade
        elif (canvas_course := self.lab.course.canvas_course) is not None:
            return canvas_course.auto_update_assignment_grades
        else:
            return False


class PendingCanvasGradeUpdate(models.Model):
    STATUS_UNATTEMPTED = 'U'
    STATUS_FAILED = 'F'

    STATUS_CHOICES = (
        (STATUS_UNATTEMPTED, 'unattempted'),
        (STATUS_FAILED, 'failed'),
    )

    canvas_student = models.ForeignKey(to=CanvasStudent, null=False, on_delete=models.CASCADE, related_name='+')
    canvas_assignment = models.ForeignKey(to=CanvasAssignment, null=False, on_delete=models.CASCADE, related_name='+')
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default=STATUS_UNATTEMPTED, null=False)
    requested = models.DateTimeField(null=False, auto_now_add=True)

    class Meta:
        constraints = (
            models.UniqueConstraint(fields=('canvas_student', 'canvas_assignment'), name='unique_student_assignment'),
        )
