# Generated by Django 3.2.5 on 2021-07-03 16:04

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('course', '0001_initial'),
        ('dbmanager', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='DatabaseProxyUser',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('username', models.CharField(max_length=30)),
                ('password', models.CharField(default='CigAL6PZwx11fva5Q919JJU2dwtPM0ZOebbe6ot9A8y7LP8uF8oOvXkrj4rNKbGo', max_length=64)),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='course.student', unique=True)),
            ],
        ),
    ]
