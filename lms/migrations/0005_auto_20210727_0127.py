# Generated by Django 3.2.5 on 2021-07-27 01:27

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('lms', '0004_auto_20210725_2255'),
    ]

    operations = [
        migrations.CreateModel(
            name='PendingCanvasGradeUpdate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('U', 'unattempted'), ('F', 'failed')], default='U', max_length=1)),
                ('requested', models.DateTimeField(auto_now_add=True)),
                ('canvas_assignment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='lms.canvasassignment')),
                ('canvas_student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='lms.canvasstudent')),
            ],
        ),
        migrations.AddConstraint(
            model_name='pendingcanvasgradeupdate',
            constraint=models.UniqueConstraint(fields=('canvas_student', 'canvas_assignment'), name='unique_student_assignment'),
        ),
    ]
