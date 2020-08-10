from __future__ import unicode_literals
import os
import sys
sys.path.insert(0, os.path.realpath(os.path.dirname(__file__)))
os.chdir(os.path.realpath(os.path.dirname(__file__)))

import dash
from dash.dependencies import Output, Input, State
from dash.exceptions import PreventUpdate
import dash_core_components as dcc
import dash_bootstrap_components as dbc
import dash_html_components as html
import plotly
import plotly.graph_objs as go

import sqlite3
import pandas as pd

from collections import Counter
import string
import re
from cache import cache
from stopwrds import stop_words
import time
import pickle

from helpers import log_error
import threading



# cursor = connection.cursor()

#serialization not needed
conn = sqlite3.connect('bbntwitterq.db', check_same_thread=False)

filterHMs_ = [
    'Erica #BBNaija', 'Kiddwaya #BBNaija', 'Neo #BBNaija', 'Vee #BBNaija', 'Brighto #BBNaija',
    'Eric #BBNaija', 'Praise #BBNaija', 'Prince #BBNaija', 'Nengi #BBNaija', 'Laycon #BBNaija',
    'Tolanibaj #BBNaija', 'Tochi #BBNaija', 'TrikyTee #BBNaija', 'Ozo #BBNaija', 'Dorathy #BBNaija',
    'Wathoni #BBNaija', 'Lucy #BBNaija', 'Kaisha #BBNaija'
]

punctuation = [str(i) for i in string.punctuation]

# st = ''

sentiment_colors = {-1:"#EE6055",
                    -0.5:"#FDE74C",
                     0:"#FFE6AC",
                     0.5:"#D0F2DF",
                     1:"#9CEC5B",}


app_colors = {
    # rgb(13, 43, 53)
    # rgb(8, 25, 31)
    'background': 'rgb(13, 43, 53)',
    'text': '#FFFFFF',
    'sentiment-plot':'#0071a5',
    'volume-bar':'#d28a06',
    'sentiment-vs-plot':'#0071c9',
    'someothercolor':'#0071a3',
}

POS_NEG_NEUT = 0.1



custom = '/assets/font_custom.css'
animate = '/assets/animate.css'
font_awesome_url = 'https://use.fontawesome.com/releases/v5.8.1/css/all.css'
app = dash.Dash(__name__, external_stylesheets=[custom, dbc.themes.SOLAR, animate, font_awesome_url])

server = app.server
app.config.suppress_callback_exceptions=True


app.config.update({
     'routes_pathname_prefix':'',
     'requests_pathname_prefix':'',
})

# tab1_layout=[
#     html.Div(className='row', children=[
#         html.Div(id='related-sentiment', children=html.Button('Loading related terms...', id='related_term_button'), className='col s12 m6 l6', style={"word-wrap":"break-word"}),
#         html.Div(id='recent-trending', className='col s12 m6 l6', style={"word-wrap":"break-word"})]),
#         html.Div(className='row', children=[html.Div(dcc.Graph(id='live-graph', animate=False), className='col s12 m6 l6'),
#         html.Div(dcc.Graph(id='historical-graph', animate=False), className='col s12 m6 l6')]),

# tab2_layout=[
#     html.Div(className='row', children=[
#         html.Div(id="recent-tweets-table", className='col s12 m6 l6'),
#         html.Div(dcc.Graph(
#             id='sentiment-pie', animate=False),
#             className='col s12 m6 l6')],
#             style={
#                 'backgroundColor': app_colors['background'],
#                 'margin-top':'30px',
#                 'height':'2000px'},
#                 ]

tab1_layout=[
    html.Div([
        dbc.Row([
            dbc.Col([
                html.Div([
                    dcc.Graph(
                        id='live-graph',
                        animate=False,
                        figure={}
                    ),
                    dcc.Interval(
                        id='graph-update',
                        interval=1*1000,
                        n_intervals=0
        ),
                ]),
            ], xs=12, sm=12, md=6, lg=6),
            dbc.Col([
                html.Div([
                    dcc.Graph(
                        id='historical-graph',
                        animate=False,
                        figure={}
                        ),
                    dcc.Interval(
                        id='historical-update',
                        interval=60*1000,
                        n_intervals=0
        ),
                ]),
            ], sm=12, md=6, lg=6),
        ], no_gutters=True)
    ])
]
        
