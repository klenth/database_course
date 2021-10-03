import string
import uuid

from django.db import models
from django.db.models import signals
from django.dispatch import receiver
from course.models import Person, Student, Instructor, DummyStudent, Course, Enrollment
import lab.settings
import csv
import os
from . import labs
from . import util


class ProblemSchema(models.Model):
    SCHEMA_MISSING = 'M'
    SCHEMA_PROCESSING = 'P'
    SCHEMA_VALID = 'V'
    SCHEMA_INVALID = 'I'

    SCHEMA_STATUS_CHOICES = (
        (SCHEMA_MISSING, 'Missing'),
        (SCHEMA_PROCESSING, 'Processing'),
        (SCHEMA_VALID, 'Valid'),
        (SCHEMA_INVALID, 'Invalid')
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid1)
    file = models.FileField(upload_to=f'{lab.settings.UPLOAD_SCHEMA_DIR}/%Y/%m/%d/', null=True, default=None)
    filename = models.CharField(max_length=100, null=True, default=None)
    status = models.CharField(max_length=1, choices=SCHEMA_STATUS_CHOICES, null=False, blank=False, default=SCHEMA_MISSING)
    table_names = models.CharField(max_length=200, null=False, blank=True, default='')  # Comma-separated list

    class Meta:
        verbose_name = 'Problem schema'
        verbose_name_plural = 'Problem schemata'

    def __str__(self):
        return self.filename

    def get_table_names(self):
        if not self.table_names:
            return ()

        def csv_file():
            yield self.table_names

        reader = csv.reader(csv_file())
        return tuple(next(reader))

    def set_table_names(self, table_names):
        class CsvFile:
            def write(self2, line):
                self.table_names = line.strip()

        writer = csv.writer(CsvFile())
        writer.writerow(table_names)

        self.save()

    @staticmethod
    def create_from_upload(upload_file):
        schema = ProblemSchema(filename=upload_file.name, status=ProblemSchema.SCHEMA_PROCESSING)
        schema.file.save(name=str(uuid.uuid1()), content=upload_file)
        schema.save()
        labs.validate_schema(schema)
        return schema


class Problem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid1)
    title = models.CharField(max_length=100, null=False, blank=True, default='')
    prompt = models.TextField(null=False, blank=True, default='')
    starter_code = models.TextField(null=False, blank=True, default='')
    solution = models.TextField(null=False, blank=True, default='')
    after_code = models.TextField(null=False, blank=True, default='')
    schema = models.ForeignKey(to=ProblemSchema, on_delete=models.RESTRICT, null=True, default=None, related_name='referenced_problems')
    enabled = models.BooleanField(default=False)

    def __str__(self):
        return self.title

    # Return the (unique) lab that this problem is on, or None if there is none. (See ProblemOnLab's uniqueness
    # constraint.)
    def lab(self):
        maybe_pols = ProblemOnLab.objects.filter(problem=self)
        return maybe_pols.get().lab if maybe_pols.exists() else None

    def set_schema(self, schema):
        old_schema = self.schema
        self.schema = schema
        self.save()

        if old_schema and old_schema.referenced_problems.count() == 0:
            old_schema.delete()

        new_schema_table_names = ()
        if schema:
            new_schema_table_names = schema.get_table_names()

        ProblemTestCaseTableData.objects \
            .filter(test_case__problem=self) \
            .exclude(table_name__in=new_schema_table_names) \
            .delete()

        self.reset_results()

    def is_schema_ok(self):
        return self.schema_status in (Problem.SCHEMA_VALID, Problem.SCHEMA_MISSING)

    def add_new_test_case(self):
        max_number = self.test_cases.aggregate(max_number=models.Max('number'))['max_number'] or 0
        ptc = ProblemTestCase(problem=self, number=max_number + 1, title=f'Test case {max_number + 1}')
        ptc.save()
        return ptc

    # Delete a test case, renumbering the remaining test cases if necessary
    def delete_test_case(self, test_case):
        if test_case.problem != self:
            raise ValueError('Test case does not belong to this problem!')
        number = test_case.number
        test_case.delete()

        test_cases = self.test_cases.filter(number__gte=number).order_by('number')
        for case, i in zip(test_cases, range(len(test_cases))):
            case.number = number + i
            case.save()

    def reset_results(self):
        for tc in self.test_cases.all():
            tc.reset_result()

    def possible_points(self):
        return self.test_cases.aggregate(points=models.Sum('points'))['points']

    def duplicate(self, title=None):
        """Returns a new (saved) Problem object that is identical to this one (including test cases, table mappings,
        etc.). The duplicated problem does not have any student scoring data, however. If the specified title is None
        (the default) the problem will be named uniquely based on the original problem's title (one of "Copy of [title]",
        "Copy 2 of [title]", etc.)"""

        new_title = title
        if not new_title:
            new_title = util.unique_duplicate_name(self.title, [problem.title for problem in self.lab().problems.all()])

        if not new_title:
            counter = 1
            existing_titles = set([problem.title for problem in self.lab().problems.all()])
            new_title = self.title if self.title.startswith('Copy of ') else f'Copy of {self.title}'
            while new_title in existing_titles:
                counter += 1
                new_title = f'Copy {counter} of {self.title}'

        # Duplicate the problem itself
        new_problem = Problem(
            title=new_title,
            prompt=self.prompt,
            starter_code=self.starter_code,
            solution=self.solution,
            after_code=self.after_code,
            schema=self.schema
        )
        new_problem.save()

        # Duplicate all table data
        table_data_map = {}
        for table_data in self.table_data.all():
            new_table_data = ProblemTableData(
                problem=new_problem,
                data_filename=table_data.data_filename
            )
            new_table_data.data_file.save(name=str(uuid.uuid1()), content=table_data.data_file)
            new_table_data.save()

            table_data_map[table_data.id] = new_table_data

        # Duplicate test cases (including mappings of table data)
        test_case_map = {}
        for test_case in self.test_cases.all():
            new_test_case = ProblemTestCase(
                problem=new_problem,
                title=test_case.title,
                description=test_case.description,
                points=test_case.points,
                number=test_case.number,
                type=test_case.type
            )
            new_test_case.result_data_file.save(name=str(uuid.uuid1()), content=test_case.result_data_file)
            new_test_case.save()

            test_case_map[test_case.id] = new_test_case.id

            for tc_table_data in test_case.table_data_set.all():
                new_tc_table_data = ProblemTestCaseTableData(
                    test_case=new_test_case,
                    table_data=table_data_map[tc_table_data.table_data.id],
                    table_name=tc_table_data.table_name
                )
                new_tc_table_data.save()

        return new_problem


