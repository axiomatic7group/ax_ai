from django.forms import ModelForm
from django.core.exceptions import ValidationError
from django import forms
from django.forms.widgets import DateInput

from .models import *
from django.contrib.auth.models import User 


### model_intiate
### model_chats
### chat_messages

class model_base_list_view(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.model_base_name}"

class models_list_view(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f" {obj.model_name} - {obj.model_base.model_base_name}"

class model_chats_list_view(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f" {obj.chat_title} - {obj.model_name}"


class create_model_intiate_form(ModelForm):
    model_connection_name = models_list_view(queryset=model_connection.objects.all())
    
    class Meta:
        model = model_intiate
        exclude = ['date_created']
        fields = '__all__'

class create_model_chats_form(ModelForm):
    model_connection_name = models_list_view(queryset=model_connection.objects.all())
    
    class Meta:
        model = model_chats
        exclude = ['date_created', 'chat_type', 'chat_user' ]
        fields = '__all__'

class create_chat_messages_form(ModelForm):
    chat_message = forms.CharField( label="", widget=forms.Textarea(attrs={'placeholder': 'what can I help you with today :)'}))
    
    class Meta:
        model = chat_messages
        exclude = ['date_created', 'message_model_chats', 'chat_sender', 'chat_meta']
        fields = '__all__'

class create_model_personality_form(ModelForm):
    
    class Meta:
        model = model_personality
        exclude = ['date_created', 'personality_type',]
        fields = '__all__'

class create_model_base_form(ModelForm):
    class Meta:
        model = model_base
        exclude = ['date_created', ]
        fields = '__all__'

class create_model_base_user_connection_form(ModelForm):
    model_api_key = forms.CharField(widget=forms.PasswordInput, required=False)
    model_base = model_base_list_view(queryset=model_base.objects.all())
    
    class Meta:
        model = model_base_user_connection
        exclude = ['date_created', 'chat_user', '_model_api_key',]
        fields = '__all__'

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.model_api_key = self.cleaned_data["model_api_key"]
        if commit:
            instance.save()
        return instance

class create_model_connection_form(ModelForm):
    model_base = model_base_list_view(queryset=model_base.objects.all())
    
    class Meta:
        model = model_connection
        exclude = ['date_created']
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        user = User.objects.get(username=user)
        user_base_connections = model_base_user_connection.objects.filter(chat_user=user)
        
        self.fields['model_base'].queryset = model_base.objects.filter(id__in=user_base_connections.values_list('model_base_id', flat=True))


#model_base
    
