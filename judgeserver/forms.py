from django import forms
from django.forms import ChoiceField
from .models import JudgeServer
from problem.models import Problem
from django.utils import timezone
from datetime import datetime
from django.contrib.admin.widgets import FilteredSelectMultiple
from datetimewidget.widgets import DateTimeWidget
from authentication.models import User



class AddJudgeserver(forms.ModelForm):
   class Meta:
      model = JudgeServer
      fields = ['address', 'is_enabled', 'problem']

      widgets = {
            'problem': FilteredSelectMultiple(('tags'), is_stacked=True,)
      }
