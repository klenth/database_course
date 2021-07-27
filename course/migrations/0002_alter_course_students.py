# Generated by Django 3.2.5 on 2021-07-13 20:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('course', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='course',
            name='students',
            field=models.ManyToManyField(related_name='courses', through='course.Enrollment', to='course.Student'),
        ),
    ]