# Generated by Django 3.2 on 2021-04-18 20:42

from django.db import migrations, models
import django.db.models.deletion
import pathlib


class Migration(migrations.Migration):

    dependencies = [
        ('lab', '0013_auto_20210418_0154'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='problemonlab',
            options={'ordering': ('problem_number',), 'verbose_name': 'Problem on lab', 'verbose_name_plural': 'Problems on labs'},
        ),
        migrations.AlterModelOptions(
            name='problemschema',
            options={'verbose_name': 'Problem schema', 'verbose_name_plural': 'Problem schemata'},
        ),
        migrations.AlterModelOptions(
            name='problemtabledata',
            options={'ordering': ('data_filename',), 'verbose_name': 'Problem table data', 'verbose_name_plural': 'Problem table data'},
        ),
        migrations.AlterModelOptions(
            name='problemtestcasetabledata',
            options={'ordering': ('table_name',), 'verbose_name': 'Problem test case table data', 'verbose_name_plural': 'Problem test case table data'},
        ),
        migrations.AddField(
            model_name='problemtestcase',
            name='result_data_file',
            field=models.FileField(default=None, null=True, upload_to=pathlib.PurePosixPath('/home/kathy/PycharmProjects/sql_lab/upload')),
        ),
        migrations.CreateModel(
            name='AttemptResults',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data_file', models.FileField(upload_to=pathlib.PurePosixPath('/home/kathy/PycharmProjects/sql_lab/upload'))),
                ('attempt', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='lab.problemattempt')),
                ('test_case', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, to='lab.problemtestcase')),
            ],
            options={
                'ordering': ('test_case__number',),
            },
        ),
    ]
