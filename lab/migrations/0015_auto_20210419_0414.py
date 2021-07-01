# Generated by Django 3.2 on 2021-04-19 04:14

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('lab', '0014_auto_20210418_2042'),
    ]

    operations = [
        migrations.AlterField(
            model_name='attemptresults',
            name='attempt',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='results', to='lab.problemattempt'),
        ),
        migrations.AlterField(
            model_name='attemptresults',
            name='test_case',
            field=models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, related_name='+', to='lab.problemtestcase'),
        ),
        migrations.AddConstraint(
            model_name='attemptresults',
            constraint=models.UniqueConstraint(fields=('attempt', 'test_case'), name='attempt_results_unique'),
        ),
    ]
