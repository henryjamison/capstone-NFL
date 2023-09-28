from flask import *
import numpy as np
import pandas as pd
import re


app = Flask(__name__)
app.secret_key = 'SECRET'

teams = [
    "ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE",
    "DAL", "DEN", "DET", "GB", "HOU", "IND", "JAX", "KC",
    "LV", "LAC", "LAR", "MIA", "MIN", "NE", "NO", "NYG",
    "NYJ", "PHI", "PIT", "SF", "SEA", "TB", "TEN", "WSH"
]

def load_dataframe(year):
    csv_file = f"./data/{year}_fantasy.csv"
    return pd.read_csv(csv_file, index_col=None)

@app.route('/tables')
@app.route('/tables/<int:year>')
def render_tables(year=None):
    # df_2021 = pd.read_csv('2021_fantasy.csv', index_col=None)
    if year is None:
        year = session.get('selected_year', 2022)  # Get the selected year from the session or default to 2022
    else:
        session['selected_year'] = year 
    df = load_dataframe(year)
    years = [2022,2021,2020,2019,2018]
    return render_template('tables.html',  tables=[df.to_html(classes='data myTable')], titles=df.columns.values, years=years)

@app.route('/home')
@app.route('/', methods=['GET', 'POST'])
def render_home():
    if request.method == 'POST':
        # Retrieve the text from the textarea
        text = request.form.get('textarea')
        # If the text is blank just re render the home page fixes error.
        if text == "":
            return render_template('home.html')
        table = get_player(text)[0]
        name = get_player(text)[1]
        # If the player wasnt found, an empty table is created, display player not found message.
        if table.empty:
            error = True
            err_message = f"{name} not found, try again"
            # err_message = "Player not found, try again"
            return render_template('home.html', error=error, err_message=err_message, teams=teams)
        else:
            return render_template('home.html', tables=[table.to_html(classes='data playerTable')], titles=table.columns.values, name=name, teams=teams)
    else:
        return render_template('home.html', teams=teams)

# @app.route('/home')
def get_player(name):
    df = pd.read_csv('./data/2022_fantasy.csv')
    df['Player'] = df['Player'].apply(lambda x: x.split('*')[0]).apply(lambda x: x.split('\\')[0])
    print("PLAYER NAME: " + name)
    name_lower = name.lower()
    player = df[df['Player'].str.lower() == name_lower]
    if (player.empty):
        print('No such player')
        player_table = pd.DataFrame()
        ret_name = name
    else:
        # id = str(player['PlayerID'][0])
        ret_name = str(player.iloc[0]['Player'])
        id = str(player.iloc[0]['PlayerID'])
        print("PLAYER ID IS: " + id)
        player_table = get_fant_table(id)
    return player_table, ret_name

def get_fant_table(player_id):
    url = 'https://www.pro-football-reference.com/players/' + player_id[0] + '/' + player_id + '/' + 'fantasy/2022/'
    print(url)
    table = pd.read_html(url)[0]
    # print(table.to_html())
    columns_to_drop = ['Unnamed: 7_level_0', 'Unnamed: 6_level_0', 'Unnamed: 1_level_0',
                       'Unnamed: 2_level_0', 'Unnamed: 3_level_0', 'Unnamed: 4_level_0', 'Unnamed: 3_level_0',
                       'Unnamed: 4_level_0', 'Unnamed: 5_level_0', 'Unnamed: 28_level_0', 'Unnamed: 29_level_0',
                       'Unnamed: 30_level_0','Unnamed: 36_level_0',	'Unnamed: 37_level_0',	'Unnamed: 38_level_0',
                       'Unnamed: 22_level_0','Unnamed: 23_level_0','Unnamed: 24_level_0']
    
    # This goes through column value levels and if the column starts with Unnamed,
    # The value is replaced with "", we cant drop the column outright so we must
    # replace it with a "".
    new_columns = []
    for col in table.columns:
        new_col = []
        for level in col:
            if "Unnamed" in level:
                new_col.append('')
            else:
                new_col.append(level)
        new_columns.append(tuple(new_col))

    table.columns = pd.MultiIndex.from_tuples(new_columns)
    table = table.drop(columns=('Rk'), level=-1)
    table.fillna(0,inplace=True)
    print(table.columns.values)
    return table