class ProblemTableData(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid1)
    problem = models.ForeignKey(to=Problem, on_delete=models.CASCADE, related_name='table_data')
    data_file = models.FileField(upload_to=f'{lab.settings.UPLOAD_TABLE_DATA_DIR}/%Y/%m/%d/', null=False)
    data_filename = models.CharField(max_length=100, null=False, blank=False)

    class Meta:
        ordering = ('data_filename',)
        verbose_name = 'Problem table data'
        verbose_name_plural = 'Problem table data'

    def __str__(self):
        return self.data_filename


class ProblemTestCase(models.Model):
    TEST_CASE_TYPE_TABLE_DATA = 'D'
    TEST_CASE_TYPE_COLUMN_NAMES = 'N'

    TYPE_CHOICES = (
        (TEST_CASE_TYPE_TABLE_DATA, 'Table data'),
        (TEST_CASE_TYPE_COLUMN_NAMES, 'Column names'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid1)
    problem = models.ForeignKey(to=Problem, on_delete=models.CASCADE, related_name='test_cases')
    title = models.CharField(max_length=100, null=False, blank=True, default='')
    description = models.CharField(max_length=100, null=False, blank=True, default='')
    points = models.PositiveSmallIntegerField(null=False, default=1)
    number = models.PositiveSmallIntegerField(null=False, default=0)
    result_data_file = models.FileField(upload_to=f'{lab.settings.UPLOAD_CORRECT_RESULT_DIR}/%Y/%m/%d/', null=True, default=None)
    type = models.CharField(max_length=1, choices=TYPE_CHOICES, default=TEST_CASE_TYPE_TABLE_DATA, null=False, blank=False)

    class Meta:
        ordering = ('number',)

    def __str__(self):
        return self.title

    # Returns a dictionary whose keys are table names and values are ProblemTableData objects. If a table doesn't have
    # a table data, the value will be None. If table_names is specified, the dictionary has just those keys; otherwise
    # all the problem's tables are included.
    def get_table_data_mapping(self, table_names=None):
        table_names = self.problem.schema.get_table_names() if table_names is None and self.problem.schema else table_names
        mapping = {
            table_name: None for table_name in table_names
        }

        for ptctd in self.table_data_set.all():
            mapping[ptctd.table_name] = ptctd.table_data

        return mapping

    def reset_result(self):
        if self.result_data_file:
            self.result_data_file.delete()
            self.result_data_file = None
            self.save()


class ProblemTestCaseTableData(models.Model):
    test_case = models.ForeignKey(to=ProblemTestCase, on_delete=models.CASCADE, related_name='table_data_set')
    table_data = models.ForeignKey(to=ProblemTableData, on_delete=models.CASCADE, related_name='test_cases')
    table_name = models.CharField(max_length=40, null=False, blank=False)

    class Meta:
        ordering = ('table_name',)
        constraints = (
            models.UniqueConstraint(fields=('test_case', 'table_name'), name='unique_mapping_for_table'),
        )
        verbose_name = 'Problem test case table data'
        verbose_name_plural = 'Problem test case table data'

    def __str__(self):
        return self.table_name


class Lab(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid1)
    course = models.ForeignKey(to=Course, null=False, on_delete=models.CASCADE, related_name='labs')
    title = models.CharField(max_length=100, null=False, blank=False)
    creation_date = models.DateTimeField(auto_now_add=True, null=False)
    problems = models.ManyToManyField(to=Problem, through='ProblemOnLab')
    enabled = models.BooleanField(default=False)

    class Meta:
        constraints = (
            models.UniqueConstraint(fields=('course', 'title'), name='lab_title_unique'),
        )

    def __str__(self):
        return self.title

    def add_problem(self, problem):
        max_problem_number = self.problemonlab_set.aggregate(max_number=models.Max('problem_number'))['max_number']
        max_problem_number = max_problem_number or 0
        pol = ProblemOnLab(problem=problem, lab=self, problem_number=max_problem_number+1)
        pol.save()

    def enabled_problems(self):
        return self.problems.order_by('problemonlab__problem_number').filter(enabled=True)

    def total_points(self):
        return self.problems.order_by('problemonlab__problem_number').filter(enabled=True).aggregate(total_points=models.Sum('test_cases__points'))['total_points'] or 0

    def enabled_problem_count(self):
        return self.enabled_problems().count()

    def disabled_problem_count(self):
        return self.problems.filter(enabled=False).count()

    def duplicate(self):
        new_title = util.unique_duplicate_name(self.title, [lab.title for lab in self.course.labs.all()])

        new_lab = Lab(
            course=self.course,
            title=new_title,
        )
        new_lab.save()

        # Duplicate all the problems too 😀
        for problem in self.problems.all():
            dup_problem = problem.duplicate(title=problem.title)
            dup_problem.enabled = problem.enabled
            new_lab.add_problem(dup_problem)

        return new_lab


# I want this model so that I can also store the number of the problem on the lab. Django doesn't have a built-in way to
# do a 1:M relationship through a relationship table, so I'm hacking around that with a uniqueness constraint.
class ProblemOnLab(models.Model):
    problem = models.ForeignKey(to=Problem, null=False, on_delete=models.CASCADE)
    lab = models.ForeignKey(to=Lab, null=False, on_delete=models.CASCADE)
    problem_number = models.PositiveSmallIntegerField(null=False, default=0)

    class Meta:
        ordering = ('problem_number',)
        constraints = (
            models.UniqueConstraint(fields=('problem',), name='problem_unique'),
        )
        verbose_name = 'Problem on lab'
        verbose_name_plural = 'Problems on labs'


class ProblemAttempt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid1)
    student = models.ForeignKey(to=Student, on_delete=models.CASCADE, related_name='+')
    problem = models.ForeignKey(to=Problem, on_delete=models.RESTRICT, related_name='+')
    when = models.DateTimeField(auto_now_add=True)
    text = models.TextField()
    score = models.PositiveSmallIntegerField()
    error_text = models.TextField(null=False, blank=True, default='')

    class Meta:
        ordering = ('when',)


