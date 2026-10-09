
from django.urls import get_resolver, URLPattern, URLResolver, resolve
from django.core.management.base import BaseCommand, CommandError
import pandas as pd



def all_url_patterns(url_patterns=None, namespace=""):
    all_url_patterns_output = pd.DataFrame()

    if url_patterns is None:
        url_patterns = get_resolver().url_patterns

    for pattern in url_patterns:
        if isinstance(pattern, URLPattern):
            # Format the view name nicely
            view_name = f"{pattern.callback.__module__}.{pattern.callback.__name__}"

            temp_dict = {"link":[f"{namespace}{pattern.pattern}"], "name":[pattern.name], "function_type":[view_name]}

            new_row_df = pd.DataFrame(temp_dict)

            all_url_patterns_output = pd.concat([new_row_df, all_url_patterns_output], ignore_index=True)
              
        elif isinstance(pattern, URLResolver):

            new_row_df = all_url_patterns(pattern.url_patterns, namespace=f"{namespace}{pattern.pattern}")

            all_url_patterns_output = pd.concat([new_row_df, all_url_patterns_output], ignore_index=True)
    
    all_url_patterns_output['function'] = all_url_patterns_output['function_type'].str.split(".").str[0]
    
    return all_url_patterns_output

def get_url_by_app_dropdown(url_patterns_df):
    if isinstance(url_patterns_df, pd.DataFrame):
        columns_to_have = ['function', 'function_type', 'link', 'name']
        if  url_patterns_df.columns.isin(columns_to_have).all():
            url_ptrns_df_to_use = url_patterns_df[url_patterns_df['function']!='django']
            url_ptrns_df_to_use = url_ptrns_df_to_use[~url_ptrns_df_to_use['link'].str.contains('api')]
            url_ptrns_df_to_use = url_ptrns_df_to_use[~url_ptrns_df_to_use['link'].str.contains('slug')]
            url_ptrns_df_to_use['name_clean'] = url_ptrns_df_to_use['name'].str.replace("_html", "").str.replace("_", " ")
            url_ptrns_df_to_use['a_link'] = "<li><a class=\"dropdown-item\" href=\"/" +url_ptrns_df_to_use['link'] +"\">"+url_ptrns_df_to_use['name_clean']+"</a></li>"
                
            list_of_apps = url_ptrns_df_to_use['function'].unique()
            output_line_all = ''
            for count_app_group, app_group in enumerate(list_of_apps):
                if app_group != 'django':
                    temp_group_list = url_ptrns_df_to_use[url_ptrns_df_to_use['function']==app_group]

                    with pd.option_context('display.max_colwidth', None):
                        output_line = '<li class="nav-item dropdown">' + f'<a class="nav-link dropdown-toggle" href="#" id="navbar{str(app_group)}" role="button" data-bs-toggle="dropdown" aria-expanded="false">' + str(app_group) + '</a>' + f'<ul class="dropdown-menu" aria-labelledby="navbar{str(app_group)}">' + temp_group_list['a_link'].to_string(index=False) + '</ul></li>'
                        output_line_all = output_line_all + "/n" + output_line

            
            with open('test.html', 'w') as file:
                file.write(output_line_all)
            
        else:
            return 'error'
    else:
        return 'error'
                    
        


    
class Command(BaseCommand):
    def handle(self, *args, **options):
        temp_x = all_url_patterns()
        get_url_by_app_dropdown(temp_x)
        #print(temp_x[temp_x['function']!='django'])
