# Generated by Django 2.0.7 on 2021-04-07 14:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('problem', '0001_initial'),
        ('judgeserver', '0006_auto_20210401_1431'),
    ]

    operations = [
        migrations.AddField(
            model_name='judgeserver',
            name='problem',
            field=models.ManyToManyField(blank=True, to='problem.Problem'),
        ),
    ]
