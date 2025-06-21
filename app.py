from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import requests, sqlite3, time, os
import time
from datetime import datetime
from datetime import timedelta
COINCAP_KEY = os.getenv("COINCAP_KEY")

...
time.sleep(1)  # تأخير 1 ثانية بين الطلبات (غير مثالي لكنه يحل في حالات التطوير)
favorites_cache = {"timestamp": 0, "data": {}}


app = Flask(__name__)
app.permanent_session_lifetime = timedelta(minutes=10)
app.secret_key = "sehr_geheimer_schlussel"

coingecko_cache = {"timestamp": 0, "data": []}

def init_db():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    
    # جدول المستخدمين
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    """)
    
    # جدول العملات المفضلة
    c.execute("""
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            coin TEXT,
            UNIQUE(user_id, coin)
        )
    """)

    c.execute("""
CREATE TABLE IF NOT EXISTS favorite_cache (
    coin_id TEXT PRIMARY KEY,
    name TEXT,
    symbol TEXT,
    image TEXT,
    price_eur REAL,
    price_usd REAL,
    change REAL,
    last_updated INTEGER
)
""")
    

    c.execute("""
CREATE TABLE IF NOT EXISTS wallet (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    coin TEXT,
    amount REAL,
    buy_price REAL,
    buy_date TEXT
)
""")

    conn.commit()
    conn.close()


def get_top50_coins():
    global coingecko_cache
    if time.time() - coingecko_cache["timestamp"] < 900:
        return coingecko_cache["data"]
    try:
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            "vs_currency": "eur",
            "order": "market_cap_desc",
            "per_page": 50,
            "page": 1,
            "sparkline": False
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        coingecko_cache = {"timestamp": time.time(), "data": data}
        return data
    except Exception as e:
        print(f"CoinGecko API error: {e}")
        return []

def get_exchange_rate():
    try:
        url = "https://api.exchangerate.host/latest?base=USD&symbols=EUR"
        response = requests.get(url)
        return response.json()["rates"]["EUR"]
    except:
        return 0.92
def update_favorite_cache(coin_data, exchange_rate):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    for coin in coin_data:
        c.execute("""
            INSERT OR REPLACE INTO favorite_cache
            (coin_id, name, symbol, image, price_eur, price_usd, change, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            coin["id"],
            coin["name"],
            coin["symbol"],
            coin["image"],
            coin["current_price"],
            round(coin["current_price"] / exchange_rate, 4),
            round(coin.get("price_change_percentage_24h", 0), 2),
            int(time.time())
        ))
    conn.commit()
    conn.close()

def get_crypto_news():
    try:
        url = "https://min-api.cryptocompare.com/data/v2/news/?lang=EN"
        res = requests.get(url)
        if res.status_code == 200:
            data = res.json().get("Data", [])
            return [
                {
                    "title": n.get("title", "Kein Titel"),
                    "link": n.get("url", "#"),
                    "image": n.get("imageurl", "https://via.placeholder.com/300x150?text=No+Image"),
                    "source": n.get("source_info", {}).get("name", "CryptoCompare"),
                    "time": time.strftime('%Y-%m-%d %H:%M', time.gmtime(n.get("published_on", 0)))
                }
                for n in data[:9]
            ]
    except Exception as e:
        print("Fehler beim Laden der CryptoCompare News:", e)
    return []
def get_coindesk_news():
    try:
        url = "https://api.rss2json.com/v1/api.json"
        params = {
            "rss_url": "https://www.coindesk.com/arc/outboundfeeds/rss/",
            "api_key": "",  # اختياري - يمكن تركه فارغ
            "count": 5
        }
        res = requests.get(url, params=params)
        res.raise_for_status()
        data = res.json()
        return data.get("items", [])
    except Exception as e:
        print("Fehler beim Laden der CoinDesk-News:", e)
        return []
def get_fear_greed_index():
    try:
        res = requests.get("https://api.alternative.me/fng/")
        data = res.json()["data"][0]
        return {
            "value": data["value"],
            "classification": data["value_classification"],
            "time": data["timestamp"]
        }
    except Exception as e:
        print("FNG Error:", e)
        return None
