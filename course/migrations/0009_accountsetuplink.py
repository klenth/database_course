# Generated by Django 3.2.5 on 2021-08-10 21:58

import course.models
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('course', '0008_alter_course_handle'),
    ]

    operations = [
        migrations.CreateModel(
            name='AccountSetupLink',
            fields=[
                ('id', models.CharField(default=course.models._random_link_id, max_length=32, primary_key=True, serialize=False)),
                ('expiration', models.DateTimeField()),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='course.student')),
            ],
        ),
    ]
