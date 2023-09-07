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
@app.route('/')
def render_home():
    return render_template('home.html')