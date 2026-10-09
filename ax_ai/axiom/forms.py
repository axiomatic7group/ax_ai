from django.forms import ModelForm
from django import forms

from .models import *
from synapse.models import connection_function_saved_inputs, connection_functions

class model_personality_list(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f" {obj.personality_name}"

class saved_input_list_view(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f" {obj.input_value}"
    
class connection_function_list_view(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.connection_function_name}; {obj.function_type}"

class user_pm_owner_view(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.last_name}, {obj.first_name}"


class add_project_template(ModelForm):
    pm_owner = user_pm_owner_view(queryset=User.objects.all())

    class Meta:
        model = project_template
        exclude = ['date_created']
        fields = "__all__"

class add_axiom_bot_message_task(ModelForm):

    class Meta:
        model = axiom_bot_message_task
        exclude = ['date_created', "model_response", "bot_function"]
        fields = "__all__"

class buil_axiom_bot_message_task(ModelForm):

    class Meta:
        model = axiom_bot_message_task
        exclude = ['date_created', "chat_user", "task_project",]
        fields = "__all__"

class add_axiom_bot_message_saved_input(ModelForm):
    bot_saved_input = saved_input_list_view(queryset=connection_function_saved_inputs.objects.all())

    class Meta:
        model = axiom_bot_message_saved_input
        exclude = ['date_created', "model_response", "bot_personality", "bot_tool", "chat_user"]
        fields = "__all__"

class add_axiom_bot_message_connection_func(ModelForm):
    bot_function = connection_function_list_view(queryset=connection_functions.objects.all())

    class Meta:
        model = axiom_bot_message_connection_func
        exclude = ['date_created', "model_response", "bot_personality", "bot_tool", "chat_user"]
        fields = "__all__"


class add_ax_task_prerequisite(ModelForm):

    class Meta:
        model = ax_task_prerequisite
        exclude = ['date_created']
        fields = "__all__"


class AddAxTaskPrerequisiteForm(forms.ModelForm):
    def __init__(self, *args, allowed_relationships=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.allowed_relationships = allowed_relationships
        
        if self.allowed_relationships is not None:
            
            self.fields['main_task'].queryset = self.fields['main_task'].queryset.filter(id__in=allowed_relationships)
            self.fields['second_task'].queryset = self.fields['second_task'].queryset.filter(id__in=allowed_relationships)

    class Meta:
            model = ax_task_prerequisite
            exclude = ['date_created']
            fields = "__all__"


class add_ax_task_status_list(ModelForm):

    class Meta:
        model = ax_task_status_list
        exclude = ['date_created']
        fields = "__all__"

class add_project_template_schedule(ModelForm):

    run_date = forms.DateTimeField(input_formats=["%Y-%m-%dT%H:%M"], label="Run date", initial=timezone.now,
                widget=forms.DateTimeInput(format="%Y-%m-%dT%H:%M", attrs={ "type": "datetime-local", "class": "form-control"}), )

    class Meta:
        model = project_template_schedule
        exclude = ['date_created']
        fields = "__all__"


class add_internal_document(ModelForm):
    document_personality = model_personality_list(queryset=model_personality.objects.all())


    class Meta:
        model = internal_document
        exclude = ['date_created', 'document_object']
        fields = "__all__"

class add_internal_document_version(ModelForm):

    class Meta:
        model = internal_document_version
        exclude = ['date_created', 'document_version', 'internal_document',]
        fields = "__all__"