tab2_layout = [
    html.Div([
        dbc.Row([
            dbc.Col([
                html.Div(
                    id='recent-tweets-table',
                ),
                dcc.Interval(
                    id='recent-table-update',
                    interval=2*1000,
                    n_intervals=0
                ),

            ], sm=12, md=12, style={'margin-bottom':'7px'}),
        ]),
            dbc.Row([
                dbc.Col([
                    html.Hr(),
                    dcc.Dropdown(
                        id='sentiment_term_pie',
                        options=[{'label':c.split(' ')[0], 'value':c.split(' ')[0]} for c in filterHMs_],
                        value='Erica',
                        searchable=False,
                        clearable=False,
                        style={'background':'whitesmoke'}
                        ),
                    ],xs=8, lg= 4, sm=4, md=4, style={
                        'margin-top':'15px',
                        'text-align': 'center'
                        }
                    ),
            ],justify="center"),

            dbc.Row([
                dbc.Col([
                html.Div([
                    dcc.Graph(
                        id='sentiment-pie', animate=False, figure={}),
                    dcc.Interval(
                        id='sentiment-pie-update',
                        interval=60*1000,
                        n_intervals=0
                    ),
                ]),
                ], sm=12, md=12),
                dbc.Col([
                    html.Div("(If the selection above does not reflect then no data for that housemate yet. Try again in 60mins)"),
                    html.Hr()
                ], sm=12, md=12, style={'text-align':'center'}),
            ], justify="center"),
    ],),
]



app.layout = html.Div([
                dbc.Row([
                    dbc.Col(className='xtcy-title animate__animated animate_bounce', children=[html.P("2B-Naija")], xs=12, sm=12, md=12, style={'margin-bottom':'3px', 'margin-top':'10px', 'padding-top':'20px', 'font-size':'70px'}),
                    dbc.Col(className='xtcy-slogan', children=[html.P("Get Live #BBNaija sentiments")], xs=12, sm=12, md=12,)
                ],justify="center", style={'margin-bottom':'20px'}),
                dbc.Row([
                    dbc.Col(
                        [
                            html.H5("CHOOSE BBN HOUSEMATE*"),
                            dcc.Dropdown(
                                id='sentiment_term',
                                options=[{'label':c.split(' ')[0], 'value':c.split(' ')[0]} for c in filterHMs_],
                                value='Erica',
                                searchable=False,
                                clearable=False,
                                style={'background':'whitesmoke'}
                                ),
                        ],xs=12, lg= 8, sm=8, md=8, style={
                            'margin-top':'10px',
                            'text-align': 'center'
                        }
                    ),

                ],justify="center"),

                dbc.Row([
                    dbc.Col([
                        html.Div(
                            id="related-sentiment",
                            children=html.Button("Related Terms",
                            id='related_term_button'),
                            style={"word-wrap":"break-word"}
                        ),
                        dcc.Interval(
                            id='related-update',
                            interval=30*1000,
                            n_intervals=0
                        ),

                    ], sm=12, md=12),
                    # dbc.Col([
                    #     html.Div(
                    #         id="recent-trending",
                    #         style={"word-wrap":"break-word"},
                    #     ),
                    #     dcc.Interval(
                    #         id='recent-table-update',
                    #         interval=2*1000,
                    #         n_intervals=0
                    #     ),

                    # ], sm=12, md=6)
                ], style={'margin-left':'2px'}),
                #         html.Div(id='related-sentiment', children=html.Button('Loading related terms...', id='related_term_button'), className='col s12 m6 l6', style={"word-wrap":"break-word"}),
#         html.Div(id='recent-trending', className='col s12 m6 l6', style={"word-wrap":"break-word"})]),

                html.Br(),
                dcc.Store(id='session', storage_type='session'),
                dbc.Tabs([
                    dbc.Tab(label="analysis", tab_id="2bn-analysis", tab_style={"margin-left":"auto"}),
                    dbc.Tab(label="sentiment", tab_id="2bn-sentiment", label_style={"color":"#00AEF9"})
                ],
                id="tabs",
                active_tab="2bn-analysis",
                ),

                html.Div(id="2bn-content"),

                dbc.Row([
                    dbc.Col(className='compare', children=[
                        html.P("Compare Sentiments Between Housemates (beta feature)")
                    ], md=12, xs=12, lg=12, style={'text-align':'center'}),

                    dbc.Col([
                            html.Div([
                                dcc.Dropdown(
                                id='contender',
                                options=[{'label':c.split(' ')[0], 'value':c.split(' ')[0]} for c in filterHMs_],
                                value='Nengi',
                                searchable=False,
                                clearable=False,
                                style={'background':'whitesmoke'}
                            ),
                        ]),
                    ],xs=8, lg= 6, sm=6, md=6, style={
                            'margin-top':'5px',
                            'text-align': 'center'
                        }, ),
                ], justify="center"),

                dbc.Row([
                    dbc.Col([
                        html.Div([
                            dcc.Graph(
                                id='historical-graph-vs',
                                animate=False,
                                figure={}
                            ),
                            dcc.Interval(
                                id='historical-vs-update',
                                interval=60*1000,
                                n_intervals=0
                            ),
                        ]),
                    ], xs=12),
                ]),

                dbc.Row([
                    html.Div("1: Positive\t0:Neutral\t-1:Negative"),
                    dbc.Col([html.Div("MOST TWEETS CURRENTLY FROM..."),
                    html.Div(
                        id='places',
                        # animate=False,
                        # figure={}
                    ),
                    dcc.Interval(
                        id='places-update',
                        interval=120*1000,
                        n_intervals=0
                    ),
                    ],xs=12),
                ], justify="center"),

                dbc.Row([
                    dbc.Col([html.P("Not Affliated with the brand name Big Brother Naija")],
                    style={'text-align':'center', 'margin-top':'20px','margin-bottom':'5px'}),
                ]),

                dbc.Row([
                        dbc.Col([
                                dcc.Markdown("[EMMANUEL](https://www.twitter.com/__oemmanuel__)", style={'cursor': 'grab','color': 'cyan','font-weight': 'bold','padding-left':'2px'}),
                            ], xs=6, style={}),
                        dbc.Col(
                                [
                                    dcc.Markdown(
                                    "Resources: [SdGH](https://github.com/Sentdex/socialsentiment)|[covid19-af](https://covid19-tracker-af.herokuapp.com/)", style = {'textAlign': 'right', 'padding-right':'3px'}),
                                    ], xs=6, style={}
                                ),

                            ]),

                ])

                


