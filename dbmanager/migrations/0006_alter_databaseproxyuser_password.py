# Generated by Django 3.2.5 on 2021-07-13 20:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dbmanager', '0005_auto_20210703_2125'),
    ]

    operations = [
        migrations.AlterField(
            model_name='databaseproxyuser',
            name='password',
            field=models.CharField(default='R1SyvYyO2r5gFoBxLYZZCdDTN7HhJ8tX7QRE5PZwetfO3C1JkyYHItonYBVdkwpB', max_length=64),
        ),
    ]