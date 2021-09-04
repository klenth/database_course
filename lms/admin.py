from django.contrib import admin
from .models import *


admin.site.register(CanvasCourse)
admin.site.register(CanvasStudent)
admin.site.register(CanvasAssignment)
admin.site.register(PendingCanvasGradeUpdate)
