import dash
from dash import dcc, html, Input, Output
import pandas as pd
import plotly.express as px
from django.core.management.base import BaseCommand

    


# 1. Initialize the App
app = dash.Dash(__name__)

# Dummy Data
data = pd.DataFrame({
    "Product": ["Laptops", "Phones", "Tablets", "Laptops", "Phones", "Tablets"],
    "Region": ["North", "North", "North", "South", "South", "South"],
    "Sales": [15000, 12000, 7000, 18000, 9000, 5000]
})

# 2. App Layout (HTML-like components)
app.layout = html.Div([
    html.H1("Dynamic Dashboard"),
    
    dcc.Dropdown(
        id='region-dropdown',
        options=[{'label': r, 'value': r} for r in data['Region'].unique()],
        value='North'  # Default value
    ),
    
    dcc.Graph(id='sales-graph', config={'displaylogo': False,})

    ])

# 3. Callbacks to Connect Dropdown Input to Graph Output
@app.callback(
    Output('sales-graph', 'figure'),
    Input('region-dropdown', 'value')
)
def update_graph(selected_region, **kwargs):  # <--- Added **kwargs here
    filtered_data = data[data["Region"] == selected_region]
    fig = px.bar(filtered_data, x="Product", y="Sales")
    fig.update_layout(
        plot_bgcolor='white',   # Dark gray inside the plot
        paper_bgcolor='aqua',  # Even darker gray around the plot
        font_color='black'        # Makes labels visible on dark backgrounds
        )
    return fig

# 4. Run the Server

class Command(BaseCommand):
    def handle(self, *args, **options):
        app.run(debug=True, dev_tools_ui=False)
