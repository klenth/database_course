# Generated by Django 3.2 on 2021-04-14 22:53

from django.db import migrations, models
import django.db.models.deletion
import pathlib
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('lab', '0007_problem_after_code'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProblemTableData',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid1, primary_key=True, serialize=False)),
                ('data_file', models.FileField(upload_to=pathlib.PurePosixPath('/home/kathy/PycharmProjects/sql_lab/upload'))),
                ('data_filename', models.CharField(max_length=100)),
            ],
            options={
                'ordering': ('data_filename',),
            },
        ),
        migrations.CreateModel(
            name='ProblemTestCaseTableData',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('table_name', models.CharField(max_length=40)),
                ('table_data', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, to='lab.problemtabledata')),
            ],
            options={
                'ordering': ('table_name',),
            },
        ),
        migrations.AddField(
            model_name='problem',
            name='table_names',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
        migrations.AlterField(
            model_name='problemtestcase',
            name='title',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.DeleteModel(
            name='TestCaseData',
        ),
        migrations.AddField(
            model_name='problemtestcasetabledata',
            name='test_case',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='lab.problemtestcase'),
        ),
        migrations.AddField(
            model_name='problemtabledata',
            name='problem',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='table_data', to='lab.problem'),
        ),
    ]
