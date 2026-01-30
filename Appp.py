from flask import Flask, render_template, request, redirect, url_for, session
import pandas as pd
import os
import requests

app = Flask(__name__)
app.secret_key = 'codesprint_hackathon_2026'

# Configuration for automatic sign-out
app.config.update(
    SESSION_PERMANENT=False,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_FILE = os.path.join(BASE_DIR, 'users.csv')
API_KEY = 'd5u4sppr01qtjet21380d5u4sppr01qtjet2138g'

def get_stock_price(symbol):
    """Fetches price and returns 0.0 if failed"""
    try:
        url = f'https://finnhub.io/api/v1/quote?symbol={symbol.upper()}&token={API_KEY}'
        r = requests.get(url, timeout=5)
        data = r.json()
        price = float(data.get('c', 0))
        if price == 0:
            return 0.0
        return price
    except:
        return 0.0

@app.route('/')
def home():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    # Force everything to strings so Pandas doesn't guess "float64"
    df = pd.read_csv(DB_FILE, dtype=str)
    user_data = df[df['username'] == session['username']]
    
    if user_data.empty:
        session.clear()
        return redirect(url_for('login'))
        
    return render_template('index.html', user=user_data.iloc[0].to_dict())

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u, p = request.form.get('username'), request.form.get('password')
        df = pd.read_csv(DB_FILE, dtype=str)
        user = df[(df['username'] == u) & (df['password'] == p)]
        if not user.empty:
            session['username'] = u
            return redirect(url_for('home'))
        return "Invalid! <a href='/login'>Try again</a>"
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        u, p = request.form.get('username'), request.form.get('password')
        df = pd.read_csv(DB_FILE, dtype=str)
        if u in df['username'].values:
            return "Exists! <a href='/signup'>Try again</a>"
        
        # Save balance as a string immediately
        new_user = {'username': u, 'password': p, 'balance': '10000.0', 'stocks_held': ''}
        df = pd.concat([df, pd.DataFrame([new_user])], ignore_index=True)
        df.to_csv(DB_FILE, index=False)
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/buy', methods=['POST'])
def buy():
    if 'username' not in session:
        return redirect(url_for('login'))

    ticker = request.form.get('ticker').upper()
    price = get_stock_price(ticker)
    
    if price <= 0:
        return "Ticker not found or API busy. <a href='/'>Go back</a>"

    # CRITICAL: Read everything as a string (Object)
    df = pd.read_csv(DB_FILE, dtype=str)
    idx = df[df['username'] == session['username']].index[0]
    
    # Convert ONLY for the math, then back to string
    current_balance = float(df.at[idx, 'balance'])
    
    if current_balance >= price:
        new_balance = round(current_balance - price, 2)
        df.at[idx, 'balance'] = str(new_balance)
        
        # Save the stock ticker as a string
        current_stocks = str(df.at[idx, 'stocks_held'])
        if current_stocks in ['nan', 'None', '', ' ']:
            df.at[idx, 'stocks_held'] = ticker
        else:
            df.at[idx, 'stocks_held'] = f"{current_stocks}, {ticker}"
        
        df.to_csv(DB_FILE, index=False)
        return redirect(url_for('home'))
    return "Insufficient funds! <a href='/'>Go back</a>"

@app.route('/sell', methods=['POST'])
def sell():
    if 'username' not in session:
        return redirect(url_for('login'))

    ticker = request.form.get('ticker').upper()
    price = get_stock_price(ticker)
    
    if price <= 0:
        return "API Error! Could not get current price to sell. <a href='/'>Go back</a>"

    df = pd.read_csv(DB_FILE, dtype=str)
    idx = df[df['username'] == session['username']].index[0]
    
    current_stocks = str(df.at[idx, 'stocks_held']).split(', ')
    
    if ticker in current_stocks:
        # Remove ONE instance of the stock
        current_stocks.remove(ticker)
        df.at[idx, 'stocks_held'] = ', '.join(current_stocks)
        
        # Add the money back
        current_balance = float(df.at[idx, 'balance'])
        df.at[idx, 'balance'] = str(round(current_balance + price, 2))
        
        df.to_csv(DB_FILE, index=False)
        return redirect(url_for('home'))
    else:
        return "You don't own this stock! <a href='/'>Go back</a>"
        
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    if not os.path.exists(DB_FILE):
        pd.DataFrame(columns=['username', 'password', 'balance', 'stocks_held']).to_csv(DB_FILE, index=False)
    app.run(debug=True)