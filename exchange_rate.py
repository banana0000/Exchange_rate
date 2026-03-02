import dash
from dash import dcc, html
from dash.dependencies import Output, Input
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
import yfinance as yf
from datetime import timedelta

PAIRS = {
    "EUR/HUF": "EURHUF=X",
    "USD/HUF": "USDHUF=X",
    "GBP/HUF": "GBPHUF=X",
}

COLORS = {
    "EUR/HUF": "#2ecc71",
    "USD/HUF": "#3498db",
    "GBP/HUF": "#e74c3c",
}

# Fetch data from Yahoo Finance (last 2 years)
frames = {}
for name, ticker in PAIRS.items():
    df = yf.download(ticker, period="2y", interval="1d", progress=False)
    frames[name] = df["Close"].squeeze()

data = pd.DataFrame(frames)
data.index.name = "DateTime"
data = data.reset_index()
data["DateTime"] = pd.to_datetime(data["DateTime"])
data = data.dropna()

# Get latest rates
latest = data.iloc[-1]
latest_date = latest["DateTime"].strftime("%Y.%m.%d")

# Initial plot
fig = px.line(
    data,
    title="Exchange Rates",
    x="DateTime",
    y=["EUR/HUF"],
    color_discrete_map={"EUR/HUF": COLORS["EUR/HUF"]}
)

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])
app.title = "Exchange Rates"
server = app.server

app.index_string = '''<!DOCTYPE html>
<html>
<head>{%metas%}{%favicon%}{%css%}
<style>
    body {
        background-color: transparent !important;
    }
    #date-range input,
    #date-range .DateInput_input {
        color: black !important;
        background-color: white !important;
    }
</style>
</head>
<body>{%app_entry%}{%config%}{%scripts%}{%renderer%}</body>
</html>'''

app.layout = html.Div(
    style={
        "background": "linear-gradient(180deg, #000000 0%, #e67e22 100%)",
        "minHeight": "100vh",
        "padding": "2px 100px",
        "--Dash-Fill-Interactive-Strong": "black",
    },
    children=[dbc.Container(
    fluid=True,
    children=[
        dbc.Row(
            dbc.Col(
                [
                    html.H1("Exchange Rates", className="text-white mt-3"),
                    html.P(
                        ["Live currency exchange rates", html.Br(), "from Yahoo Finance"],
                        className="text-white-50",
                    ),
                ]
            ),
            className="mb-3",
        ),
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody([
                            dbc.Label("Currency Pair", className="text-white"),
                            dcc.Dropdown(
                                id="currency-filter",
                                options=[{"label": pair, "value": pair} for pair in PAIRS],
                                clearable=False,
                                value="EUR/HUF",
                                style={"color": "black", "width": "50%"},
                            ),
                        ]),
                        color="dark",
                    ),
                    md=4,
                ),
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody([
                            dbc.Label("Date Range", className="text-white"),
                            html.Div(
                                dcc.DatePickerRange(
                                    id="date-range",
                                    min_date_allowed=data.DateTime.min().date(),
                                    max_date_allowed=data.DateTime.max().date(),
                                    start_date=data.DateTime.min().date(),
                                    end_date=data.DateTime.max().date(),
                                    style={"color": "black"},
                                ),
                                style={"width": "50%"},
                            ),
                        ]),
                        color="dark",
                    ),
                    md=8,
                ),
            ],
            className="mb-3",
        ),
        dbc.Row(
            dbc.Col(
                html.Div(
                    [
                        html.Span(f"{latest_date}", className="text-muted me-3"),
                    ] + [
                        html.Span([
                            html.Span(f"{pair}: ", style={"color": COLORS[pair], "fontWeight": "bold"}),
                            html.Span(f"{latest[pair]:.2f} HUF", className="text-white me-4"),
                        ]) for pair in PAIRS
                    ],
                )
            ),
            className="mb-3",
        ),
        dbc.Row(
            dbc.Col(
                dbc.ButtonGroup([
                    dbc.Button("1W", id="btn-1w", n_clicks=0, color="secondary", size="sm"),
                    dbc.Button("1M", id="btn-1m", n_clicks=0, color="secondary", size="sm"),
                    dbc.Button("3M", id="btn-3m", n_clicks=0, color="secondary", size="sm"),
                    dbc.Button("6M", id="btn-6m", n_clicks=0, color="secondary", size="sm"),
                    dbc.Button("1Y", id="btn-1y", n_clicks=0, color="secondary", size="sm"),
                    dbc.Button("Max", id="btn-max", n_clicks=0, color="secondary", size="sm"),
                    dbc.Button("All Pairs", id="btn-all", n_clicks=0, color="success", size="sm"),
                ]),
            ),
            className="mb-3",
        ),
        dbc.Row(
            dbc.Col(
                dbc.Card(
                    dcc.Graph(
                        id="rate-chart",
                        figure=fig,
                        config={"displayModeBar": False},
                    ),
                    color="dark",
                ),
            ),
        ),
    ],
)]
)


@app.callback(
    Output("date-range", "start_date"),
    Output("date-range", "end_date"),
    Input("btn-1w", "n_clicks"),
    Input("btn-1m", "n_clicks"),
    Input("btn-3m", "n_clicks"),
    Input("btn-6m", "n_clicks"),
    Input("btn-1y", "n_clicks"),
    Input("btn-max", "n_clicks"),
    prevent_initial_call=True,
)
def update_date_range(w1, m1, m3, m6, y1, mx):
    ctx = dash.callback_context
    button_id = ctx.triggered[0]["prop_id"].split(".")[0]
    end = data.DateTime.max().date()
    offsets = {
        "btn-1w": timedelta(weeks=1),
        "btn-1m": timedelta(days=30),
        "btn-3m": timedelta(days=90),
        "btn-6m": timedelta(days=180),
        "btn-1y": timedelta(days=365),
    }
    if button_id in offsets:
        start = end - offsets[button_id]
    else:
        start = data.DateTime.min().date()
    return start, end


@app.callback(
    Output("rate-chart", "figure"),
    Input("currency-filter", "value"),
    Input("date-range", "start_date"),
    Input("date-range", "end_date"),
    Input("btn-all", "n_clicks"),
)
def update_chart(pair, start_date, end_date, all_clicks):
    ctx = dash.callback_context
    triggered = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else ""

    filtered_data = data.loc[(data.DateTime >= start_date) & (data.DateTime <= end_date)]

    if triggered == "btn-all":
        y_cols = list(PAIRS.keys())
    else:
        y_cols = [pair]

    fig = px.line(
        filtered_data,
        title="Exchange Rates",
        x="DateTime",
        y=y_cols,
        color_discrete_map=COLORS,
    )

    annotations = []
    for col in y_cols:
        if len(filtered_data) > 0:
            last_val = filtered_data[col].iloc[-1]
            last_dt = filtered_data["DateTime"].iloc[-1]
            annotations.append(dict(
                x=last_dt, y=last_val,
                text=f"  {last_val:.2f}",
                showarrow=False,
                font=dict(color=COLORS[col], size=14, family="Verdana"),
                xanchor="left",
            ))

    fig.update_layout(
        template="plotly_dark",
        xaxis_title="Date",
        yaxis_title="HUF",
        font=dict(
            family="Verdana, sans-serif",
            size=18,
            color="white"
        ),
        annotations=annotations,
    )

    return fig


if __name__ == "__main__":
    app.run(debug=True)
