from django.db import models
from course.models import *
from lab.models import *


class CanvasCourse(models.Model):
    course = models.OneToOneField(to=Course, null=False, on_delete=models.CASCADE, related_name='canvas_course')
    canvas_id = models.CharField(max_length=32)
    auto_update_assignment_grades = models.BooleanField(null=False, default=False)

    def canvas_students(self):
        return CanvasStudent.objects.filter(student__enrollment__course=self.course)


class CanvasStudent(models.Model):
    student = models.OneToOneField(to=Student, null=False, on_delete=models.CASCADE, related_name='canvas_student')
    canvas_id = models.CharField(max_length=32)


class CanvasAssignment(models.Model):
    lab = models.OneToOneField(to=Lab, null=False, on_delete=models.CASCADE, related_name='canvas_assignment')
    canvas_id = models.CharField(max_length=32)
    auto_update_grade = models.BooleanField(null=True, default=None)

    def get_auto_update_grade(self):
        if self.auto_update_grade is not None:
            return self.auto_update_grade
        elif (canvas_course := self.lab.course.canvas_course) is not None:
            return canvas_course.auto_update_assignment_grades
        else:
            return False
