# Generated by Django 3.2.5 on 2021-07-15 20:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('course', '0006_course_handle'),
    ]

    operations = [
        migrations.AlterField(
            model_name='course',
            name='handle',
            field=models.CharField(max_length=30, unique=True),
        ),
    ]