MAX_DF_LENGTH = 100

def df_resample_sizes(df, maxlen=MAX_DF_LENGTH):
    df_len = len(df)
    resample_amt = 100
    vol_df = df.copy()
    vol_df['volume'] = 1

    ms_span = (df.index[-1] - df.index[0]).seconds*1000
    rs = int(ms_span/maxlen)

    df = df.resample('{}ms'.format(int(rs))).mean()
    df.dropna(inplace=True)

    vol_df = vol_df.resample('{}ms'.format(int(rs))).sum()
    vol_df.dropna(inplace=True)

    df = df.join(vol_df['volume'])

    return df


# make a counter with blacklist words and empty word with some big value - we'll use it later to filter counter
stop_words.append('')
blacklist_counter = Counter(dict(zip(stop_words, [1000000]*len(stop_words))))

# complie a regex for split operations (punctuation list, plus space and new line)
split_regex = re.compile("[ \n"+re.escape("".join(punctuation))+']')

def related_sentiments(df, sentiment_term, how_many=14): #13, as same term is excluded
    try:
        related_words = {}
        # it's way faster to join strings to one string then use regex split using your punctuation list plus space and new line chars
        # regex precomiled above
        tokens = split_regex.split(' '.join(df['tweet'].values.tolist()).lower())

        # it is way faster to remove stop_words, sentiment_term and empty token by making another counter
        # with some big value and substracting (counter will substract and remove tokens with negative count)
        blacklist_counter_with_term = blacklist_counter.copy()
        blacklist_counter_with_term[sentiment_term] = 1000000
        counts = (Counter(tokens) - blacklist_counter_with_term).most_common(13)

        for term,count in counts:
            try:
                df = pd.read_sql("SELECT sentiment.* FROM  sentiment_fts fts LEFT JOIN sentiment ON fts.rowid = sentiment.id WHERE fts.sentiment_fts MATCH ? ORDER BY fts.rowid DESC LIMIT 200", conn, params=(term,))
                related_words[term] = [df['sentiment'].mean(), count]
            except Exception as e:
                log_error(str(e))

        return related_words

    except Exception as e:
        log_error(str(e))


