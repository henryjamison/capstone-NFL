from flask import *
import numpy as np
import pandas as pd
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
positions=["RB","QB","WR","TE"]
years = [2023,2022,2021,2020,2019,2018]

# Current Week number
curr_week = 14

def load_dataframe(year):
    csv_file = f"./data/{year}_fantasy.csv"
    return pd.read_csv(csv_file, index_col=None)

# This code just gets the updated list of players in the current fantasy year, its used for autofill in our search bar.
updated_fantasy_url_2023 = 'https://www.pro-football-reference.com/years/2023/fantasy.htm'
player_df = pd.read_html(updated_fantasy_url_2023)[0]
player_df[('Unnamed: 1_level_0', 'Player')] = player_df[('Unnamed: 1_level_0', 'Player')].apply(lambda x: x.split('*')[0]).apply(lambda x: x.split('\\')[0])
player_df = player_df[player_df[('Unnamed: 1_level_0', 'Player')] != 'Player']
list_of_names = player_df[('Unnamed: 1_level_0', 'Player')].tolist()
kicker_df = pd.read_csv('./data/2023_NFL_kickers.csv')
kicker_names = kicker_df['Player'].tolist()
player_names = list_of_names + kicker_names

# This renders our table page HTML.
@app.route('/tables')
@app.route('/tables', methods=['GET', 'POST'])
def render_tables():
    team = request.form.get('selected_team')
    position = request.form.get('selected_positon')
    year = request.form.get('selected_year')
    if year is None:
        year = session.get('selected_year', 2023)  # Get the selected year from the session or default to 2022
    else:
        session['selected_year'] = year 
    df = load_dataframe(year)
    df = clean_df(df)
    if team:
        df = df[df['Tm'] == team]
    if position:
        df = df[df['FantPos'] == position]
    df = df.reset_index(drop=True)
    # print(team,position,year)
    return render_template('tables.html', tables=[df.to_html(classes='data myTable')], titles=df.columns.values,years=years,teams=teams,positions=positions)

# This renders our home page HTML.
@app.route('/')
def render_home():
        return render_template('home.html')

# @app.route('/home')
# Gets player info from local dataframe, used to see if a player exists, is valid, etc...
def get_player(name):
    ######## Old csv file
    # df = pd.read_csv('./data/2023_fantasy.csv')
    df = pd.read_csv('./data/2023_fantasy_with_kickers.csv')
    df['Player'] = df['Player'].apply(lambda x: x.split('*')[0]).apply(lambda x: x.split('\\')[0])
    # print("PLAYER NAME: " + name)
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

# Gets fantasy stats from ProFootballReference with a given player ID.
def get_fant_table(player_id):
    url = 'https://www.pro-football-reference.com/players/' + player_id[0] + '/' + player_id + '/' + 'fantasy/2023/'
    print(url)
    table = pd.read_html(url)[0]
    # This goes through column value levels and if the column starts with Unnamed,
    # The value is replaced with "", we cant drop the column outright so we must
    # replace it with a "".
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

# This controls all functionality for searching and displaying search HTML. 
@app.route('/search')
@app.route('/search', methods=['GET', 'POST'])
def render_search():
    # Have to fix this eventually, because its the reason searching was slow. Using local data for now, instead of fetching data each time. Maybe set up a script to update local data once a week with new fantasy data and remove the old csv.
    players_info = get_top_10()
    error =False
    bye = False
    loading = False
    # print(players_info)
    if request.method == 'POST':
        loading = True
        # Retrieve the text from the textarea
        text = request.form.get('text')
        # If the text is blank just re render the home page fixes error.
        if text == "":
            search=False
            return render_template('search.html', players=players_info,search=search,player_names=player_names)
        table = get_player(text)[0]
        name = get_player(text)[1]
        status = getPlayerStatus(name)
        # print(status)
        results = prediction(name)
        # If the player wasnt found, an empty table is created, display player not found message.
        if table.empty:
            error = True
            search = True
            loading = False
            err_message = f"{name} not found, try again"
            return render_template('search.html', error=error, err_message=err_message,players=players_info,search=search,player_names=player_names,loading=loading)
        # If the Player is on a bye week, results will be "", so display that the player is on a bye week.
        elif results == '':
            bye = True
            bye_message = f'{name} is on a Bye Week'
            search = True
            return render_template('search.html',players=players_info,search=search,error=error, player_names=player_names, bye=bye, bye_message=bye_message, results=results, week=curr_week)
        #Player is found enter loop
        else:
            # If the player is out, print a predicition of 0.0 and display their status
            if status == "Out" or status == "Injured Reserve" or status == "Doubtful":
                color = "Red"
                return render_template('search.html', error=error,players=players_info,search=True,player_names=player_names,status=status,name=name,results=0.0,color=color, week=curr_week)
            # Player is healthy and prediction is found, display as usual.
            else:
                if status == "Questionable":
                    color = "Orange"
                else:
                    color = "Green"
                search = True
                loading = False
                return render_template('search.html', tables=[table.to_html(classes='data playerTable')], titles=table.columns.values, name=name, players=players_info, search=search,error=error,player_names=player_names, results=results,loading=loading,status=status,color=color, week=curr_week)
    else:
        search=False
        return render_template('search.html',players=players_info,search=False,error=error, player_names=player_names,loading=loading)

