# Generated by Django 2.0.7 on 2021-05-03 16:19

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('competitive', '0002_auto_20201113_2144'),
    ]

    operations = [
        migrations.AlterField(
            model_name='submit',
            name='server',
            field=models.ForeignKey(limit_choices_to={'is_enabled': True}, on_delete=django.db.models.deletion.CASCADE, to='judgeserver.JudgeServer'),
        ),
    ]