def quick_color(s):
    # except return bg as app_colors['background']
    if s >= POS_NEG_NEUT:
        # positive
        return "#002C0D"
    elif s <= -POS_NEG_NEUT:
        # negative:
        return "#270000"

    else:
        return app_colors['background']

def generate_table(df, sentiment_term='', max_rows=3):
    return html.Table(className="responsive-table",
                      children=[
                        #   print("VALUES: ",df.values.tolist()),
                        #   print("======"),
                        #   print(df.columns.values),
                          
                          html.Thead(
                              html.Tr([html.Th(col.title() ) for col in df.columns.values],
                                  style={'color':app_colors['text']}
                                  )
                              ),
                          html.Tbody([
                              html.Tr([
                                  html.Td(data) for data in i
                                      ], style={
                                          'color':app_colors['text'],
                                          'background-color':quick_color(i[1])
                                          }
                                  ) for i in df.values.tolist()
                          ]),
                          html.P("Table for {}".format(sentiment_term)),
                        ])


#1:positve, 0:neutral -1: negative
def pos_neg_neutral(col):
    if col >= POS_NEG_NEUT:
        return 1
    elif col <= -POS_NEG_NEUT:
        return -1
    else:
        return 0



def map_places(df, sentiment_term):
    for col in df.columns:
        df[col] = df[col].astype('str')
    
    # scl = [
    #     [0.0, 'rgb(209,15,17)'], [0.2, 'rgb(204,60,49)'], [0.4, 'rgb(204,60,49)']\
    #     [0.6, 'rgb(44,60,49)'], [0.8, 'rgb(102,60,49)'], [1, 'rgb(65,60,49)']
    # ]

    df['text'] = df['place'] + '<br>' + 'Avg. Sentiment: '+df['sentiment'] + \
        '<br>' + '# of tweets: ' + df['nb_tweets']

    data = [
        dict(
            type='cholopleth',
            # colorscale=scl,
            autocolorscale=True,
            locations='iso_alpha',
            z = df['sentiment'].astype(float),
            hovername=df['place'],
            text = df['text']

        )
    ]
    return data
            


 #########################################################################################################
 # CALLBACKS #
 # ######################################################################################################
 # 




@app.callback(Output("2bn-content", "children"),
                [Input("tabs", "active_tab")])
def tab_switch(_active_tab):
    # if _active_tab is not None:
    if _active_tab == "2bn-analysis":
        return tab1_layout
        
    elif _active_tab == "2bn-sentiment":
        return tab2_layout
        
    return html.Div([
                    html.P("If you're seeing this then something is not right")
                    ])   


# @app.callback(Output('memory-output', 'data'),
#             [Input('sentiment_term', 'value')])
#             # [State('memory-output', 'data')])
# def store_data(sentiment_term):
#     if sentiment_term is None:
#         raise PreventUpdate
#     return sentiment_term



@app.callback(Output('sentiment-pie', 'figure'),
              [Input('sentiment_term_pie', 'value'), Input('sentiment-pie-update', 'n_intervals')])
def update_pie_chart(sentiment_term_pie, n):
    # get data from cache
    total_tweets = 0
    # print(sentiment_term)
    for i in range(100):
        sentiment_pie_dict = cache.get('sentiment_shares', sentiment_term_pie)
        # print("PIE DICT: ", sentiment_pie_dict)
        if sentiment_pie_dict:
            break
        time.sleep(0.1)

    if sentiment_pie_dict is None:
        raise PreventUpdate
    else:
        total_tweets = sum(sentiment_pie_dict.values())

    labels = ['Positive','Negative']

    try:
        pos = sentiment_pie_dict[1]
    except:
        pos = 0

    try:
        neg = sentiment_pie_dict[-1]
    except:
        neg = 0



    values = [pos,neg]
    colors = ['#007F25', '#800000']

    trace = go.Pie(
                labels=labels,
                values=values,
                # hoverinfo='label+percent', 
                # textinfo='value',
                # pull=[0, 0, .2, 0],
                textfont=dict(
                    size=22,
                    color=app_colors['text'],
                    ),
                marker=dict(
                    colors=colors, 
                    line=dict(color=app_colors['background'], width=4)))

    return {
        'data':[trace],
        'layout' : go.Layout(
                        title='Pos. vs Neg. sentiment for {0} \n({1} Tweets)'.format(sentiment_term_pie, total_tweets),
                        font={'color':app_colors['text'], 'family':'Courier New, monospace'},
                        plot_bgcolor = app_colors['background'],
                        paper_bgcolor = app_colors['background'],
                        showlegend=True
                        )
        }

           