def get_crypto_joke():
    try:
        res = requests.get("https://official-joke-api.appspot.com/jokes/programming/random")
        joke = res.json()[0]
        return f"{joke['setup']} – {joke['punchline']}"
    except:
        return "Why did the blockchain break up with fiat? It found someone more decentralized. 😅"

def get_coordinates(location):
    api_key = "30fa24a2c96343459b0ffb9c8567969e"
    url = f"https://api.opencagedata.com/geocode/v1/json"
    params = {
        "q": location,
        "key": api_key,
        "limit": 1
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        if data["results"]:
            lat = data["results"][0]["geometry"]["lat"]
            lon = data["results"][0]["geometry"]["lng"]
            return lat, lon
    except Exception as e:
        print(f"OpenCage Error: {e}")
    return None, None

# === CoinGecko Exchange + OpenCage ===
def get_exchange_data_dynamic():
    try:
        url = "https://api.coingecko.com/api/v3/exchanges?per_page=5&page=1"
        res = requests.get(url)
        res.raise_for_status()
        data = res.json()
        exchanges = []

        for exchange in data:
            name = exchange["name"]
            country = exchange.get("country", "Global")
            volume = round(exchange.get("trade_volume_24h_btc", 0), 2)
            lat, lon = get_coordinates(country)
            if lat and lon:
                exchanges.append({
                    "name": name,
                    "country": country,
                    "volume": volume,
                    "lat": lat,
                    "lon": lon
                })
        return exchanges
    except Exception as e:
        print("Error loading exchanges:", e)
        return []


@app.route("/")
def index():
    coins_list = get_top50_coins()
    exchange_rate = get_exchange_rate()
    news_list = get_crypto_news()
    coindesk_news = get_coindesk_news()
    crypto_news = get_crypto_news()
    fng = get_fear_greed_index()
    joke = get_crypto_joke()
    exchange_data = get_exchange_data_dynamic()
    user_favorites = []

    if "user_id" in session:
        conn = sqlite3.connect("users.db")
        c = conn.cursor()
        c.execute("SELECT coin FROM favorites WHERE user_id = ?", (session["user_id"],))
        user_favorites = [row[0] for row in c.fetchall()]
        conn.close()

    for coin in coins_list:
        coin["price_usd"] = round(coin["current_price"] / exchange_rate, 4)
        coin["price_eur"] = round(coin["current_price"], 4)
        coin["change"] = round(coin.get("price_change_percentage_24h", 0), 2)
        coin["image"] = coin.get("image", "")
        coin["symbol"] = coin.get("symbol", "").upper()

    market_data = {
        "market_cap_eur": 0,
        "volume_24h_eur": 0,
        "btc_dominance": 0
    }
    try:
        res = requests.get("https://api.coingecko.com/api/v3/global")
        if res.status_code == 200:
            data = res.json()["data"]
            market_data = {
                "market_cap_eur": round(data["total_market_cap"]["eur"] / 1e12, 2),
                "volume_24h_eur": round(data["total_volume"]["eur"] / 1e9, 2),
                "btc_dominance": round(data["market_cap_percentage"]["btc"], 1),
            }
    except Exception as e:
        print("Fehler beim Laden der globalen Daten:", e)

    return render_template(
        "index.html",
        coins_list=coins_list,
        market_data=market_data,
        username=session.get("username"),
        favorites=user_favorites,
        news_list=news_list,
        crypto_news=crypto_news,
        coindesk_news=coindesk_news,
        fng=fng,
        joke=joke,
        exchange_data=exchange_data
        )

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        conn = sqlite3.connect("users.db")
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
        except sqlite3.IntegrityError:
            return "Benutzername existiert bereits."
        finally:
            conn.close()
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    session.permanent = True
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("users.db")
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE username = ? AND password = ?", (username, password))
        result = c.fetchone()
        conn.close()

        if result:
            session["user_id"] = result[0]
            session["username"] = username
            print("LOGIN SUCCESS")  # ✅ مؤقتًا لتتبع الحالة
            return redirect(url_for("index"))
        else:
            print("LOGIN FAILED")
            return "Zugangsdaten sind falsch."
        
    return render_template("login.html")


@app.route("/add_favorite", methods=["POST"])
def add_favorite():
    if "user_id" not in session:
        return redirect(url_for("login"))

    coin = request.form["coin"]
    user_id = session["user_id"]

    # 1. حفظ العملة في المفضلة
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO favorites (user_id, coin) VALUES (?, ?)", (user_id, coin))
    conn.commit()
    conn.close()

    # 2. تحديث الكاش فوراً
    try:
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            "vs_currency": "eur",
            "ids": coin
        }
        res = requests.get(url, params=params)
        res.raise_for_status()
        coin_data = res.json()
        exchange_rate = get_exchange_rate()
        update_favorite_cache(coin_data, exchange_rate)
    except Exception as e:
        print(f"⚠️ Fehler beim Caching der Coin '{coin}':", e)

    return redirect(url_for("index"))


