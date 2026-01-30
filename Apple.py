from flask import Flask, render_template, request, redirect, url_for, session
from google import genai
import pandas as pd
import os
import requests
import datetime
import finnhub

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
finnhub_client = finnhub.Client(api_key=API_KEY)

gemini_client = genai.Client(api_key='AIzaSyCK_XQtbb3rsf5CCzaWuelH00S_qdURd-U')

# --- UTILITY FUNCTIONS ---

def get_stock_price(symbol):
    """Fetches price and returns 0.0 if failed"""
    try:
        url = f'https://finnhub.io/api/v1/quote?symbol={symbol.upper()}&token={API_KEY}'
        r = requests.get(url, timeout=5)
        data = r.json()
        price = float(data.get('c', 0))
        return price if price > 0 else 0.0
    except:
        return 0.0

def check_achievements(username):
    """Safely checks for easy-to-reach achievements"""
    df = pd.read_csv(DB_FILE, dtype=str)
    user_rows = df[df['username'] == username]
    if user_rows.empty:
        return
        
    idx = user_rows.index[0]
    
    try:
        balance = float(df.at[idx, 'balance'])
        stocks_raw = str(df.at[idx, 'stocks_held'])
        # Create a list of all shares held
        stocks_list = [s.strip() for s in stocks_raw.split(',')] if stocks_raw not in ['nan', 'None', '', ' '] else []
        # Create a set to count unique types of stocks
        unique_stocks = set(stocks_list)
        
        existing_ach_raw = str(df.at[idx, 'achievements'])
        current_achievements = [a.strip() for a in existing_ach_raw.split(',')] if existing_ach_raw not in ['nan', 'None', ''] else []
    except:
        return

    new_awards = []

    # ACHIEVEMENT: First Buy (Own at least 1 share)
    if len(stocks_list) >= 1 and "First Buy" not in current_achievements:
        new_awards.append("First Buy")

    # ACHIEVEMENT: Penny Pincher (Spent half your cash; balance below $5,000)
    if balance < 5000 and "Penny Pincher" not in current_achievements:
        new_awards.append("Penny Pincher")

    # ACHIEVEMENT: Investor (Own 5 or more total shares)
    if len(stocks_list) >= 5 and "Investor" not in current_achievements:
        new_awards.append("Investor")

    # ACHIEVEMENT: Diversified (Own 3 or more different types of stocks)
    if len(unique_stocks) >= 3 and "Diversified" not in current_achievements:
        new_awards.append("Diversified")

    if new_awards:
        # Combine old and new, removing any 'nan' junk
        combined = [a for a in (current_achievements + new_awards) if a and a != 'nan']
        df.at[idx, 'achievements'] = ", ".join(combined)
        df.to_csv(DB_FILE, index=False)

# --- ROUTES ---

@app.route('/')
def home():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    df = pd.read_csv(DB_FILE, dtype=str)
    user_data = df[df['username'] == session['username']].iloc[0].to_dict()
    
    stocks_held_raw = str(user_data.get('stocks_held', ''))
    stocks_list = [s.strip() for s in stocks_held_raw.split(',')] if stocks_held_raw not in ['nan', 'None', '', ' '] else []
    
    portfolio_value = 0.0
    price_cache = {}

    for ticker in stocks_list:
        if ticker not in price_cache:
            price_cache[ticker] = get_stock_price(ticker)
        portfolio_value += price_cache[ticker]
    
    return render_template('index.html', user=user_data, portfolio_value=portfolio_value)

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
    
    portfolio_value = 0.0
    price_cache = {}
    for ticker in stocks_list:
        if ticker not in price_cache:
            price_cache[ticker] = get_stock_price(ticker)
        portfolio_value += price_cache[ticker]
        
    return render_template('market.html', user=user_data, portfolio_value=portfolio_value)

@app.route('/leaderboard')
def leaderboard():
    if 'username' not in session:
        return redirect(url_for('login'))

    df = pd.read_csv(DB_FILE, dtype=str)
    
    # --- ADD THIS PART TO FIX THE ERROR ---
    user_rows = df[df['username'] == session['username']]
    if user_rows.empty:
        session.clear()
        return redirect(url_for('login'))
    user_data = user_rows.iloc[0].to_dict()
    # ---------------------------------------

    leaderboard_entries = []
    price_cache = {}

    for _, row in df.iterrows():
        cash = float(row['balance'])
        stocks_held_raw = str(row['stocks_held'])
        stocks_list = [s.strip() for s in stocks_held_raw.split(',')] if stocks_held_raw not in ['nan', 'None', ''] else []
        
        portfolio_stock_value = 0.0
        for ticker in stocks_list:
            if ticker not in price_cache:
                price_cache[ticker] = get_stock_price(ticker)
            portfolio_stock_value += price_cache[ticker]
        
        total_net_worth = cash + portfolio_stock_value
        leaderboard_entries.append({
            'username': row['username'],
            'cash': cash,
            'stock_value': portfolio_stock_value,
            'net_worth': total_net_worth
        })

    sorted_leaderboard = sorted(leaderboard_entries, key=lambda x: x['net_worth'], reverse=True)
    
    # PASS 'user=user_data' HERE
    return render_template('leaderboard.html', user=user_data, users=sorted_leaderboard)

