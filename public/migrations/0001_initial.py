# Generated by Django 2.0.7 on 2021-05-03 12:53

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('problem', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Statistics',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('total_submissions', models.PositiveIntegerField(default=0)),
                ('accurate_submissions', models.PositiveIntegerField(default=0)),
                ('total_users', models.PositiveIntegerField(default=0)),
                ('accurate_users', models.PositiveIntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
                ('problem', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='problem.Problem')),
            ],
        ),
    ]
