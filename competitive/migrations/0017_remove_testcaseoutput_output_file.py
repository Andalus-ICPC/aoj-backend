# Generated by Django 2.0.7 on 2021-04-27 16:38

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('competitive', '0016_auto_20210427_1637'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='testcaseoutput',
            name='output_file',
        ),
    ]
