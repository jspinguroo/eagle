import os
import pandas as pd
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
import subprocess
import time
from datetime import datetime
import shutil

# Function to read the CSV and return a DataFrame
def read_ping_results(csv_file):
    try:
        df = pd.read_csv(csv_file)
        return df
    except Exception as e:
        print(f"Failed to read the file: {e}")
        return pd.DataFrame()

# Function to list config files
def list_config_files(config_dir):
    return [f for f in os.listdir(config_dir) if f.endswith('.json')]

# Function to read config file content
def read_config_file(config_path):
    with open(config_path, 'r') as file:
        return file.read()

# Function to save config file content
def save_config_file(config_path, content):
    with open(config_path, 'w') as file:
        file.write(content)

# Function to calculate latency statistics
def calculate_latency_stats(df):
    stats = {}
    labels = df['Label'].unique()
    for label in labels:
        subset = df[df['Label'] == label]
        min_latency = subset['Latency (ms)'].min()
        avg_latency = subset['Latency (ms)'].mean()
        max_latency = subset['Latency (ms)'].max()
        stats[label] = (min_latency, avg_latency, max_latency)
    return stats

# Global variables to store the ping script process and test start time
ping_process = None
test_start_time = None

# Main script execution
if __name__ == '__main__':
    config_dir = os.path.join(os.getcwd(), 'configs')
    results_dir = os.path.join(os.getcwd(), 'results')
    os.makedirs(results_dir, exist_ok=True)
    csv_file = os.path.join(os.getcwd(), 'ping_results.csv')

    app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY], suppress_callback_exceptions=True)
    app.index_string = '''
    <!DOCTYPE html>
    <html>
        <head>
            <title>EAGLE</title>
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css">
            <link href="https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;700&display=swap" rel="stylesheet">
            {%metas%}
            {%favicon%}
            {%css%}
        </head>
        <body>
            <div id="root">
                {%app_entry%}
            </div>
            <footer>
                {%config%}
                {%scripts%}
                {%renderer%}
            </footer>
        </body>
    </html>
    '''

    app.layout = html.Div([
        dcc.Location(id='url', refresh=False),
        html.Div(id='page-content', children=[
            html.Div([
                html.Img(src='/assets/logo.png', style={'width': '80px'}),  # Adjust the width as needed
                html.H1("EAGLE", style={'margin-left': '20px', 'color': '#00A36C', 'fontFamily': 'Roboto Mono'})
            ], style={'display': 'flex', 'align-items': 'center', 'justify-content': 'center', 'padding': '20px', 'backgroundColor': '#1E1E1E'}),  # Center logo and title

            html.Div([
                html.Div([
                    dcc.Graph(id='latency-graph')
                ], style={'padding': '20px', 'backgroundColor': '#1E1E1E', 'borderRadius': '8px', 'boxShadow': '0 4px 8px rgba(0,0,0,0.1)'}),  # Card style for graph

                html.Div(id='latency-stats-table', style={'padding': '20px', 'backgroundColor': '#1E1E1E', 'borderRadius': '8px', 'boxShadow': '0 4px 8px rgba(0,0,0,0.1)', 'marginTop': '20px'})  # Card style for table
            ], style={'margin': '40px'}),

            dcc.Interval(
                id='interval-component',
                interval=1*1000,  # Update every second
                n_intervals=0
            ),

            html.Div(id='config-action-container', children=[
                html.Div([
                    html.I(className="fas fa-file-alt", style={'margin-right': '10px', 'color': '#00A36C'}),
                    dcc.Dropdown(
                        id='config-dropdown',
                        options=[{'label': cfg, 'value': cfg} for cfg in list_config_files(config_dir)],
                        placeholder="Select a configuration file",
                        style={'width': '60%', 'backgroundColor': '#303435', 'color': 'white', 'fontFamily': 'Roboto Mono'},
                        className='dropdown-dark'
                    ),
                    html.Button([
                        html.I(className="fas fa-pen", style={'margin-right': '5px'}),
                        'Edit Config'
                    ], id='edit-config-button', n_clicks=0, style={'margin-left': '10px', 'backgroundColor': '#303435', 'color': 'white', 'fontFamily': 'Roboto Mono'}),
                    html.Button([
                        html.I(className="fas fa-play", style={'margin-right': '5px'}),
                        'Start Test'
                    ], id='start-button', n_clicks=0, style={'margin-left': '10px', 'backgroundColor': '#303435', 'color': 'white', 'fontFamily': 'Roboto Mono'}),
                    html.Button([
                        html.I(className="fas fa-stop", style={'margin-right': '5px'}),
                        'Stop Test'
                    ], id='stop-button', n_clicks=0, style={'margin-left': '10px', 'backgroundColor': '#303435', 'color': 'white', 'fontFamily': 'Roboto Mono'}),
                    html.Button([
                        html.I(className="fas fa-save", style={'margin-right': '5px'}),
                        'Save Results'
                    ], id='save-button', n_clicks=0, style={'margin-left': '10px', 'backgroundColor': '#303435', 'color': 'white', 'fontFamily': 'Roboto Mono'}),
                    html.Button([
                        html.I(className="fas fa-trash-alt", style={'margin-right': '5px'}),
                        'Clear Results'
                    ], id='clear-button', n_clicks=0, style={'margin-left': '10px', 'backgroundColor': '#303435', 'color': 'white', 'fontFamily': 'Roboto Mono'})
                ], style={'display': 'flex', 'align-items': 'center', 'justify-content': 'center', 'padding': '20px', 'backgroundColor': '#1E1E1E', 'borderRadius': '8px', 'boxShadow': '0 4px 8px rgba(0,0,0,0.1)'}),

                html.Div(id='status', style={'margin-top': '20px', 'text-align': 'center', 'color': '#00A36C', 'fontFamily': 'Roboto Mono'})
            ]),

            html.Div(id='author-container', children=[
                html.P("Author: Jon Spindler", style={'margin': '5px', 'color': '#00A36C', 'fontFamily': 'Roboto Mono'}),
                html.P("Version: 1.0.0", style={'margin': '5px', 'color': '#00A36C', 'fontFamily': 'Roboto Mono'})
            ], style={'textAlign': 'center', 'backgroundColor': '#1E1E1E'})
        ], style={'backgroundColor': '#121212', 'height': '100vh', 'position': 'relative'}),

        # Modal for editing config file
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("Edit Config File", style={'fontFamily': 'Roboto Mono'})),
            dbc.ModalBody([
                dcc.Textarea(id='config-file-editor', style={'width': '100%', 'height': '400px', 'fontFamily': 'Roboto Mono'}),
            ]),
            dbc.ModalFooter([
                html.Button('Save', id='save-config-button', n_clicks=0, style={'backgroundColor': '#303435', 'color': 'white', 'fontFamily': 'Roboto Mono'}),
                html.Button('Cancel', id='cancel-config-button', n_clicks=0, style={'backgroundColor': '#303435', 'color': 'white', 'fontFamily': 'Roboto Mono'})
            ])
        ], id='config-modal', is_open=False, centered=True),

        # Modal for saving results
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("Save Results", style={'fontFamily': 'Roboto Mono'})),
            dbc.ModalBody([
                html.Label('File Name', style={'color': 'white', 'fontFamily': 'Roboto Mono'}),
                dcc.Input(id='file-name-input', value='', style={'width': '100%', 'fontFamily': 'Roboto Mono'}),
            ]),
            dbc.ModalFooter([
                html.Button('Save', id='confirm-save-button', n_clicks=0, style={'backgroundColor': '#303435', 'color': 'white', 'fontFamily': 'Roboto Mono'}),
                html.Button('Cancel', id='cancel-save-button', n_clicks=0, style={'backgroundColor': '#303435', 'color': 'white', 'fontFamily': 'Roboto Mono'})
            ])
        ], id='modal', is_open=False),

        # Toast notification
        dbc.Toast(
            id="toast",
            header="Notification",
            is_open=False,
            duration=4000,
            style={"position": "fixed", "top": 10, "right": 10, "width": 350, 'fontFamily': 'Roboto Mono'}
        )
    ])

    @app.callback(
        Output('status', 'children'),
        Output('modal', 'is_open'),
        Output('toast', 'is_open'),
        Output('toast', 'children'),
        Output('config-modal', 'is_open'),
        Output('config-file-editor', 'value'),
        Output('latency-stats-table', 'children'),
        [Input('start-button', 'n_clicks'), Input('stop-button', 'n_clicks'), Input('confirm-save-button', 'n_clicks'), Input('save-button', 'n_clicks'), Input('cancel-save-button', 'n_clicks'), Input('clear-button', 'n_clicks'), Input('edit-config-button', 'n_clicks'), Input('save-config-button', 'n_clicks'), Input('cancel-config-button', 'n_clicks')],
        [State('config-dropdown', 'value'), State('file-name-input', 'value'), State('config-file-editor', 'value')]
    )
    def control_ping_script(start_clicks, stop_clicks, confirm_save_clicks, save_clicks, cancel_clicks, clear_clicks, edit_clicks, save_config_clicks, cancel_config_clicks, config_file, file_name, config_content):
        global ping_process, test_start_time
        ctx = dash.callback_context

        if not ctx.triggered:
            return "", False, False, "", False, "", html.Div()

        button_id = ctx.triggered[0]['prop_id'].split('.')[0]

        if button_id == 'start-button' and config_file:
            if ping_process is None or ping_process.poll() is not None:
                config_path = os.path.join(config_dir, config_file)
                print(f"Starting test with config: {config_path}")  # Debug print
                ping_process = subprocess.Popen(["python3", "ping_script.py", config_path])
                test_start_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
                time.sleep(2)  # Give some time for the script to start and create the file
                return f"Test is running with config: {config_file}", False, False, "", False, "", html.Div()

        elif button_id == 'stop-button':
            if ping_process and ping_process.poll() is None:
                print(f"Stopping test with PID: {ping_process.pid}")  # Debug print
                ping_process.terminate()
                ping_process.wait()
                ping_process = None

                if os.path.exists(csv_file):
                    df = read_ping_results(csv_file)
                    stats = calculate_latency_stats(df)
                    status_message = "Test is stopped."
                    table_header = [
                        html.Thead(html.Tr([html.Th("Transport"), html.Th("Min Latency (ms)"), html.Th("Avg Latency (ms)"), html.Th("Max Latency (ms)")]))
                    ]
                    table_body = [
                        html.Tr([
                            html.Td(label), 
                            html.Td(f"{min_latency:.2f}"), 
                            html.Td(f"{avg_latency:.2f}"), 
                            html.Td(f"{max_latency:.2f}")
                        ]) for label, (min_latency, avg_latency, max_latency) in stats.items()
                    ]
                    latency_stats_table = html.Table(table_header + [html.Tbody(table_body)], style={'color': '#00A36C', 'width': '100%', 'textAlign': 'center', 'fontFamily': 'Roboto Mono'})
                    return status_message, False, False, "", False, "", latency_stats_table
                else:
                    return "Test is stopped. No data available.", False, False, "", False, "", html.Div()

        elif button_id == 'save-button':
            return "", True, False, "", False, "", html.Div()

        elif button_id == 'cancel-save-button':
            return "", False, False, "", False, "", html.Div()

        elif button_id == 'confirm-save-button' and file_name:
            destination_file = os.path.join(results_dir, f"{file_name}.csv")
            shutil.copyfile(csv_file, destination_file)
            print(f"Saving results as {file_name}.csv")  # Debug print
            return f"Results saved as {file_name}.csv in /results directory.", False, True, f"Results saved as {file_name}.csv", False, "", html.Div()

        elif button_id == 'clear-button':
            if os.path.exists(csv_file):
                os.remove(csv_file)  # Delete the file
                print("ping_results.csv deleted.")  # Debug print
            return "Results cleared.", False, True, "Results have been cleared.", False, "", html.Div()

        elif button_id == 'edit-config-button' and config_file:
            config_path = os.path.join(config_dir, config_file)
            config_content = read_config_file(config_path)
            return "", False, False, "", True, config_content, html.Div()

        elif button_id == 'save-config-button' and config_file:
            config_path = os.path.join(config_dir, config_file)
            save_config_file(config_path, config_content)
            return "Config file saved.", False, True, "Config file has been saved.", False, "", html.Div()

        elif button_id == 'cancel-config-button':
            return "", False, False, "", False, "", html.Div()

        return "", False, False, "", False, "", html.Div()

    @app.callback(
        Output('file-name-input', 'value'),
        [Input('save-button', 'n_clicks')]
    )
    def update_file_name_input(save_clicks):
        if save_clicks:
            return test_start_time
        return ''

    @app.callback(
        Output('latency-graph', 'figure'),
        [Input('interval-component', 'n_intervals')]
    )
    def update_graph_live(n):
        if os.path.exists(csv_file):
            df = read_ping_results(csv_file)
            figure = {
                'data': [
                    {
                        'x': df[(df['DSCP'] == dscp) & (df['Label'] == label)]['Timestamp'],
                        'y': df[(df['DSCP'] == dscp) & (df['Label'] == label)]['Latency (ms)'],
                        'name': f'{label} (DSCP {dscp})',
                        'type': 'line'
                    } for dscp, label in df[['DSCP', 'Label']].drop_duplicates().itertuples(index=False)
                ],
                'layout': {
                    'title': 'SD-WAN Black Transport Performance',
                    'xaxis': {'title': 'Time', 'color': '#00A36C', 'fontFamily': 'Roboto Mono'},
                    'yaxis': {'title': 'Latency (ms)', 'color': '#00A36C', 'fontFamily': 'Roboto Mono'},
                    'plot_bgcolor': '#1E1E1E',
                    'paper_bgcolor': '#1E1E1E',
                    'font': {'color': '#00A36C', 'family': 'Roboto Mono'}
                }
            }
            return figure
        else:
            return {
                'data': [],
                'layout': {
                    'title': 'SD-WAN Black Transport Performance',
                    'xaxis': {'title': 'Time', 'color': '#00A36C', 'fontFamily': 'Roboto Mono'},
                    'yaxis': {'title': 'Latency (ms)', 'color': '#00A36C', 'fontFamily': 'Roboto Mono'},
                    'plot_bgcolor': '#1E1E1E',
                    'paper_bgcolor': '#1E1E1E',
                    'font': {'color': '#00A36C', 'family': 'Roboto Mono'}
                }
            }

    app.run_server(debug=True, host='0.0.0.0')
