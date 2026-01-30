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

@app.route('/market')
def market():
    """Displays the market trends and stock graphs page"""
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('market.html')

@app.route('/buy', methods=['POST'])
def buy():
    if 'username' not in session:
        return redirect(url_for('login'))

    ticker = request.form.get('ticker').upper()
    
    # FIX 1: Ensure we are grabbing the quantity as an integer
    try:
        quantity = int(request.form.get('quantity', 1))
    except ValueError:
        return "Invalid quantity! <a href='/'>Go back</a>"
        
    price = get_stock_price(ticker)
    if price <= 0:
        return "Ticker not found. <a href='/'>Go back</a>"

    # Total cost math
    total_cost = price * quantity

    # Read with dtype=str to keep AAPL from crashing the float64 column
    df = pd.read_csv(DB_FILE, dtype=str)
    idx = df[df['username'] == session['username']].index[0]
    
    current_balance = float(df.at[idx, 'balance'])
    
    if current_balance >= total_cost:
        # Update balance
        df.at[idx, 'balance'] = str(round(current_balance - total_cost, 2))
        
        # FIX 2: This is the "asscheeks" part—we must repeat the ticker 'quantity' times
        new_shares_string = ", ".join([ticker] * quantity)
        
        current_stocks = str(df.at[idx, 'stocks_held'])
        
        # Handle the very first purchase vs adding to an existing list
        if current_stocks in ['nan', 'None', '', ' ']:
            df.at[idx, 'stocks_held'] = new_shares_string
        else:
            df.at[idx, 'stocks_held'] = f"{current_stocks}, {new_shares_string}"
        
        df.to_csv(DB_FILE, index=False)
        return redirect(url_for('home'))
        
    return f"Insufficient funds for {quantity} shares! <a href='/'>Go back</a>"

@app.route('/sell', methods=['POST'])
def sell():
    if 'username' not in session:
        return redirect(url_for('login'))

    ticker = request.form.get('ticker').upper()
    
    # Grab the quantity from your new HTML input
    try:
        qty_to_sell = int(request.form.get('quantity', 1))
    except ValueError:
        return "Invalid quantity! <a href='/'>Go back</a>"
        
    price = get_stock_price(ticker)
    if price <= 0:
        return "API Error! Could not get price. <a href='/'>Go back</a>"

    # Read as string to prevent the float64 crash
    df = pd.read_csv(DB_FILE, dtype=str)
    idx = df[df['username'] == session['username']].index[0]
    
    # Split holdings into a list and clean up whitespace
    stocks_held_raw = str(df.at[idx, 'stocks_held'])
    current_stocks = [s.strip() for s in stocks_held_raw.split(',')] if stocks_held_raw not in ['nan', 'None', ''] else []
    
    # CHECK: Do you actually have enough shares?
    owned_count = current_stocks.count(ticker)
    
    if owned_count >= qty_to_sell:
        # Loop to remove the exact number of shares requested
        for _ in range(qty_to_sell):
            current_stocks.remove(ticker)
        
        # Save the shortened list back as a string
        df.at[idx, 'stocks_held'] = ', '.join(current_stocks)
        
        # Add the TOTAL value (Price * Qty) back to balance
        current_balance = float(df.at[idx, 'balance'])
        total_sale_value = price * qty_to_sell
        df.at[idx, 'balance'] = str(round(current_balance + total_sale_value, 2))
        
        df.to_csv(DB_FILE, index=False)
        return redirect(url_for('home'))
    
    return f"Error: You only own {owned_count} shares of {ticker}! <a href='/'>Go back</a>"

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    if not os.path.exists(DB_FILE):
        pd.DataFrame(columns=['username', 'password', 'balance', 'stocks_held']).to_csv(DB_FILE, index=False)
    app.run(debug=True)