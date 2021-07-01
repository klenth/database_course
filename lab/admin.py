from django.contrib import admin
from lab import models


class StudentAdmin(admin.ModelAdmin):
    fieldsets = [
        ('Authentication information',
            {'fields': ['username', 'password']}),
        ('Student details',
            {'fields': ['name', 'sortable_name', 'email', 'student_id']})
    ]


admin.site.register(models.Instructor)
admin.site.register(models.Student, StudentAdmin)
admin.site.register(models.Course)
admin.site.register(models.Enrollment)
admin.site.register(models.Problem)
admin.site.register(models.Lab)
admin.site.register(models.ProblemOnLab)
admin.site.register(models.ProblemSchema)
admin.site.register(models.ProblemTableData)
admin.site.register(models.ProblemTestCase)
admin.site.register(models.ProblemTestCaseTableData)
admin.site.register(models.ProblemAttempt)
admin.site.register(models.AttemptResults)
