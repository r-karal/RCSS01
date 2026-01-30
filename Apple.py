from flask import Flask, render_template, request, redirect, url_for, session
from google import genai
import pandas as pd
import os
import requests
import datetime
import finnhub
import csv

app = Flask(__name__)
app.secret_key = 'codesprint_hackathon_2026'

app.config.update(
    SESSION_PERMANENT=False,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_FILE = os.path.join(BASE_DIR, 'users.csv')
TRADES_FILE = os.path.join(BASE_DIR, 'transactions.csv') 
API_KEY = 'd5u4sppr01qtjet21380d5u4sppr01qtjet2138g'
finnhub_client = finnhub.Client(api_key=API_KEY)

gemini_client = genai.Client(api_key='AIzaSyCK_XQtbb3rsf5CCzaWuelH00S_qdURd-U')

# --- UTILITY FUNCTIONS ---

def get_stock_price(symbol):
    try:
        url = f'https://finnhub.io/api/v1/quote?symbol={symbol.upper()}&token={API_KEY}'
        r = requests.get(url, timeout=5)
        data = r.json()
        price = float(data.get('c', 0))
        return price if price > 0 else 0.0
    except:
        return 0.0

def check_achievements(username):
    df = pd.read_csv(DB_FILE, dtype=str)
    user_rows = df[df['username'] == username]
    if user_rows.empty:
        return
    idx = user_rows.index[0]
    try:
        balance = float(df.at[idx, 'balance'])
        stocks_raw = str(df.at[idx, 'stocks_held'])
        stocks_list = [s.strip() for s in stocks_raw.split(',')] if stocks_raw not in ['nan', 'None', '', ' '] else []
        unique_stocks = set(stocks_list)
        existing_ach_raw = str(df.at[idx, 'achievements'])
        current_achievements = [a.strip() for a in existing_ach_raw.split(',')] if existing_ach_raw not in ['nan', 'None', ''] else []
    except:
        return

    new_awards = []
    if len(stocks_list) >= 1 and "First Buy" not in current_achievements:
        new_awards.append("First Buy")
    if balance < 5000 and "Penny Pincher" not in current_achievements:
        new_awards.append("Penny Pincher")
    if len(stocks_list) >= 5 and "Investor" not in current_achievements:
        new_awards.append("Investor")
    if len(unique_stocks) >= 3 and "Diversified" not in current_achievements:
        new_awards.append("Diversified")

    if new_awards:
        combined = [a for a in (current_achievements + new_awards) if a and a != 'nan']
        df.at[idx, 'achievements'] = ", ".join(combined)
        df.to_csv(DB_FILE, index=False)

# --- ROUTES ---

@app.route('/')
def home():
    if 'username' not in session:
        return redirect(url_for('login'))
    df = pd.read_csv(DB_FILE, dtype=str)
    user_rows = df[df['username'] == session['username']]
    if user_rows.empty:
        session.clear()
        return redirect(url_for('login'))
    user_data = user_rows.iloc[0].to_dict()
    stocks_held_raw = str(user_data.get('stocks_held', ''))
    stocks_list = [s.strip() for s in stocks_held_raw.split(',')] if stocks_held_raw not in ['nan', 'None', '', ' '] else []
    
    portfolio_value = 0.0
    price_cache = {}
    for ticker in stocks_list:
        if ticker not in price_cache:
            price_cache[ticker] = get_stock_price(ticker)
        portfolio_value += price_cache[ticker]
    
    try:
        news_data = finnhub_client.general_news('general', min_id=0)[:8]
    except:
        news_data = []

    return render_template('index.html', user=user_data, portfolio_value=portfolio_value, news=news_data)

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
        new_user = {'username': u, 'password': p, 'balance': '10000.0', 'stocks_held': '', 'achievements': ''}
        df = pd.concat([df, pd.DataFrame([new_user])], ignore_index=True)
        df.to_csv(DB_FILE, index=False)
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/market')
def market():
    if 'username' not in session:
        return redirect(url_for('login'))
    df = pd.read_csv(DB_FILE, dtype=str)
    user_data = df[df['username'] == session['username']].iloc[0].to_dict()
    stocks_held_raw = str(user_data.get('stocks_held', ''))
    stocks_list = [s.strip() for s in stocks_held_raw.split(',')] if stocks_held_raw not in ['nan', 'None', '', ' '] else []
    portfolio_value = sum(get_stock_price(ticker) for ticker in stocks_list)
    return render_template('market.html', user=user_data, portfolio_value=portfolio_value)

@app.route('/leaderboard')
def leaderboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    df = pd.read_csv(DB_FILE, dtype=str)
    user_rows = df[df['username'] == session['username']]
    if user_rows.empty:
        session.clear()
        return redirect(url_for('login'))
    user_data = user_rows.iloc[0].to_dict()
    leaderboard_entries = []
    for _, row in df.iterrows():
        cash = float(row['balance'])
        stocks_raw = str(row['stocks_held'])
        s_list = [s.strip() for s in stocks_raw.split(',')] if stocks_raw not in ['nan', 'None', ''] else []
        s_val = sum(get_stock_price(t) for t in s_list)
        leaderboard_entries.append({'username': row['username'], 'cash': cash, 'stock_value': s_val, 'net_worth': cash + s_val})
    sorted_lb = sorted(leaderboard_entries, key=lambda x: x['net_worth'], reverse=True)
    return render_template('leaderboard.html', user=user_data, users=sorted_lb)

@app.route('/history')
def transaction_history():
    if 'username' not in session:
        return redirect(url_for('login'))
    df_users = pd.read_csv(DB_FILE, dtype=str)
    user_data = df_users[df_users['username'] == session['username']].iloc[0].to_dict()
    if not os.path.exists(TRADES_FILE):
        pd.DataFrame(columns=['timestamp','username','ticker','type','quantity','price','total_cost']).to_csv(TRADES_FILE, index=False)
    df_trades = pd.read_csv(TRADES_FILE)
    user_history = df_trades[df_trades['username'] == session['username']].sort_values(by='timestamp', ascending=False)
    return render_template('history.html', user=user_data, transactions=user_history.to_dict('records'))

@app.route('/buy', methods=['POST'])
def buy():
    if 'username' not in session:
        return redirect(url_for('login'))
    ticker = request.form.get('ticker').upper()
    try:
        quantity = int(request.form.get('quantity', 1))
    except ValueError:
        return "Invalid quantity! <a href='/'>Go back</a>"
    price = get_stock_price(ticker)
    if price <= 0:
        return "Ticker not found. <a href='/'>Go back</a>"
    total_cost = price * quantity
    df = pd.read_csv(DB_FILE, dtype=str)
    idx = df[df['username'] == session['username']].index[0]
    current_balance = float(df.at[idx, 'balance'])
    
    if current_balance >= total_cost:
        df.at[idx, 'balance'] = str(round(current_balance - total_cost, 2))
        new_shares = ", ".join([ticker] * quantity)
        current_stocks = str(df.at[idx, 'stocks_held'])
        df.at[idx, 'stocks_held'] = new_shares if current_stocks in ['nan', 'None', '', ' '] else f"{current_stocks}, {new_shares}"
        df.to_csv(DB_FILE, index=False)
        
        # --- LOG TRANSACTION ---
        file_exists = os.path.isfile(TRADES_FILE)
        with open(TRADES_FILE, mode='a', newline='') as f:
            fieldnames = ['timestamp', 'username', 'ticker', 'type', 'quantity', 'price', 'total_cost']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow({
                'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'username': session['username'],
                'ticker': ticker,
                'type': 'BUY',
                'quantity': quantity,
                'price': price,
                'total_cost': round(total_cost, 2)
            })
        
        check_achievements(session['username'])
        return redirect(request.referrer or url_for('home'))
        
    return f"Insufficient funds! <a href='/'>Go back</a>"

@app.route('/sell', methods=['POST'])
def sell():
    if 'username' not in session:
        return redirect(url_for('login'))
    ticker = request.form.get('ticker').upper()
    try:
        qty_to_sell = int(request.form.get('quantity', 1))
    except ValueError:
        return "Invalid quantity! <a href='/'>Go back</a>"
    price = get_stock_price(ticker)
    if price <= 0:
        return "API Error! <a href='/'>Go back</a>"
    df = pd.read_csv(DB_FILE, dtype=str)
    idx = df[df['username'] == session['username']].index[0]
    stocks_raw = str(df.at[idx, 'stocks_held'])
    stocks = [s.strip() for s in stocks_raw.split(',')] if stocks_raw not in ['nan', 'None', ''] else []
    owned_count = stocks.count(ticker)
    
    if owned_count >= qty_to_sell:
        for _ in range(qty_to_sell):
            stocks.remove(ticker)
        df.at[idx, 'stocks_held'] = ', '.join(stocks)
        current_balance = float(df.at[idx, 'balance'])
        df.at[idx, 'balance'] = str(round(current_balance + (price * qty_to_sell), 2))
        
        # --- LOG TRANSACTION (CORRECTED INDENTATION & TYPE) ---
        file_exists = os.path.isfile(TRADES_FILE)
        with open(TRADES_FILE, mode='a', newline='') as f:
            fieldnames = ['timestamp', 'username', 'ticker', 'type', 'quantity', 'price', 'total_cost']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow({
                'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'username': session['username'],
                'ticker': ticker,
                'type': 'SELL',
                'quantity': qty_to_sell,
                'price': price,
                'total_cost': round(price * qty_to_sell, 2)
            })
        
        existing_achs = str(df.at[idx, 'achievements'])
        if "Quick Seller" not in existing_achs:
            df.at[idx, 'achievements'] = "Quick Seller" if existing_achs in ['nan', 'None', ''] else f"{existing_achs}, Quick Seller"
        
        df.to_csv(DB_FILE, index=False)
        check_achievements(session['username'])
        return redirect(request.referrer or url_for('home'))
    
    return f"Error: You only own {owned_count} shares! <a href='/'>Go back</a>"

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    if not os.path.exists(DB_FILE):
        pd.DataFrame(columns=['username', 'password', 'balance', 'stocks_held', 'achievements']).to_csv(DB_FILE, index=False)
    app.run(debug=True)