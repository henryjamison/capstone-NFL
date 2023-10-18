from flask import *
from bs4 import BeautifulSoup
import numpy as np
import pandas as pd
import requests
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
positions=["RB","QB","WR","TE","K"]
years = [2022,2021,2020,2019,2018]



def load_dataframe(year):
    csv_file = f"./data/{year}_fantasy.csv"
    return pd.read_csv(csv_file, index_col=None)

player_df = load_dataframe(2022)
player_df['Player'] = player_df['Player'].apply(lambda x: x.split('*')[0]).apply(lambda x: x.split('\\')[0])
player_names = player_df['Player'].tolist()
# player_names = ["name1", "name2", "name3"]


@app.route('/tables')
@app.route('/tables', methods=['GET', 'POST'])
def render_tables():
    return render_template('tables.html', years=years,teams=teams,positions=positions)
    # years = [2022,2021,2020,2019,2018]
    # if request.method == 'POST':
    #     team = request.form.get('selected_team')
    #     position = request.form.get('selected_positon')
    #     year = request.form.get('selected_year')
    #     print(team,position,year)
    #     session['selected_year'] = year
    #     df = load_dataframe(year)
    #     return render_template('tables.html',  tables=[df.to_html(classes='data myTable')], titles=df.columns.values, years=years,teams=teams,positions=positions)
    # return render_template('tables.html',years=years,teams=teams,positions=positions)
    # df_2021 = pd.read_csv('2021_fantasy.csv', index_col=None)
    # if year is None:
    #     year = session.get('selected_year', 2022)  # Get the selected year from the session or default to 2022
    # else:
    #     session['selected_year'] = year 
    # df = load_dataframe(year)
    # years = [2022,2021,2020,2019,2018]
    # return render_template('tables.html',  tables=[df.to_html(classes='data myTable')], titles=df.columns.values, years=years,teams=teams,positions=positions)

@app.route('/')
@app.route('/home', methods=['GET', 'POST'])
def render_home():
    if request.method == 'POST':
        # text = request.form.get('text')
        # return render_template('search.html', text=text)
        # print("TEXT IS" + text)
        return redirect(url_for('render_search'))
    else:
        return render_template('home.html')

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

@app.route('/search')
@app.route('/search', methods=['GET', 'POST'])
def render_search():
    players_info = get_top_10()
    error =False
    # print(players_info)
    if request.method == 'POST':
        # Retrieve the text from the textarea
        text = request.form.get('text')
        # If the text is blank just re render the home page fixes error.
        if text == "":
            search=False
            return render_template('search.html', players=players_info,search=search,player_names=player_names)
        table = get_player(text)[0]
        name = get_player(text)[1]
        results = prediction(name)
        # If the player wasnt found, an empty table is created, display player not found message.
        if table.empty:
            error = True
            search = True
            err_message = f"{name} not found, try again"
            return render_template('search.html', error=error, err_message=err_message,players=players_info,search=search,player_names=player_names)
        else:
            search = True
            return render_template('search.html', tables=[table.to_html(classes='data playerTable')], titles=table.columns.values, name=name, players=players_info, search=search,error=error,player_names=player_names, results=results)
    else:
        search=False
        return render_template('search.html',players=players_info,search=False,error=error, player_names=player_names)

def get_top_10():
    url = 'https://www.pro-football-reference.com/years/2023/fantasy.htm'
    table = pd.read_html(url)[0]
    table = table.head(10)

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

    players_list = table[('', 'Player')].tolist()
    positions_list = table[('', 'FantPos')].tolist()
    teams_list = table[('', 'Tm')].tolist()
    points_list = table[('Fantasy', 'FantPt')].tolist()
    rank_list = list(map(lambda i : i + 1, table.index.tolist()))

    players_info = [{'Name': player, 'Position': position, 'Team': team, 'Points':points, 'Rank':rank} for player, position, team, points, rank in zip(players_list, positions_list, teams_list,points_list, rank_list)]
    return players_info

def get_team(name):
    table, id = get_player(name)
    data = preprocessing(table)
    return data['Tm'][0]

def get_opp(team):
    sched = pd.read_csv('./data/2023_schedule.csv')
    new_df = sched.query('Home == @team or Away == @team')
    opp = 'Bye Week'
    if new_df.query('Home == @team').empty:
        opp = new_df['Home'].item()
    else:
        opp = new_df['Away'].item()
    return opp

def create_pred_table(name):
    sched = pd.read_csv('./data/2023_schedule.csv')
    team = get_team(name)
    opp = get_opp(team)
    opponent = 'Opp_' + opp
    week = sched['G#'][0].item()
    pred_dict = {'G#': [week], opponent: [1.0]}
    pred_table = pd.DataFrame(pred_dict)
    not_playing = np.zeros(1)
    for i in teams:
        if 'Opp_' + i not in pred_table.columns:
            pred_table['Opp_' + i] = not_playing
    print(pred_table)
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
    ridge_pred = lm_r.predict(pred_data)[0]
    lasso_pred = lm_l.predict(pred_data)[0]
    elastic_net_pred = lm_en.predict(pred_data)[0]
    ridge_str = 'Ridge model: ' + str(ridge_pred)
    lasso_str = 'Lasso model: ' + str(lasso_pred)
    elastic_net_str = 'Elastic Net Model: ' + str(elastic_net_pred)
    results_str = '\n'.join([ridge_str, lasso_str, elastic_net_str])
    return results_str
    # return (ridge_pred, lasso_pred, elastic_net_pred)


@app.route('/tables')
@app.route('/tables', methods=['GET', 'POST'])
def filter_data():
    print("Entered")
    team = request.form.get('selected_team')
    position = request.form.get('selected_positon')
    year = request.form.get('selected_year')
    print(team,position,year)
    # filtered_data = data
    if year is None:
        year = session.get('selected_year', 2022)  # Get the selected year from the session or default to 2022
    else:
        session['selected_year'] = year 
    df = load_dataframe(year)

    if team:
        df = df[df['Tm'] == team]

    if position:
        df = df[df['FantPos'] == position]

    return render_template('tables.html', filtered_data=df.to_html())

# def getPlayerURL(url):
#     player_url_list = []
#     response = requests.get(url)
#     if response.status_code == 200:
#         soup = BeautifulSoup(response.text, 'html.parser')
#         url = 'https://www.pro-football-reference.com/years/2023/fantasy.htm'
#         player_ids = []
#         player_td_elements = soup.find_all('td', {'data-stat': 'player'})

#         for td_element in player_td_elements:
#         # Do something with the td_element
#             href = td_element.find('a')['href']
#             player_id = href.split('/players/')[1].split('.htm')[0]
#             player_url = f"https://www.pro-football-reference.com/players/{player_id}.htm"
#             player_url_list.append(player_url)

#     else:
#         print("Failed to fetch the webpage.")
#     return player_url_list[:10]

# def get_images(url_list):
#     img_list = []
#     src_list = [] 
#     for u in url_list:
#         req = requests.get(u)
#         soup = BeautifulSoup(req.text, 'html.parser')
#         images = soup.find_all('img', {"itemscope" : "image"})
#         img_list.append(images)

#     for img in img_list:
#         src = img[0]['src']
#         src_list.append(src)
#     return(src_list)

# def get_suggested_players():
