# Generated by Django 3.2.5 on 2021-08-12 21:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lab', '0003_auto_20210810_2158'),
    ]

    operations = [
        migrations.AddField(
            model_name='problemattempt',
            name='error_text',
            field=models.TextField(blank=True, default=''),
        ),
    ]