def get_top_10():
    # Commenting a lot of this out while I figure out a better way to fetch this data.
    # url = 'https://www.pro-football-reference.com/years/2023/fantasy.htm'
    # table = pd.read_html(url)[0]
    table = load_dataframe(2023)
    table['FantPt'] = pd.to_numeric(table['FantPt'])
    # table = table[table[('Unnamed: 1_level_0', 'Player')] != 'Player']
    # table[('Fantasy', 'FantPt')] = pd.to_numeric(table[('Fantasy', 'FantPt')])
    # table = table.sort_values(by=('Fantasy', 'FantPt'), ascending=False)
    table = table.sort_values(by=('FantPt'), ascending=False)
    table = table.head(10)
    table = table.reset_index(drop=True)
    # new_columns = []
    # for col in table.columns:
    #     new_col = []
    #     for level in col:
    #         if "Unnamed" in level:
    #             new_col.append('')
    #         else:
    #             new_col.append(level)
    #     new_columns.append(tuple(new_col))
    # table.columns = pd.MultiIndex.from_tuples(new_columns)
    # table = table.drop(columns=('Rk'), level=-1)
    table.fillna(0,inplace=True)

    # players_list = table[('', 'Player')].tolist()
    # positions_list = table[('', 'FantPos')].tolist()
    # teams_list = table[('', 'Tm')].tolist()
    # points_list = table[('Fantasy', 'FantPt')].tolist()
    players_list = table['Player'].tolist()
    positions_list = table['FantPos'].tolist()
    teams_list = table['Tm'].tolist()
    points_list = table['FantPt'].tolist()
    rank_list = list(map(lambda i : i + 1, table.index.tolist()))

    players_info = [{'Name': player, 'Position': position, 'Team': team, 'Points':points, 'Rank':rank} for player, position, team, points, rank in zip(players_list, positions_list, teams_list,points_list, rank_list)]
    return players_info

def get_team(name):
    table, id = get_player(name)
    data = preprocessing(table)
    return data['Tm'][0]

# Gets the  for a given team from schedule.csv
def get_opp(team):
    schedule = pd.read_csv('./data/Schedule.csv')
    game = schedule.query('Week == (@curr_week) and (Home == @team or Away == @team)')
    # opp = 'Bye Week'
    # print(game)
    if game.query('Home == @team').empty and game.query('Away == @team').empty:
        opp = 'Bye Week'
    elif game.query('Home == @team').empty:
        opp = game['Home'].item()
    elif game.query('Away == @team').empty:
        opp = game['Away'].item()
    return opp

# Creates prediction table for prediction() function
def create_pred_table(name):
    sched = pd.read_csv('./data/2023_schedule.csv')
    team = get_team(name)
    opp = get_opp(team)
    if opp == 'Bye Week':
        return pd.DataFrame()
    else:
        opponent = 'Opp_' + opp
        week = sched['G#'][0].item()
        pred_dict = {'G#': [week], opponent: [1.0]}
        pred_table = pd.DataFrame(pred_dict)
        not_playing = np.zeros(1)
        for i in teams:
            if 'Opp_' + i not in pred_table.columns:
                pred_table['Opp_' + i] = not_playing
        return pred_table

