from flask import *
import numpy as np
import pandas as pd
import re
from sklearn.preprocessing import OneHotEncoder
import warnings
from sklearn.linear_model import Ridge
from sklearn.linear_model import Lasso
from sklearn.linear_model import ElasticNet
warnings.filterwarnings("ignore")


app = Flask(__name__)
app.secret_key = 'SECRET'

teams = [
    "ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE",
    "DAL", "DEN", "DET", "GNB", "HOU", "IND", "JAX", "KAN",
    "LVR", "LAC", "LAR", "MIA", "MIN", "NWE", "NOR", "NYG",
    "NYJ", "PHI", "PIT", "SFO", "SEA", "TAM", "TEN", "WAS"
]

curr_week = 7

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
        prediction(name)
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
    # print(table.columns.values)
    table.rename({'Unnamed: 4_level_2':'Home/Away'}, axis=1, inplace=True)
    new_columns = []
    for col in table.columns:
        new_col = []
        for level in col:
            # print (level)
            if "Unnamed" in level:
                new_col.append('')
            else:
                new_col.append(level)
        new_columns.append(tuple(new_col))

    table.columns = pd.MultiIndex.from_tuples(new_columns)
    table = table.drop(columns=('Rk'), level=-1)
    table.fillna(0,inplace=True)
    table.loc[table.index[:-1], ('', '', 'Home/Away')] = table.loc[table.index[:-1], ('', '', 'Home/Away')].apply(lambda x: 'Away' if x == '@' else ('Home' if x == 0 else x))
    return table

def get_team(name):
    table, id = get_player(name)
    data = preprocessing(table)
    return data['Tm'][0]

def get_opp(team):
    schedule = pd.read_csv('./data/Schedule.csv')
    game = schedule.query('Week == (@curr_week) and (Home == @team or Away == @team)')
    opp = 'Bye Week'
    if game.query('Home == @team').empty:
        opp = game['Home'].item()
    else:
        opp = game['Away'].item()
    return opp

def create_pred_table(name):
    sched = pd.read_csv('./data/2023_schedule.csv')
    team = get_team(name)
    opp = get_opp(team)
    #if opp = bye week have a way to print that they are on the bye week
    opponent = 'Opp_' + opp
    week = sched['G#'][0].item()
    pred_dict = {'G#': [week], opponent: [1.0]}
    pred_table = pd.DataFrame(pred_dict)
    not_playing = np.zeros(1)
    for i in teams:
        if 'Opp_' + i not in pred_table.columns:
            pred_table['Opp_' + i] = not_playing
    return pred_table

def preprocessing(player_table):
    #get the table
    df = player_table
    #remove unneeded columns from a higher level
    table = df.drop(['Inside 20', 'Inside 10', 'Snap Counts'], axis=1)
    #make only one level of column names
    table.columns = table.columns.get_level_values(-1)
    #drop columns not needed for training
    tab = table.drop(['Date', 'Pos', 'DKPt', 'FDPt', 'Home/Away',  'Result'], axis=1)
    drop = tab.shape
    #drop totals column
    data = tab.drop(index=(drop[0] - 1))
    #one hot encode opponent column
    encoder = OneHotEncoder()
    onehotarray = encoder.fit_transform(data[['Opp']]).toarray()
    items = [f'{"Opp"}_{item}' for item in encoder.categories_[0]]
    data[items] = onehotarray
    data = data.drop('Opp', axis=1)
    #add missing opponents to have all teams in the dataframe
    teams_unplayed = np.zeros(drop[0] - 1)
    for i in teams:
        if 'Opp_' + i not in data.columns:
            data['Opp_' + i] = teams_unplayed
    return data

def prediction(name):
    table, pid = get_player(name)
    train = preprocessing(table)
    train_data = train.drop('Tm', axis=1)
    pred_data = create_pred_table(name)
    y_train = train_data['FantPt'].values
    X_train = train_data.drop('FantPt', axis=1).values
    lm_r = Ridge(alpha=10).fit(X_train, y_train)
    lm_l = Lasso().fit(X_train, y_train)
    lm_en = ElasticNet().fit(X_train, y_train)
    ridge_pred = lm_r.predict(pred_data)
    lasso_pred = lm_l.predict(pred_data)
    elastic_net_pred = lm_en.predict(pred_data)
    print('Ridge model: ' + str(ridge_pred))
    print('Lasso model: ' + str(lasso_pred))
    print('Elastic Net Model: ' + str(elastic_net_pred))
    return ridge_pred, lasso_pred, elastic_net_pred


