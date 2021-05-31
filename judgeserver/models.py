from django.db import models
from problem.models import Problem
# Create your models here.


class JudgeServer(models.Model):
   STATUS_CHOICES = [
      ('normal', 'Normal'),
      ('abnormal', 'Abnormal')
   ]
   address = models.CharField(max_length=1200, unique=True)
   status = models.CharField(max_length=200, choices=STATUS_CHOICES, blank=True, null=True)
   server_name = models.CharField(max_length=600, blank=True)
   server_cpu_number = models.PositiveIntegerField(blank=True, null=True)
   server_cpu_usage = models.PositiveIntegerField(blank=True, null=True)
   server_memory_usage = models.PositiveIntegerField(blank=True, null=True)
   is_enabled = models.BooleanField(default=True)
   load = models.PositiveIntegerField(default=0)
   command_runner_version = models.CharField(max_length=400, blank=True, null=True)
   problem = models.ManyToManyField(Problem, blank=True)

   def __str__(self):
       return self.address
   