@app.callback(Output('recent-tweets-table', 'children'),
                [Input('sentiment_term','value'), Input('recent-table-update', 'n_intervals')])  
def update_recent_tweets(sentiment_term, n):
    if 'kidd' in sentiment_term.lower() or 'tola' in sentiment_term.lower() or 'dora' in sentiment_term.lower():
        # print("IF", sentiment_term)
        df = pd.read_sql("SELECT sentiment.* FROM sentiment_fts fts LEFT JOIN sentiment ON fts.rowid = sentiment.id WHERE fts.sentiment_fts MATCH ? ORDER BY fts.rowid DESC LIMIT 10", conn, params=(sentiment_term+'*',))
    elif sentiment_term+' #BBNaija' in filterHMs_:
        # print("ELSE: ", sentiment_term, sentiment_term+' #BBNaija')
        df = pd.read_sql("SELECT sentiment.* FROM sentiment_fts fts LEFT JOIN sentiment ON fts.rowid = sentiment.id WHERE fts.sentiment_fts MATCH ? ORDER BY fts.rowid DESC LIMIT 10", conn, params=(sentiment_term,))
    else:
        df = pd.read_sql("SELECT * FROM sentiment ORDER BY id DESC, unix DESC LIMIT 10", conn)
    
    # df['date'] = pd.to_datetime(df['unix'], unit='ms')

        #due to housemate tagging, there might be duplicate tweets containing more than one
        #housemate name, so drop duplicates
    df = df.drop(['unix','id'], axis=1)
    df = df[['tweet','sentiment']].drop_duplicates()
    return generate_table(df.iloc[:6,], sentiment_term=sentiment_term, max_rows=6)



@app.callback(Output('live-graph', 'figure'),
              [Input('sentiment_term', 'value'), Input('graph-update', 'n_intervals')])
def update_graph_scatter(sentiment_term, n):
    # global g
    # g = sentiment_term
    # print(sentiment_term)
    try:
        if 'kidd' in sentiment_term.lower() or 'tola' in sentiment_term.lower() or 'dora' in sentiment_term.lower():
            # print("IF", sentiment_term)
            df = pd.read_sql("SELECT sentiment.* FROM sentiment_fts fts LEFT JOIN sentiment ON fts.rowid = sentiment.id WHERE fts.sentiment_fts MATCH ? ORDER BY fts.rowid DESC LIMIT 10000", conn, params=(sentiment_term+'*',))
        elif sentiment_term:
            df = pd.read_sql("SELECT sentiment.* FROM sentiment_fts fts LEFT JOIN sentiment ON fts.rowid = sentiment.id WHERE fts.sentiment_fts MATCH ? ORDER BY fts.rowid DESC LIMIT 10000", conn, params=(sentiment_term,))
        else:
            df = pd.read_sql("SELECT * FROM sentiment ORDER BY id DESC, unix DESC LIMIT 10", conn)
        df.sort_values('unix', inplace=True)
        # print(df.place)
        df['date'] = pd.to_datetime(df['unix'], unit='ms')
        df.set_index('date', inplace=True)
        init_length = len(df)
        # print(init_length)
        df['sentiment_smoothed'] = df['sentiment'].rolling(int(len(df)/5)).mean()
        df = df_resample_sizes(df)
        X = df.index
        Y = df.sentiment_smoothed.values
        Y2 = df.volume.values
        data = plotly.graph_objs.Scatter(
                        x=X,
                        y=Y,
                        name='Sentiment',
                        mode= 'lines',
                        yaxis='y2',
                        line = dict(color = (app_colors['sentiment-plot']),
                                    width = 4,)
                        )

        data2 = plotly.graph_objs.Bar(
                        x=X,
                        y=Y2,
                        name='Volume',
                        marker=dict(color=app_colors['volume-bar']),
                        )

        return {
            'data': [data,data2],
            'layout' : go.Layout(xaxis=dict(range=[min(X),max(X)]),
                                                                yaxis=dict(range=[min(Y2),max(Y2*4)], title='Volume', side='right'),
                                                                yaxis2=dict(range=[min(Y),max(Y)], side='left', overlaying='y',title='sentiment'),
                                                                title='#BBNaija sentiment for housemate {}'.format(sentiment_term),
                                                                font={'color':app_colors['text'], 'family':'Courier New, monospace'},
                                                                plot_bgcolor = app_colors['background'],
                                                                paper_bgcolor = app_colors['background'],
                                                                showlegend=False)}

    except Exception as e:
        log_error(str(e))


