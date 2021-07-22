from django.db import models
from course.models import *


class CanvasCourse(models.Model):
    course = models.OneToOneField(to=Course, null=False, on_delete=models.CASCADE)
    canvas_id = models.CharField(max_length=32)

    def canvas_students(self):
        return CanvasStudent.objects.filter(student__enrollment__course=self.course)


class CanvasStudent(models.Model):
    student = models.OneToOneField(to=Student, null=False, on_delete=models.CASCADE)
    canvas_id = models.CharField(max_length=32)