@app.route('/news')
def news_page():
    if 'username' not in session:
        return redirect(url_for('login'))

    df = pd.read_csv(DB_FILE, dtype=str)
    user_data = df[df['username'] == session['username']].iloc[0].to_dict()
    
    stocks_held_raw = str(user_data.get('stocks_held', ''))
    stocks_list = [s.strip() for s in stocks_held_raw.split(',')] if stocks_held_raw not in ['nan', 'None', '', ' '] else []
    
    portfolio_value = 0.0
    price_cache = {}
    for ticker in stocks_list:
        if ticker not in price_cache:
            price_cache[ticker] = get_stock_price(ticker)
        portfolio_value += price_cache[ticker]

    try:
        raw_news = finnhub_client.general_news('general', min_id=0)
        headlines = [item['headline'] for item in raw_news[:10]]
        
        prompt = (
            f"Analyze these market headlines: {headlines}. "
            "1. Start with one word: 'BULLISH', 'BEARISH', or 'NEUTRAL'. "
            "2. Provide 3-4 bite-sized bullet points summarizing the news. "
            "Use HTML tags like <b> and <ul> for formatting."
        )
        
        response = gemini_client.models.generate_content(
            model='gemini-1.5-flash', 
            contents=prompt
        )
        
        full_text = response.text
        sentiment = "NEUTRAL"
        if "BULLISH" in full_text.upper(): sentiment = "BULLISH"
        elif "BEARISH" in full_text.upper(): sentiment = "BEARISH"
        
        summary = full_text.replace("BULLISH", "").replace("BEARISH", "").replace("NEUTRAL", "").strip()
    except Exception as e:
        sentiment = "UNKNOWN"
        summary = f"Error loading news: {str(e)}"

    return render_template('news.html', 
                           user=user_data, 
                           portfolio_value=portfolio_value, 
                           summary=summary, 
                           sentiment=sentiment,
                           now=datetime.datetime.now())

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
    
    user_rows = df[df['username'] == session['username']]
    if user_rows.empty:
        return redirect(url_for('login'))
        
    idx = user_rows.index[0]
    current_balance = float(df.at[idx, 'balance'])
    
    if current_balance >= total_cost:
        df.at[idx, 'balance'] = str(round(current_balance - total_cost, 2))
        new_shares_string = ", ".join([ticker] * quantity)
        current_stocks = str(df.at[idx, 'stocks_held'])
        
        if current_stocks in ['nan', 'None', '', ' ']:
            df.at[idx, 'stocks_held'] = new_shares_string
        else:
            df.at[idx, 'stocks_held'] = f"{current_stocks}, {new_shares_string}"
        
        df.to_csv(DB_FILE, index=False)
        check_achievements(session['username'])
        return redirect(request.referrer or url_for('home'))
        
    return f"Insufficient funds for {quantity} shares! <a href='/'>Go back</a>"

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
    user_rows = df[df['username'] == session['username']]
    if user_rows.empty:
        return redirect(url_for('login'))
        
    idx = user_rows.index[0]
    stocks_held_raw = str(df.at[idx, 'stocks_held'])
    current_stocks = [s.strip() for s in stocks_held_raw.split(',')] if stocks_held_raw not in ['nan', 'None', ''] else []
    
    owned_count = current_stocks.count(ticker)
    
    if owned_count >= qty_to_sell:
        for _ in range(qty_to_sell):
            current_stocks.remove(ticker)
        df.at[idx, 'stocks_held'] = ', '.join(current_stocks)
        current_balance = float(df.at[idx, 'balance'])
        df.at[idx, 'balance'] = str(round(current_balance + (price * qty_to_sell), 2))
        # Trigger the Quick Seller badge manually on the first sale
        existing_achs = str(df.at[idx, 'achievements'])
        if "Quick Seller" not in existing_achs:
            # Add it to the string, cleaning up leading commas
            if existing_achs in ['nan', 'None', '']:
                df.at[idx, 'achievements'] = "Quick Seller"
            else:
                df.at[idx, 'achievements'] = f"{existing_achs}, Quick Seller"
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