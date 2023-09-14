from flask import *
import numpy as np
import pandas as pd


app = Flask(__name__)
app.secret_key = 'SECRET'

def load_dataframe(year):
    csv_file = f"{year}_fantasy.csv"
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
        get_player(text)
    return render_template('home.html')

def get_player(name):
    df = pd.read_csv('2022_fantasy.csv')
    df['Player'] = df['Player'].apply(lambda x: x.split('*')[0]).apply(lambda x: x.split('\\')[0])
    player = df[df['Player'] == name]
    if (player.empty):
        print('No such player')
    else:
        id = str(player['PlayerID'][0])
        get_fant_table(id)

def get_fant_table(player_id):
    url = 'https://www.pro-football-reference.com/players/' + player_id[0] + '/' + player_id + '/' + 'fantasy/2022/'
    table = pd.read_html(url)[0]
    print(table.head())