@app.callback(Output('historical-graph', 'figure'),
              [Input('sentiment_term', 'value'), Input('historical-update','n_intervals')])
def update_hist_graph_scatter(sentiment_term, n):
    try:
        if 'kidd' in sentiment_term.lower() or 'tola' in sentiment_term.lower() or 'dora' in sentiment_term.lower():
            # print("IF", sentiment_term)
            df = pd.read_sql("SELECT sentiment.* FROM sentiment_fts fts LEFT JOIN sentiment ON fts.rowid = sentiment.id WHERE fts.sentiment_fts MATCH ? ORDER BY fts.rowid DESC LIMIT 10000", conn, params=(sentiment_term+'*',))
        elif sentiment_term+' #BBNaija' in filterHMs_:
            df = pd.read_sql("SELECT sentiment.* FROM sentiment_fts fts LEFT JOIN sentiment ON fts.rowid = sentiment.id WHERE fts.sentiment_fts MATCH ? ORDER BY fts.rowid DESC LIMIT 10000", conn, params=(sentiment_term,))
        else:
            df = pd.read_sql("SELECT * FROM sentiment ORDER BY id DESC, unix DESC LIMIT 10", conn)
        df.sort_values('unix', inplace=True)
        df['date'] = pd.to_datetime(df['unix'], unit='ms')
        df.set_index('date', inplace=True)
                # save this to a file, then have another function that

                # updates because of this, using intervals to read the file.
                # https://community.plot.ly/t/multiple-outputs-from-single-input-with-one-callback/4970

                # store related sentiments in cache
        cache.set('related_terms', sentiment_term, related_sentiments(df, sentiment_term), 120)

                #print(related_sentiments(df,sentiment_term), sentiment_term)
        init_length = len(df)
        df['sentiment_smoothed'] = df['sentiment'].rolling(int(len(df)/5)).mean()
        df.dropna(inplace=True)
        df = df_resample_sizes(df,maxlen=500)
        X = df.index
        Y = df.sentiment_smoothed.values
        Y2 = df.volume.values

        data = plotly.graph_objs.Scatter(
                        x=X,
                        y=Y,
                        name='Sentiment',
                        mode= 'lines',
                        yaxis='y2',
                        line = dict(color = (app_colors['sentiment-plot']),
                                    width = 4,)
                        )

        data2 = plotly.graph_objs.Bar(
                        x=X,
                        y=Y2,
                        name='Volume',
                        marker=dict(color=app_colors['volume-bar']),
                        )

        df['sentiment_shares'] = list(map(pos_neg_neutral, df['sentiment']))

                #sentiment_shares = dict(df['sentiment_shares'].value_counts())
        cache.set('sentiment_shares', sentiment_term, dict(df['sentiment_shares'].value_counts()), 120)

        return {
            'data': [data,data2],
            'layout' : go.Layout(xaxis=dict(range=[min(X),max(X)]), # add type='category to remove gaps'
                                                                yaxis=dict(range=[min(Y2),max(Y2*4)], title='Volume', side='right'),
                                                                yaxis2=dict(range=[min(Y),max(Y)], side='left', overlaying='y',title='sentiment'),
                                                                title='#BBNaija sentiment for {} over time'.format(sentiment_term),
                                                                font={'color':app_colors['text'],'family':'Courier New, monospace',},
                                                                plot_bgcolor = app_colors['background'],
                                                                paper_bgcolor = app_colors['background'],
                                                                showlegend=False)}

    except Exception as e:
        log_error(str(e))



