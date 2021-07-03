from django.db import models
from django.contrib.auth import models as auth_models
import uuid


class Person(auth_models.User):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid1)
    name = models.CharField(max_length=80, null=False, blank=False)
    sortable_name = models.CharField(max_length=80, null=False, blank=True)

    password_change_listeners = []

    class Meta:
        verbose_name = 'Person'
        verbose_name_plural = 'People'
        abstract = True

    def get_sortable_name(self):
        return self.sortable_name if self.sortable_name else self.name

    def set_password(self, raw_password):
        super().set_password(raw_password)
        self.save()
        for listener in Person.password_change_listeners:
            listener(self, raw_password)

    def __str__(self):
        return self.name

    @staticmethod
    def resolve(user):
        s = Student.objects.filter(id=user.id)
        if s.exists():
            return 'Student', s.get()

        i = Instructor.objects.filter(id=user.id)
        if i.exists():
            return 'Instructor', i.get()

        return None, None

    @staticmethod
    def password_change_listener(listener):
        Person.password_change_listeners.append(listener)
        return listener


class Instructor(Person):
    class Meta:
        verbose_name = 'Instructor'

    def dummy(self):
        return DummyStudent.dummy_for(self)


class Student(Person):
    student_id = models.CharField(max_length=10, null=False, blank=True, default='')
    is_dummy = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Student'

    def score_on_problem(self, problem):
        maybe_score = self.problem_scores.filter(problem=problem)
        print(maybe_score.query)
        return maybe_score.get().score if maybe_score.exists() else 0.0

    def score_on_lab(self, lab):
        return self.problem_scores.filter(problem__problemonlab__lab=lab, problem__enabled=True).aggregate(score=models.Sum('score'))['score'] or 0.0

    def courses(self):
        if self.is_dummy:
            return DummyStudent.objects.get(id=self.id).courses()
        return self.course_set.all()


class DummyStudent(Student):
    alter_ego = models.ForeignKey(to=Instructor, on_delete=models.CASCADE, null=False, related_name='+')

    @staticmethod
    def dummy_for(instructor):
        maybe_dummy = DummyStudent.objects.filter(alter_ego=instructor)
        if maybe_dummy.exists():
            return maybe_dummy.get()
        else:
            dummy = DummyStudent(
                alter_ego=instructor,
                is_dummy=True,
                username=f'{instructor.username}/dummy',
                name=f'{instructor.name} (student)',
                sortable_name=instructor.sortable_name
            )
            dummy.save()
            return dummy

    def courses(self):
        return self.alter_ego.courses.all()


class Course(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid1)
    title = models.CharField(max_length=80, null=False, blank=False)
    instructor = models.ForeignKey(to=Instructor, null=False, on_delete=models.RESTRICT, related_name='courses')
    students = models.ManyToManyField(to=Student, through='Enrollment')

    class Meta:
        constraints = (
            models.UniqueConstraint(fields=('instructor', 'title',), name='unique_course_title'),
        )

    def __str__(self):
        return self.title

    def enabled_labs(self):
        return self.labs.filter(enabled=True)

    def disabled_labs(self):
        return self.labs.filter(enabled=False)


class Enrollment(models.Model):
    student = models.ForeignKey(to=Student, null=False, on_delete=models.RESTRICT)
    course = models.ForeignKey(to=Course, null=False, on_delete=models.RESTRICT)
    active = models.BooleanField(default=True)

    class Meta:
        constraints = (
            models.UniqueConstraint(fields=['student', 'course'], name='unique_student_course'),
        )

    def __str__(self):
        return f'{self.student} / {self.course}{"" if self.active else " (inactive)"}'
