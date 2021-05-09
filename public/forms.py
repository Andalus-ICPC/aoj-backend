from django import forms
from competitive.models import Submit
from control.models import Setting


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


class SubmitSpecificProblem(forms.ModelForm):
    specific_problem = forms.CharField(
        label="Problem",
        widget=forms.TextInput(attrs={'readonly': True}),
    )
    class Meta:
        model = Submit
        fields = [ 'specific_problem', 'language', 'submit_file']

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

class SubmitSpecificProblemWithEditor(forms.Form):
    
    source = forms.CharField(widget=forms.Textarea) 
    specific_problem = forms.CharField(
        label="Problem",
        widget=forms.TextInput(attrs={'readonly': True}),
    )
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
    