max_size_change = .4

def generate_size(value, smin, smax):
    size_change = round((((value-smin)/smax)*2)-1,2)
    final_size = (size_change*max_size_change)+1
    return final_size*120


#SINCE A SINGLE FUNCTION CANNOT UPDATE MULTIPLE OUTPUTS...
#https://community.plot.ly/t/multiple-outputs-from-single-input-with-one-callback/4970

@app.callback(Output('related-sentiment', 'children'),
            [Input('sentiment_term','value')])
def update_related_terms(sentiment_term):
    try:#get data from cache
        # global st
        # st = sentiment_term
        # print(st)
        for i in range(100):#term: {mean sentiment, count}
            related_terms = cache.get('related_terms', sentiment_term) 
            if related_terms:
                break
            time.sleep(0.1)

        if not related_terms:
            # print("PROBLEM")
            return None

        buttons = [
            html.Button('{}({})'.format(term, related_terms[term][1]), 
            id='related_term_button',
            value=term,
            className='btn',
            type='submit',
            style={
                'background-color':'#4CBFE1',
                'margin-right':'5px',
                'margin-top':'5px'}) for term in related_terms]
        #size: related_terms[term][1], sentiment related_terms[term][0]
        

        sizes = [related_terms[term][1] for term in related_terms]
        smin = min(sizes)
        smax = max(sizes) - smin  

        buttons = [html.H5('Recent terms associated with {}: '.format(sentiment_term),
             style={'color':app_colors['text'],'margin-top':'6px',})]+[html.Span(term, 
             style={'color':sentiment_colors[round(related_terms[term][0]*2)/2],
                                                              'margin-right':'15px',
                                                              'margin-top':'15px',
                                                              'border-bottom': '2px solid',
                                                              'family':'Courier New, monospace',
                                                            #   'background': 'slategray',
                                                              'font-size':'{}%'.format(generate_size(related_terms[term][1], smin, smax))}) for term in related_terms if term.lower() != sentiment_term.lower()]


        return buttons

    except Exception as e:
        log_error(str(e))




@app.callback(Output('historical-graph-vs', 'figure'),
              [Input('sentiment_term', 'value'), Input('contender','value'), Input('historical-vs-update','n_intervals')])
