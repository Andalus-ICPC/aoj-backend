# Generated by Django 2.0.7 on 2021-04-27 16:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('competitive', '0012_auto_20210427_1601'),
    ]

    operations = [
        migrations.AlterField(
            model_name='testcaseoutput',
            name='output_file',
            field=models.FilePathField(path='/home/andalus'),
        ),
    ]
