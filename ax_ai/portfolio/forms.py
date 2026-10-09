from django.forms import ModelForm
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django import forms
from django.utils.safestring import  mark_safe

from synapse.models import user_info
from .models import *

class add_new_users(ModelForm):
    organization = forms.CharField(initial=None)

    class Meta:
        model = user_info
        exclude = ['date_created', 'user', 'user_type', 'first_name', 'last_name', 'user_email']
        fields = '__all__'


class DetailedSignUpForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    email = forms.EmailField(required=True)
    agree_to_terms = forms.BooleanField(
        required=True,
        label=mark_safe(
            'I have read and agree to the <a href="/terms/" target="_blank" rel="noopener">Terms of Use</a> '
            'and acknowledge the data processing practices described in the '
            '<a href="/privacy/" target="_blank" rel="noopener">Privacy Policy</a>.'
        ),
        error_messages={
            'required': 'You must accept the Terms of Use and acknowledge the Privacy Policy to proceed.'
        }
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('first_name', 'last_name', 'email')
    
    def clean_email(self):
        """Checks if the email is already registered in the database."""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("A user with that email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.email = self.cleaned_data["email"]
        user.is_staff = False  
        
        if commit:
            user.save()
        return user

class add_new_projects(ModelForm):

    class Meta:
        model = portfolio_projects
        exclude = ['date_created', 'project_hero_image']
        fields = "__all__"


class add_new_campaign_funnel(ModelForm):

    class Meta:
        model = campaign_funnel
        fields = "__all__"



class create_new_lead_form(ModelForm):
    
    agree_to_terms = forms.BooleanField(
        required=True,
        label=mark_safe(
            'I have read and agree to the <a href="/terms/" target="_blank" rel="noopener">Terms of Use</a> '
            'and acknowledge the data processing practices described in the '
            '<a href="/privacy/" target="_blank" rel="noopener">Privacy Policy</a>.'
        ),
        error_messages={
            'required': 'You must accept the Terms of Use and acknowledge the Privacy Policy to proceed.'
        }
    )

    class Meta():
        model = campaign_funnel_lead
        exclude = ['date_created', 'campaign_funnel', ]
        fields = "__all__"
    


class add_new_campaign_faq_form(ModelForm):

    class Meta:
        model = campaign_faq
        fields = "__all__"

class add_new_campaign_blog_form(ModelForm):

    class Meta:
        model = campaign_blog
        fields = "__all__"


class add_user_link_in_bio_info_form(ModelForm):

    class Meta:
        model = user_link_in_bio_info
        exclude = ["link_user_info",]
        fields = "__all__"


class add_link_in_bio_links_form(ModelForm):

    class Meta:
        model = link_in_bio_links
        exclude = ["user_link",]
        fields = "__all__"