@app.route("/meine_favoriten")
def meine_favoriten():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT coin FROM favorites WHERE user_id = ?", (user_id,))
    coin_ids = [row[0] for row in c.fetchall()]
    conn.close()

    if not coin_ids:
        return render_template("favoriten.html", coins=[])

    now = int(time.time())
    fresh_data = []
    missing_ids = []

    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    for coin_id in coin_ids:
        c.execute("SELECT * FROM favorite_cache WHERE coin_id = ?", (coin_id,))
        row = c.fetchone()
        if row and now - row[-1] < 900:  # ✅ 15 دقيقة
            fresh_data.append({
                "id": row[0],
                "name": row[1],
                "symbol": row[2],
                "image": row[3],
                "price_eur": row[4],
                "price_usd": row[5],
                "change": row[6]
            })
        else:
            missing_ids.append(coin_id)
    conn.close()

    if missing_ids:
        try:
            url = "https://api.coingecko.com/api/v3/coins/markets"
            params = {
                "vs_currency": "eur",
                "ids": ",".join(missing_ids)
            }
            res = requests.get(url, params=params)
            res.raise_for_status()
            new_data = res.json()
            exchange_rate = get_exchange_rate()
            update_favorite_cache(new_data, exchange_rate)
            for coin in new_data:
                fresh_data.append({
                    "id": coin["id"],
                    "name": coin["name"],
                    "symbol": coin["symbol"],
                    "image": coin["image"],
                    "price_eur": coin["current_price"],
                    "price_usd": round(coin["current_price"] / exchange_rate, 4),
                    "change": round(coin.get("price_change_percentage_24h", 0), 2)
                })
        except Exception as e:
            print("Fehler beim Abrufen von CoinGecko:", e)

    return render_template("favoriten.html", coins=fresh_data)



@app.route("/remove_favorite", methods=["POST"])
def remove_favorite():
    if "user_id" not in session:
        return redirect(url_for("login"))

    coin = request.form["coin"]
    user_id = session["user_id"]

    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("DELETE FROM favorites WHERE user_id = ? AND coin = ?", (user_id, coin))
    conn.commit()
    conn.close()

    return redirect(url_for("meine_favoriten"))

