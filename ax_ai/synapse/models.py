from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.db.models import Q, CheckConstraint
from django.core.exceptions import ValidationError
from django.core import signing
from django.core.validators import RegexValidator


user_type = [
    ('staff', 'staff'),
    ('stakeholder', 'stakeholder'),
    ('other', 'other'),
]

database_type = [
    ('postgres', 'postgres'),
    ('sqlite', 'sqlite'),
    ('other', 'other'),
]

datatable_type = [
    ('data', 'data'),
    ('mapping', 'mapping'),
    ('other', 'other'),
]

function_type = [
    ('data', 'data'),
    ('mapping', 'mapping'),
    ('action', 'action'),
    ('other', 'other'),
]

data_type = [
    ('numeric', 'numeric'),
    ('date', 'date'),
    ('string', 'string'),
    ('other', 'other'),
]

local_file_type = [
    ('xlsx', 'xlsx'),
    ('csv', 'csv'),
    ('other', 'other'),
]

local_function_type = [
    ('xlsx', 'xlsx'),
    ('python', 'python'),
    ('other', 'other'),
]

phone_regex = RegexValidator(regex=r'^\+?1?\d{9,15}$', message="Phone number must be entered in the format: '+999999999'.")

class user_info(models.Model):
    date_created = models.DateTimeField('date created', default=timezone.now)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    user_email = models.EmailField(max_length=254, unique=True)
    user_type = models.CharField(max_length=25, choices=user_type, default='other')
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    organization = models.CharField(max_length=200, default='internal')
    phone_number = models.CharField(validators=[phone_regex], max_length=17, blank=True, null=True)

class database_connection(models.Model):
    date_created = models.DateTimeField('date created', default=timezone.now)
    database_type = models.CharField(max_length=25, choices=database_type)
    database_url = models.CharField(max_length=250)
    database_port = models.CharField(max_length=250, default='5432')
    database_name = models.CharField(max_length=250, default='')

class database_user_connection(models.Model):
    user_connection = models.ForeignKey(user_info, on_delete=models.CASCADE, unique=False)
    connection_to_db = models.ForeignKey(database_connection, on_delete=models.CASCADE, unique=False)
    db_username = models.CharField(max_length=250)
    _db_password = models.CharField(max_length=250, db_column='db_password')

    def __init__(self, *args, **kwargs):
        pw = kwargs.pop('db_password', None)
        super().__init__(*args, **kwargs)
        if pw:
            self.db_password = pw 

    @property
    def db_password(self):
        if not self._db_password:
            return self._db_password
        try:
            return signing.loads(self._db_password)
        except signing.BadSignature:
            return None
    
    @db_password.setter
    def db_password(self, value):
        if value:
            self._db_password = signing.dumps(value)
        else:
            self._db_password = ''
        
class datatable_connection(models.Model):
    user_db_connection = models.ForeignKey(database_user_connection, on_delete=models.CASCADE, unique=False)
    datatable_name = models.CharField(max_length=250)
    databale_type = models.CharField(max_length=25, choices=datatable_type, default='data')

class api_connection(models.Model):
    user_connection = models.ForeignKey(user_info, on_delete=models.CASCADE, unique=False)
    api_base_url = models.CharField(max_length=250, unique=True)
    api_headers = models.TextField(default='')
    api_username = models.CharField(max_length=250, default='')
    _api_password = models.CharField(max_length=250, blank=True, null=True, db_column='api_password')
    _api_key = models.CharField(max_length=250, blank=True, null=True, db_column='api_key')

    class Meta:
        constraints = [
            CheckConstraint( condition = Q(_api_password=None) | Q(_api_key=None), name='at_least_1_non_null_api',),
            CheckConstraint(condition = Q(_api_password=None) | Q(_api_key=None), name='at_least_1_null_api',),]

    @property
    def api_password(self):
        if not self._api_password:
            return ""
        try:
            return signing.loads(self._api_password)
        except signing.BadSignature:
            return ""

    @api_password.setter
    def api_password(self, value):
        self._api_password = signing.dumps(value) if value else None
    
    @property
    def api_key(self):
        if not self._api_key:
            return ""
        try:
            return signing.loads(self._api_key)
        except signing.BadSignature:
            return ""
        
    @api_key.setter
    def api_key(self, value):
        self._api_key = signing.dumps(value) if value else None

