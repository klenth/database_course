# Generated by Django 3.2 on 2021-04-15 03:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lab', '0008_auto_20210414_2253'),
    ]

    operations = [
        migrations.AddField(
            model_name='problem',
            name='schema_status',
            field=models.CharField(choices=[('M', 'Missing'), ('P', 'Processing'), ('V', 'Valid'), ('I', 'Invalid')], default='M', max_length=1),
        ),
        migrations.AddField(
            model_name='problem',
            name='validation_token',
            field=models.UUIDField(blank=True, default='5f9e53fa-9d97-11eb-a842-0cdd241b97c0'),
        ),
    ]