@app.route("/kaufen/<coin_id>", methods=["GET", "POST"])
def kaufen(coin_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    coin = None  # تعريف مسبق لتجنب UnboundLocalError

    if request.method == "POST":
        amount_raw = request.form.get("amount", "").strip()
        price_raw = request.form.get("price", "").strip()

        # تحقق من الكمية والسعر
        if not amount_raw or not price_raw:
            return "❌ Fehler: Bitte Menge und Preis eingeben."

        try:
            amount = float(amount_raw)
            price = float(price_raw)
            if amount <= 0:
                return "❌ Fehler: Die Menge muss größer als 0 sein."
        except ValueError:
            return "❌ Fehler: Ungültige Eingabe."

        # حفظ في قاعدة البيانات
        buy_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user_id = session["user_id"]

        conn = sqlite3.connect("users.db")
        c = conn.cursor()
        c.execute("""
            INSERT INTO wallet (user_id, coin, amount, buy_price, buy_date)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, coin_id, amount, price, buy_date))
        conn.commit()
        conn.close()

        return redirect(url_for("meine_wallet"))

    # محاولة تحميل بيانات العملة من الكاش
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT * FROM favorite_cache WHERE coin_id = ?", (coin_id,))
    row = c.fetchone()
    conn.close()

    now = int(time.time())
    if row and now - row[-1] < 900:  # 15 دقيقة
        coin = {
            "id": row[0],
            "name": row[1],
            "symbol": row[2],
            "image": row[3],
            "current_price": row[4]
        }
    else:
        try:
            url = "https://api.coingecko.com/api/v3/coins/markets"
            params = {
                "vs_currency": "eur",
                "ids": coin_id
            }
            res = requests.get(url, params=params)
            res.raise_for_status()
            coin_data = res.json()
            coin = {
                "id": coin_data[0]["id"],
                "name": coin_data[0]["name"],
                "symbol": coin_data[0]["symbol"],
                "image": coin_data[0]["image"],
                "current_price": coin_data[0]["current_price"]
            }
            exchange_rate = get_exchange_rate()
            update_favorite_cache(coin_data, exchange_rate)
        except Exception as e:
            print("Fehler beim Laden der Coin:", e)
            coin = None

    return render_template("kaufen.html", coin=coin)



@app.route("/meine_wallet")
def meine_wallet():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT coin, amount, buy_price, buy_date, id FROM wallet WHERE user_id = ?", (user_id,))
    wallet_data = c.fetchall()
    conn.close()

    if not wallet_data:
        return render_template("wallet.html", wallet=[], total=0)

    coin_ids = list(set([row[0] for row in wallet_data]))

    now = int(time.time())
    fresh_data = []
    missing_ids = []

    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    for coin_id in coin_ids:
        c.execute("SELECT * FROM favorite_cache WHERE coin_id = ?", (coin_id,))
        row = c.fetchone()
        if row and now - row[-1] < 900:
            fresh_data.append({
                "id": row[0],
                "name": row[1],
                "symbol": row[2],
                "image": row[3],
                "current_price": row[4]
            })
        else:
            missing_ids.append(coin_id)
    conn.close()

    prices = {coin["id"]: coin["current_price"] for coin in fresh_data}

    if missing_ids:
        try:
            url = "https://api.coingecko.com/api/v3/coins/markets"
            params = {
                "vs_currency": "eur",
                "ids": ",".join(missing_ids)
            }
            res = requests.get(url, params=params)
            res.raise_for_status()
            new_data = res.json()
            exchange_rate = get_exchange_rate()
            update_favorite_cache(new_data, exchange_rate)
            for coin in new_data:
                prices[coin["id"]] = coin["current_price"]
        except Exception as e:
            print("Fehler beim Laden der aktuellen Preise:", e)

    wallet = []
    total_value = 0

    for coin, amount, buy_price, buy_date, entry_id in wallet_data:
        current_price = prices.get(coin, 0)
        value_now = amount * current_price
        value_then = amount * buy_price
        profit = value_now - value_then
        wallet.append({
            "id": entry_id,
            "coin": coin,
            "amount": amount,
            "buy_price": buy_price,
            "buy_date": buy_date,
            "current_price": current_price,
            "value_now": round(value_now, 2),
            "profit": round(profit, 2)
        })
        total_value += value_now

    return render_template("wallet.html", wallet=wallet, total=round(total_value, 2))


@app.route("/delete_wallet_entry/<int:entry_id>", methods=["POST"])
def delete_wallet_entry(entry_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("DELETE FROM wallet WHERE id = ? AND user_id = ?", (entry_id, user_id))
    conn.commit()
    conn.close()

    return redirect(url_for("meine_wallet"))



@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True)