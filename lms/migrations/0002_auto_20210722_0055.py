# Generated by Django 3.2.5 on 2021-07-22 00:55

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('course', '0008_alter_course_handle'),
        ('lms', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='canvascourse',
            name='course',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='course.course'),
        ),
        migrations.CreateModel(
            name='CanvasStudent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('canvas_id', models.CharField(max_length=32)),
                ('student', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='course.student')),
            ],
        ),
    ]
