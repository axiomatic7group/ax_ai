from django.forms import ModelForm
from django.core.exceptions import ValidationError
from django import forms
from django.forms.widgets import DateInput

from .models import *
from synapse.models import user_info


class delete_project_f(ModelForm):

    class Meta:
        model = project
        exclude = ['date_created', 'pm_owner', 'project_description']
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        # Pop the user from the kwargs
        user = kwargs.pop('user', None) 
        super().__init__(*args, **kwargs)
        
        # Filter the queryset for the specific field based on the user
        if user:
            if not user.is_superuser:
                self.fields['pm_owner'].queryset = user_info.objects.filter(user_id=user.id)

class create_new_projects(ModelForm):

    class Meta:
        model = project
        exclude = ['date_created']
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if user_info.objects.filter(user_type='staff').exists():
            self.fields['pm_owner'].queryset = user_info.objects.filter(user_type='staff')
        else:
            self.fields['pm_owner'].queryset = user_info.objects.all()

class new_deliverable_frm(ModelForm):
    start_date = forms.DateField(
        widget=DateInput(attrs={'type': 'date'}),
    )

    class Meta:
        model = deliverable
        exclude = ['date_created',]
        fields = '__all__'

class create_new_tasks(ModelForm):

    task_description = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 5, 'cols': 40})
    )

    class Meta:
        model = task
        exclude = ['date_created',]
        fields = '__all__'

class add_staff_to_task(ModelForm):
    class Meta:
        model = task_staff
        exclude = ['date_created',]
        fields = '__all__'

class add_stakeholder_to_deliverable(ModelForm):
    class Meta:
        model = deliverable_stakeholder
        exclude = ['date_created',]
        fields = '__all__'

class create_project_group(ModelForm):
    class Meta:
        model = project_group
        exclude = ['date_created',]
        fields = '__all__'

class create_deliverable_group(ModelForm):
    class Meta:
        model = deliverable_group
        exclude = ['date_created',]
        fields = '__all__'

class create_project_grouping(ModelForm):
    class Meta:
        model = project_grouping
        fields = '__all__'

class create_deliverable_grouping(ModelForm):
    class Meta:
        model = deliverable_grouping
        fields = '__all__'

class add_task_comments(ModelForm):
    class Meta:
        model = task_comments
        exclude = ['datetime_created', 'task_comment_owner', 'task_comment_type', 'comment_task']
        fields = '__all__'

class add_task_attachement(ModelForm):
    class Meta:
        model = task_attachement
        exclude = ['datetime_created', 'attachemnet_task', 'attachemnet', 'attachemnet_owner']
        fields = '__all__'

class add_task_prerequisite(ModelForm):
    class Meta:
        model = task_prerequisite
        exclude = ['date_created',]
        fields = '__all__'

class add_user_messages(ModelForm):
    class Meta:
        model = user_messages
        exclude = ['date_created', 'message_warning_level', 'message_sender']
        fields = '__all__'

class add_task_status_list(ModelForm):
    class Meta:
        model = task_status_list
        exclude = ['date_created',]
        fields = '__all__'



class add_stakeholder_to_project(ModelForm):
    class Meta:
        model = project_stakeholder
        exclude = ['date_created',]
        fields = '__all__'


"""

### For Beta ###

class add_task_comments_super(ModelForm):
    class Meta:
        model = task_comments
        exclude = ['date_created',]
        fields = '__all__'

class add_task_attachement_super(ModelForm):
    class Meta:
        model = task_attachement
        exclude = ['date_created',]
        fields = '__all__'

"""