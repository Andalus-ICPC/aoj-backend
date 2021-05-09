from django import forms
from .models import Submit, Language
from problem.models import Problem
from control.models import Setting

# from django_ace import AceWidget


class SubmitAnswer(forms.ModelForm):
    class Meta:
        model = Submit
        fields = ['problem', 'language', 'submit_file']

    def clean(self):
        cleaned_data = super().clean()
        submit_file_size = cleaned_data.get('submit_file').size # it is in byte
        submit_file_size /= 1024.0

        try:
            max_source_size = Setting.objects.get(name="source code size").value
        except Setting.DoesNotExist:
            max_source_size = 256

        if submit_file_size > max_source_size:
            raise forms.ValidationError("submission file may not exceed 256 kilobytes.")


class SubmitWithEditor(forms.Form):
    source = forms.CharField(widget=forms.Textarea) 
    problem = forms.ChoiceField(widget=forms.Select)
    language =  forms.ChoiceField(widget=forms.Select)

    def clean(self):
        cleaned_data = super().clean()
        submit_file_size = len(cleaned_data.get('source').encode('utf-8')) # it is in byte
        submit_file_size /= 1024.0

        try:
            max_source_size = Setting.objects.get(name="source code size").value
        except Setting.DoesNotExist:
            max_source_size = 256

        if submit_file_size > max_source_size:
            raise forms.ValidationError("submission file may not exceed %d kilobytes." %max_source_size)
    