class AttemptResults(models.Model):
    attempt = models.ForeignKey(to=ProblemAttempt, on_delete=models.CASCADE, related_name='results')
    test_case = models.ForeignKey(to=ProblemTestCase, on_delete=models.RESTRICT, related_name='+')
    data_file = models.FileField(upload_to=f'{lab.settings.UPLOAD_ATTEMPT_RESULT_DIR}/%Y/%m/%d/', null=False)
    score = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ('test_case__number',)
        constraints = (
            models.UniqueConstraint(fields=('attempt', 'test_case'), name='attempt_results_unique'),
        )

    def correct_result_data_file(self):
        return self.test_case.result_data_file


# Django model for custom view: Meta.managed=False so Django will query the table and wrap in the model but will not
# manipulate the table (actually a view)
class StudentProblemScore(models.Model):
    id = models.CharField(max_length=65, primary_key=True)
    student = models.ForeignKey(to=Student, on_delete=models.DO_NOTHING, related_name='problem_scores')
    problem = models.ForeignKey(to=Problem, on_delete=models.DO_NOTHING, related_name='student_scores')
    score = models.PositiveSmallIntegerField()

    class Meta:
        db_table = 'custom_student_problem_scores'
        managed = False


# Triggers!
def unlink_if_exists(file):
    if os.path.exists(file.name):
        os.unlink(file.name)


@receiver(signals.post_delete, sender=ProblemSchema)
def handle_problem_schema_post_delete(sender, instance, using, **kwargs):
    unlink_if_exists(instance.file)


@receiver(signals.post_delete, sender=ProblemTableData)
def handle_problem_table_data_post_delete(sender, instance, using, **kwargs):
    unlink_if_exists(instance.data_file)


@receiver(signals.post_delete, sender=ProblemTestCase)
def handle_problem_test_case_post_delete(sender, instance, using, **kwargs):
    unlink_if_exists(instance.result_data_file)


@receiver(signals.post_delete, sender=AttemptResults)
def handle_attempt_results_post_delete(sender, instance, using, **kwargs):
    unlink_if_exists(instance.data_file)
