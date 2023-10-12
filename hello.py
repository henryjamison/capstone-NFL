from flask import *
from bs4 import BeautifulSoup
import numpy as np
import pandas as pd
import requests



app = Flask(__name__)
app.secret_key = 'SECRET'

teams = [
    "ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE",
    "DAL", "DEN", "DET", "GB", "HOU", "IND", "JAX", "KC",
    "LV", "LAC", "LAR", "MIA", "MIN", "NE", "NO", "NYG",
    "NYJ", "PHI", "PIT", "SF", "SEA", "TB", "TEN", "WSH"
]
positions=["RB","QB","WR","TE","K"]
years = [2022,2021,2020,2019,2018]

def load_dataframe(year):
    csv_file = f"./data/{year}_fantasy.csv"
    return pd.read_csv(csv_file, index_col=None)

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
            return render_template('search.html', players=players_info,search=search)
        table = get_player(text)[0]
        name = get_player(text)[1]
        # If the player wasnt found, an empty table is created, display player not found message.
        if table.empty:
            error = True
            search = True
            err_message = f"{name} not found, try again"
            return render_template('search.html', error=error, err_message=err_message,players=players_info,search=search)
        else:
            search = True
            return render_template('search.html', tables=[table.to_html(classes='data playerTable')], titles=table.columns.values, name=name, players=players_info, search=search,error=error)
    else:
        search=False
        return render_template('search.html',players=players_info,search=False,error=error)

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