# This preprocesses our data, gets called in prediction() function
def preprocessing(player_table):
    #get the table
    df = player_table
    if df.empty:
        return pd.DataFrame()   
    #remove unneeded columns from a higher level
    table = df.drop(['Inside 20', 'Inside 10', 'Snap Counts'], axis=1, errors='ignore')
    #make only one level of column names
    table.columns = table.columns.get_level_values(-1)
    #drop columns not needed for training
    tab = table.drop(['Date', 'Pos', 'DKPt', 'FDPt', 'Home/Away',  'Result'], axis=1, errors='ignore')
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

# This does the prediction for the player, calls preprocessing and returns mean value
def prediction(name):
    table, pid = get_player(name)
    train = preprocessing(table)
    if train.empty:
        return ''
    train_data = train.drop('Tm', axis=1)
    pred_data = create_pred_table(name)
    if pred_data.empty:
        return ''
    else:
        y_train = train_data['FantPt'].values
        X_train = train_data.drop('FantPt', axis=1).values
        lm_r = Ridge(alpha=10).fit(X_train, y_train)
        lm_l = Lasso().fit(X_train, y_train)
        lm_en = ElasticNet().fit(X_train, y_train)
        ridge_pred = lm_r.predict(pred_data)[0]
        lasso_pred = lm_l.predict(pred_data)[0]
        elastic_net_pred = lm_en.predict(pred_data)[0]
        # Average the 3 scores and display that. Gets us the best results overall.
        mean = np.mean([ridge_pred, lasso_pred, elastic_net_pred])
        mean_rounded = np.around(mean, decimals=2)
        return mean_rounded


# @app.route('/tables')
# @app.route('/tables', methods=['GET', 'POST'])
# def filter_data():
#     print("Entered")
#     team = request.form.get('selected_team')
#     position = request.form.get('selected_positon')
#     year = request.form.get('selected_year')
#     # print(team,position,year)
#     # filtered_data = data
#     if year is None:
#         year = session.get('selected_year', 2022)  # Get the selected year from the session or default to 2022
#     else:
#         session['selected_year'] = year 
#     df = load_dataframe(year)

#     if team:
#         df = df[df['Tm'] == team]

#     if position:
#         df = df[df['FantPos'] == position]
#     print(team,position,year)

#     # return render_template('tables.html', filtered_data=df.to_html())
#     return render_template('tables.html', tables=[df.to_html(classes='data myTable')], titles=df.columns.values)

# Gets Injured Player list and drops comments column
def getInjuredPlayers():
    espn_url = 'https://www.espn.com/nfl/injuries'
    espn_df = pd.read_html(espn_url)
    # Concat all team dfs into one and drop unneeded columns
    merged_df = pd.concat(espn_df)
    merged_df = merged_df.drop('COMMENT', axis=1)
    merged_df = merged_df.reset_index(drop=True)
    # We only care about offensive positions so filter out others.
    merged_df = merged_df[merged_df['POS'].isin(positions)]
    merged_df = merged_df.reset_index(drop=True)
    return merged_df

# Returns status of the player if theyre in the data frame,
# Return Healthy if the player isnt on the injured list.
def getPlayerStatus(name):
    injured_df = getInjuredPlayers()
    player_row = injured_df[injured_df['NAME'] == name]
    if not player_row.empty:
        return player_row['STATUS'].values[0]
    else:
        return "Healthy"

# Gets rid of unneeded columns from out dataframe.
def clean_df(df):
    df.drop(['Rk', '2PM', '2PP', 'DKPt', 'FDPt', 'VBD', 'PosRank', 'OvRank', 'PPR', 'Fmb', 'GS', 'PlayerID'], axis=1, inplace=True, errors='ignore')
    df.fillna(0, inplace=True)
    df['Player'] = df['Player'].apply(lambda x: x.split('*')[0]).apply(lambda x: x.split('\\')[0])
    df.rename({
    'TD': 'PassingTD',
    'TD.1': 'RushingTD',
    'TD.2': 'ReceivingTD',
    'TD.3': 'TotalTD',
    'Yds': 'PassingYDs',
    'Yds.1': 'RushingYDs',
    'Yds.2': 'ReceivingYDs',
    'Att': 'PassingAtt',
    'Att.1': 'RushingAtt',
    'FantPt': 'FantasyPts'
    }, axis=1, inplace=True)
    return df