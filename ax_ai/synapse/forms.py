from django.forms import ModelForm
from django import forms
from django.forms.widgets import DateInput

from .models import *
from django.contrib.auth.models import User 


class input_value_for_input_value_conn(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f" {obj.input_value} , - {obj.input_value_name}"

class input_conn_for_input_value_conn(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f" {obj.connection_function_name} , - {obj.function_type}"

class input_mapping_for_saved_input_func(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f" {obj.unique_key}"

class dictionary_keys_for_datatable_dict(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f" {obj.unique_key} , - {obj.datatable_group};"

class datatable_group_to_dict_key(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f" {obj.datatable_group};"

class datatable_connection_to_conn_func(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f" {obj.datatable_name} , - {obj.user_db_connection.user_connection.first_name};"


class api_connection_to_conn_func(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f" {obj.api_base_url} , - {obj.user_connection.first_name};"

class connection_to_db_to_datatable_conn(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f" {obj.connection_to_db.database_url} ;"

class add_new_users(ModelForm):
    class Meta:
        model = user_info
        exclude = ['date_created', 'user', 'organization', 'phone_number']
        fields = '__all__'

class create_database_connection(ModelForm):
    class Meta:
        model = database_connection
        exclude = ['date_created',]
        fields = '__all__'

class create_database_user_connection(ModelForm):
    db_password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = database_user_connection
        exclude = ['_db_password',] 
        fields = '__all__'
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.db_password = self.cleaned_data["db_password"]
        if commit:
            instance.save()
        return instance
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        user = User.objects.get(username=user)
        
        self.fields['user_connection'].queryset = user_info.objects.filter(user=user)

class create_datatable_connection(ModelForm):
    user_db_connection = connection_to_db_to_datatable_conn(queryset=database_user_connection.objects.all())

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        user = User.objects.get(username=user)
        request_user = user_info.objects.get(user=user)
        
        self.fields['user_db_connection'].queryset = database_user_connection.objects.filter(user_connection=request_user)

    class Meta:
        model = datatable_connection
        fields = '__all__'

class create_api_connection(ModelForm):
    api_username = forms.CharField(required=False)
    api_password = forms.CharField(widget=forms.PasswordInput, required=False)
    api_key = forms.CharField(widget=forms.PasswordInput, required=False)

    class Meta:
        model = api_connection
        exclude = ['_api_password', '_api_key']
        fields = '__all__'
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.api_password = self.cleaned_data["api_password"]
        instance.api_key = self.cleaned_data["api_key"]
        if commit:
            instance.save()
        return instance
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        user = User.objects.get(username=user)
        
        self.fields['user_connection'].queryset = user_info.objects.filter(user=user)

class create_connection_functions(ModelForm):
    connection_to_datable = datatable_connection_to_conn_func(queryset=datatable_connection.objects.all())
    connection_to_api = api_connection_to_conn_func(queryset=api_connection.objects.all())
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        user = User.objects.get(username=user)
        request_user = user_info.objects.get(user=user)
        user_database_connections = database_user_connection.objects.filter(user_connection=request_user)
        
        self.fields['connection_to_datable'].queryset = datatable_connection.objects.filter(user_db_connection__in=user_database_connections)
        self.fields['connection_to_api'].queryset = api_connection.objects.filter(user_connection=request_user)
        self.fields['connection_to_datable'].required = False
        self.fields['connection_to_api'].required = False

    class Meta:
        model = connection_functions
        fields = '__all__'

class create_datatable_groups(ModelForm):

    class Meta:
        model = datatable_groups
        fields = '__all__'

class create_dictionary_keys(ModelForm):
    datatable_group = datatable_group_to_dict_key(queryset=datatable_groups.objects.all())

    class Meta:
        model = dictionary_keys
        fields = '__all__'



class create_datatable_dictionary(ModelForm):
    data_connection_function = input_conn_for_input_value_conn(queryset=connection_functions.objects.all())
    dictionary_key = dictionary_keys_for_datatable_dict(queryset=dictionary_keys.objects.all())


    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        user = User.objects.get(username=user)
        request_user = user_info.objects.get(user=user)
        user_database_connections = database_user_connection.objects.filter(user_connection=request_user)
        user_datatables = datatable_connection.objects.filter(user_db_connection__in=user_database_connections)
        user_api_connection = api_connection.objects.filter(user_connection=request_user)
        
        all_users_functions = connection_functions.objects.filter(
                        Q(connection_to_datable__in=user_datatables) | 
                        Q(connection_to_api__in=user_api_connection),
                        
                        function_type="data"
                    ).distinct()
        self.fields['data_connection_function'].queryset = all_users_functions

    class Meta:
        model = datatable_dictionary
        fields = '__all__'

#data_connection_function

class create_local_data_files(ModelForm):

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        user = User.objects.get(username=user)
        
        self.fields['user_connection'].queryset = user_info.objects.filter(user=user)

    class Meta:
        model = local_data_files
        fields = '__all__'

class create_local_function_files(ModelForm):

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        user = User.objects.get(username=user)
        
        self.fields['user_connection'].queryset = user_info.objects.filter(user=user)

    class Meta:
        model = local_function_files
        fields = '__all__'



class create_connection_function_saved_inputs(ModelForm):
    input_mapping = input_mapping_for_saved_input_func(queryset=dictionary_keys.objects.all())

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        user = User.objects.get(username=user)
        request_user = user_info.objects.get(user=user)
        user_database_connections = database_user_connection.objects.filter(user_connection=request_user)
        user_datatables = datatable_connection.objects.filter(user_db_connection__in=user_database_connections)
        user_api_connection = api_connection.objects.filter(user_connection=request_user)
        
        all_users_functions = connection_functions.objects.filter(connection_to_datable__in=user_datatables) | connection_functions.objects.filter(connection_to_api__in=user_api_connection)
        self.fields['user_connection'].queryset = user_info.objects.filter(user=user)

    class Meta:
        model = connection_function_saved_inputs
        fields = '__all__'




class create_input_value_to_connections_function(ModelForm):
    input_value = input_value_for_input_value_conn(queryset=connection_function_saved_inputs.objects.all())
    input_connection_function = input_conn_for_input_value_conn(queryset=connection_functions.objects.all())

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        user = User.objects.get(username=user)
        request_user = user_info.objects.get(user=user)
        user_database_connections = database_user_connection.objects.filter(user_connection=request_user)
        user_datatables = datatable_connection.objects.filter(user_db_connection__in=user_database_connections)
        user_api_connection = api_connection.objects.filter(user_connection=request_user)
        
        self.fields['input_connection_function'].queryset = connection_functions.objects.filter(connection_to_datable__in=user_datatables) | connection_functions.objects.filter(connection_to_api__in=user_api_connection)
        self.fields['user_connection'].queryset = user_info.objects.filter(user=user)

    class Meta:
        model = input_value_to_connections_function
        fields = '__all__'