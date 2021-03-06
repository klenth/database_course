# Generated by Django 3.2.5 on 2021-07-03 02:19

import dbmanager.models
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('course', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ClassDatabase',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=64, unique=True)),
                ('published', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='StudentDatabase',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=64, unique=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='StudentDatabaseAccess',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('write_permission', models.BooleanField(default=False)),
                ('database', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='shared_with_students', to='dbmanager.studentdatabase')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='shared_databases', to='course.student')),
            ],
        ),
        migrations.AddField(
            model_name='studentdatabase',
            name='other_students',
            field=models.ManyToManyField(related_name='other_databases', through='dbmanager.StudentDatabaseAccess', to='course.Student'),
        ),
        migrations.AddField(
            model_name='studentdatabase',
            name='owner',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='databases', to='course.student'),
        ),
        migrations.CreateModel(
            name='DatabaseSnapshot',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('request_time', models.DateTimeField(default=None, null=True)),
                ('completion_time', models.DateTimeField(default=None, null=True)),
                ('database_name', models.CharField(default='', max_length=64)),
                ('table_names', models.TextField(default='')),
                ('success', models.BooleanField(default=None, null=True)),
                ('stdout', models.TextField(default='')),
                ('stderr', models.TextField(default='')),
                ('database', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='exports', to='dbmanager.studentdatabase')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='exports', to='course.student')),
            ],
        ),
        migrations.CreateModel(
            name='DatabaseImport',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('request_time', models.DateTimeField(default=None, null=True)),
                ('completion_time', models.DateTimeField(default=None, null=True)),
                ('source_file', models.CharField(default='', max_length=40)),
                ('success', models.BooleanField(default=None, null=True)),
                ('stdout', models.TextField(default='')),
                ('stderr', models.TextField(default='')),
                ('database', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='imports', to='dbmanager.studentdatabase')),
                ('source_export', models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to='dbmanager.databasesnapshot')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='imports', to='course.student')),
            ],
        ),
        migrations.CreateModel(
            name='AccessToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('write_permission', models.BooleanField(default=False)),
                ('username', models.CharField(default=dbmanager.models._choose_access_token_username, max_length=64)),
                ('password', models.CharField(default=dbmanager.models._choose_access_token_password, max_length=64)),
                ('database', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tokens', to='dbmanager.studentdatabase')),
            ],
        ),
        migrations.AddConstraint(
            model_name='studentdatabaseaccess',
            constraint=models.UniqueConstraint(fields=('student', 'database'), name='unique_student_database'),
        ),
    ]
