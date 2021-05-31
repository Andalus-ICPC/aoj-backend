# Generated by Django 2.0.7 on 2021-05-03 12:52

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('problem', '__first__'),
        ('contest', '__first__'),
    ]

    operations = [
        migrations.CreateModel(
            name='Clarification',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('question', models.TextField()),
                ('answer', models.TextField()),
                ('send_time', models.DateTimeField()),
                ('is_public', models.BooleanField(default=False)),
                ('status', models.BooleanField(default=False)),
                ('contest', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contest.Contest')),
                ('problem', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='problem.Problem')),
                ('user', models.ForeignKey(blank=True, limit_choices_to={'role__short_name': 'contestant'}, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