class connection_functions(models.Model):
    connection_function_name = models.CharField(max_length=50)
    function_type = models.CharField(max_length=25, choices=function_type, default='data')
    function_extension = models.CharField(max_length=250)
    function_input_values_schema = models.CharField(max_length=2500)
    function_output_type = models.CharField(max_length=250, default='', blank=True)
    function_output_extensions = models.CharField(max_length=250, default='', blank=True)

    connection_to_datable = models.ForeignKey(datatable_connection, on_delete=models.CASCADE, blank=True, null=True)
    connection_to_api = models.ForeignKey(api_connection, on_delete=models.CASCADE, blank=True, null=True)
    class Meta:
        constraints = [
            CheckConstraint( condition = Q(connection_to_datable=None) | Q(connection_to_api=None), name='at_least_1_non_null_con',),
            CheckConstraint(condition = Q(connection_to_datable=None) | Q(connection_to_api=None), name='at_least_1_null_con',),]

class datatable_groups(models.Model):
    datatable_group = models.CharField(max_length=250, unique=True)

class dictionary_keys(models.Model):
    datatable_group = models.ForeignKey(datatable_groups, on_delete=models.CASCADE, blank=True)
    unique_key = models.CharField(max_length=250, unique=True)
    unique_key_desc = models.CharField(max_length=2500, unique=True)

class datatable_dictionary(models.Model):
    data_type = models.CharField(max_length=25, choices=data_type)
    dictionary_key = models.ForeignKey(dictionary_keys, on_delete=models.CASCADE, blank=True, null=True)
    dictionary_table_key = models.CharField(max_length=250, default='', blank=True, null=True)
    data_value_column = models.CharField(max_length=250)
    data_connection_function = models.ForeignKey(connection_functions, on_delete=models.CASCADE, limit_choices_to={'function_type__in': ['data', 'mapping']})

class local_data_files(models.Model):
    user_connection = models.ForeignKey(user_info, on_delete=models.CASCADE, unique=False, default=1)
    local_file_type = models.CharField(max_length=25, choices=local_file_type)
    local_file_path = models.CharField(max_length=250)
    local_file_path_old = models.CharField(max_length=250, default='', blank=True, null=True)
    local_file_name = models.CharField(max_length=250, default='')
    local_file_sheet = models.CharField(max_length=250, default='', blank=True, null=True)
    local_file_header = models.CharField(max_length=250, default='0', blank=True, null=True)
    local_file_repeat = models.BooleanField(default=False)

class local_function_files(models.Model):
    user_connection = models.ForeignKey(user_info, on_delete=models.CASCADE, unique=False, default=1)
    local_function_type = models.CharField(max_length=25, choices=local_function_type)
    local_function_path = models.CharField(max_length=250)
    local_function_name = models.CharField(max_length=250)
    function_input_values_schema = models.CharField(max_length=2500, default='')

class connection_function_saved_inputs(models.Model):
    user_connection = models.ForeignKey(user_info, on_delete=models.CASCADE, unique=False, default=1)
    input_mapping = models.ForeignKey(dictionary_keys, on_delete=models.CASCADE, blank=True, null=True)
    input_value = models.CharField(max_length=2500)
    input_value_name = models.CharField(max_length=250)
    input_value_description = models.CharField(max_length=500, default='')



class input_value_to_connections_function(models.Model):
    input_connection_function = models.ForeignKey(connection_functions, on_delete=models.CASCADE)
    input_value = models.ForeignKey(connection_function_saved_inputs, on_delete=models.CASCADE)
    user_connection = models.ForeignKey(user_info, on_delete=models.CASCADE, unique=False, default=1)