def compare(sentiment_term, contender, negative):
    # print(sentiment_term, contender)
    try:
        if sentiment_term and contender:
            df1 = pd.read_sql("SELECT sentiment.* FROM sentiment_fts fts LEFT JOIN sentiment ON fts.rowid = sentiment.id WHERE fts.sentiment_fts MATCH ? ORDER BY fts.rowid DESC LIMIT 10000", conn, params=(sentiment_term,))
            df2 = pd.read_sql("SELECT sentiment.* FROM sentiment_fts fts LEFT JOIN sentiment ON fts.rowid = sentiment.id WHERE fts.sentiment_fts MATCH ? ORDER BY fts.rowid DESC LIMIT 10000", conn, params=(contender,))
            # print(df1, df2)
    except Exception as e:
        print(str(e))
    # print(df1, df2)
    else:
        # print(df1, df2)
        df1.sort_values('unix', inplace=True), df2.sort_values('unix', inplace=True)
        df1['date'], df2['date'] = pd.to_datetime(df1['unix'], unit='ms'), pd.to_datetime(df2['unix'], unit='ms')
        df1.set_index('date', inplace=True), df2.set_index('date', inplace=True)

        cache.set('related_terms', sentiment_term, related_sentiments(df1, sentiment_term), 120)
        cache.set('related_terms', contender, related_sentiments(df2, contender), 120)

                    #print(related_sentiments(df,sentiment_term), sentiment_term)
        init_length1, init_length2 = len(df1), len(df2)
        df1['sentiment_smoothed'], df2['sentiment_smoothed']  = df1['sentiment'].rolling(int(len(df1)/5)).mean(), df2['sentiment'].rolling(int(len(df2)/5)).mean()
        df1.dropna(inplace=True), df2.dropna(inplace=True)
        df1, df2 = df_resample_sizes(df1,maxlen=500), df_resample_sizes(df2,maxlen=500)
        X = df1.index
        Y = df1.sentiment_smoothed.values
        Y2 = df2.sentiment_smoothed.values

        data = plotly.graph_objs.Scatter(
                            x=X,
                            y=Y,
                            name='{}'.format(sentiment_term),
                            mode= 'lines',
                            # yaxis='y2',
                            line = dict(color = (app_colors['sentiment-plot']),
                                        width = 4,)
                            )

        data2 = plotly.graph_objs.Scatter(
                            x=X,
                            y=Y2,
                            name='{}'.format(contender),
                            mode= 'lines',
                            line = dict(color = (app_colors['sentiment-vs-plot']),
                                        width = 4,),
                            )

        df1['sentiment_shares1'],df2['sentiment_shares2']  = list(map(pos_neg_neutral, df1['sentiment'])),list(map(pos_neg_neutral, df2['sentiment']))

                    #sentiment_shares = dict(df['sentiment_shares'].value_counts())
        cache.set('sentiment_shares1', sentiment_term, dict(df1['sentiment_shares1'].value_counts()), 120)
        cache.set('sentiment_shares2', contender, dict(df2['sentiment_shares2'].value_counts()), 120)

    return {
            'data': [data,data2],
            'layout' : go.Layout(xaxis=dict(range=[min(X),max(X)]), # add type='category to remove gaps'
                                                                # yaxis=dict(range=[min(Y2),max(Y2*4)], title='Volume', side='right'),
                                                                yaxis2=dict(range=[min(Y),max(Y)], side='left',title='sentiment'),
                                                                title='#BBNaija sentiment for {0}* vs {1} over time'.format(sentiment_term, contender),
                                                                font={'color':app_colors['text'],'family':'Courier New, monospace',},
                                                                plot_bgcolor = app_colors['background'],
                                                                paper_bgcolor = app_colors['background'],
                                                                showlegend=False)}




@app.callback(Output('places', 'children'),
              [Input('sentiment_term', 'value'), Input('places-update','n_intervals')])
def update_map(input, n):
    
    if input:
        df = pd.read_sql("SELECT sentiment.place AS place, ROUND(AVG(sentiment.sentiment), 2) AS sentiment, COUNT(sentiment.tweet) AS nb_tweets FROM sentiment_fts fts LEFT JOIN sentiment ON fts.rowid = sentiment.id WHERE fts.sentiment_fts MATCH ? GROUP BY sentiment.place ORDER BY fts.rowid DESC LIMIT 10000", conn, params=(input,))
    df = df[df['nb_tweets'] >= 50]
    df = df[['place','sentiment', 'nb_tweets']]
    return generate_table(df.iloc[:7, :], sentiment_term=input, max_rows=3)



        # return map_places(df, input)
# @app.callback(Output('recent-trending', 'children'),
#             [Input(component_id='sentiment_term', component_property='value')])
# def update_recent_trending(sentiment_term):
#     try:
#         query = """
#                     SELECT value From misc WHERE key = 'trending'
#                 """

#         c = conn.cursor()
#         result = c.execute(query).fetchone()
#         related_terms = pickle.loads(result[0])
#         sizes = [related_terms[term][1] for term in related_terms]
#         smin = min(sizes)
#         smax = max(sizes) - smin  
#         buttons = [
#             html.H5('Recently Trending Terms in #BBNaija: ',
#             style={'color':app_colors['text']})]+[html.Span(term, style={'color':sentiment_colors[round(related_terms[term][0]*2)/2],
#                                                                     'margin-right':'15px',
#                                                                     'margin-top':'15px',
#                                                                     'font-size':'{}%'.format(generate_size(related_terms[term][1], smin, smax))}) for term in related_terms]


#         return buttons
                

#     except Exception as e:
#         log_error(str(e))
            



# external_js = ['https://cdnjs.cloudflare.com/ajax/libs/materialize/0.100.2/js/materialize.min.js',
#                'https://pythonprogramming.net/static/socialsentiment/googleanalytics.js']
# for js in external_js:
#     app.scripts.append_script({'external_url': js})

# dev_server = app.run_server

if __name__ == '__main__':
    app.run_server(debug=False)