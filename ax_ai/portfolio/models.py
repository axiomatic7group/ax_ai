from django.db import models
from django.utils import timezone
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.urls import reverse

from synapse.models import user_info

alphanumeric = RegexValidator(r'^[0-9a-zA-Z ]*$', 'Only alphanumeric characters are allowed.')
phone_regex = RegexValidator(regex=r'^\+?1?\d{9,15}$',message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")

project_type_list = [
    ('open_source', 'Open Source'),
    ('research', 'Research'),
    ('client', 'Client'),
    ('propietary', 'Proprietary'),
    ('services', 'Services'),
    ('product', 'Product'),
    ('other', 'Other'),
]

class portfolio_projects(models.Model):
    date_created = models.DateField('date created', default=timezone.now)
    project_name = models.CharField(max_length=254)
    project_description = models.TextField()
    project_casestudy = models.TextField()
    project_repo_link = models.CharField(max_length=254)
    project_hero_image = models.CharField(max_length=254, blank=True, null=True)
    project_type = models.CharField(max_length=75, choices=project_type_list)

    slug = models.CharField(max_length=250, blank=True, null=True)

    def get_absolute_url(self):
        if not self.slug:
            return ""
        return reverse('service_view', kwargs={'project_id': self.slug})

class campaign(models.Model):
    date_created = models.DateField('date created', default=timezone.now)
    campaign_name = models.CharField(max_length=254, validators=[alphanumeric])
    campaign_description = models.TextField()

class campaign_funnel(models.Model):
    funnel_name = models.CharField(max_length=254, validators=[alphanumeric], unique=True)
    funnel_campaign = models.ForeignKey(campaign, on_delete=models.CASCADE)
    funnel_input_form = models.TextField(default='{"message":"placeholder"}')
    funnel_hero_img = models.CharField(max_length=350, blank=True, null=True)
    funnel_hero_md = models.CharField(max_length=350, blank=True, null=True)

    slug = models.CharField(max_length=250, blank=True, null=True)
    def get_absolute_url(self):
        if not self.slug:
            return ""
        return reverse('view_campaign_funnel_view', kwargs={'funnel_id': self.slug})


class campaign_funnel_lead(models.Model):
    date_created = models.DateTimeField('date created', default=timezone.now)
    campaign_funnel = models.ForeignKey(campaign_funnel, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=125, validators=[alphanumeric])
    last_name = models.CharField(max_length=125, validators=[alphanumeric])
    organization = models.CharField(max_length=200,)
    email = models.EmailField(max_length=254)
    phone_number = models.CharField( validators=[phone_regex], max_length=17, blank=True) 

    class Meta:
        constraints = [models.UniqueConstraint(fields=['email', 'campaign_funnel'], name='unique_email')]



class campaign_faq(models.Model):
    faq_name = models.TextField(validators=[alphanumeric], unique=True)
    faq_campaign = models.ForeignKey(campaign, on_delete=models.CASCADE)
    faq_md = models.TextField(blank=True, null=True)

    slug = models.CharField(max_length=250, blank=True, null=True)
    def get_absolute_url(self):
        if not self.slug:
            return ""
        return reverse('campaign_faq_view', kwargs={'campaign_faq_id': self.slug})
    

class campaign_blog(models.Model):
    blog_name = models.TextField(validators=[alphanumeric], unique=True)
    blog_campaign = models.ForeignKey(campaign, on_delete=models.CASCADE)
    blog_md = models.TextField(blank=True, null=True)

    slug = models.CharField(max_length=250, blank=True, null=True)
    def get_absolute_url(self):
        if not self.slug:
            return ""
        return reverse('campaign_blog_view', kwargs={'blog_post_id': self.slug})


class user_link_in_bio_info(models.Model):
    link_in_bio_desc = models.TextField(default="")
    header_img_link = models.CharField(max_length=250, blank=True, null=True)
    link_user_info = models.ForeignKey(user_info, on_delete=models.CASCADE)
    instagram_link = models.CharField(max_length=250, blank=True, null=True)
    linkedin_link = models.CharField(max_length=250, blank=True, null=True)
    youtube_link = models.CharField(max_length=250, blank=True, null=True)
    x_link = models.CharField(max_length=250, blank=True, null=True)
    substack_link = models.CharField(max_length=250, blank=True, null=True)
    github_link = models.CharField(max_length=250, blank=True, null=True)
    tiktok_link = models.CharField(max_length=250, blank=True, null=True)
    facebook_link = models.CharField(max_length=250, blank=True, null=True)
    spotify_link = models.CharField(max_length=250, blank=True, null=True)

class link_in_bio_links(models.Model):
    user_link = models.ForeignKey(user_link_in_bio_info, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    link_order = models.PositiveIntegerField()
    link = models.CharField(max_length=500)
    link_img = models.CharField(max_length=500, blank=True, null=True)
    link_desc = models.TextField(default="")


