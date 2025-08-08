import os
import ccxt
import pandas as pd
import pandas_ta as ta
import sqlite3
import requests
from dotenv import load_dotenv

# Cargar claves
load_dotenv()

api_key = os.getenv("BITSO_API_KEY")
api_secret = os.getenv("BITSO_SECRET_KEY")
symbol = os.getenv("TRADE_SYMBOL", "btc_mxn")
trade_percent = float(os.getenv("TRADE_PERCENT", 0.03))
telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")

# Conexión a Bitso
exchange = ccxt.bitso({
    'apiKey': api_key,
    'secret': api_secret
})

# Base de datos
def init_db():
    conn = sqlite3.connect("trades.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trade_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            symbol TEXT,
            price REAL,
            amount REAL,
            signal TEXT
        )
    ''')
    conn.commit()
    conn.close()

def log_trade(symbol, price, amount, signal_type):
    conn = sqlite3.connect("trades.db")
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO trade_log (timestamp, symbol, price, amount, signal)
        VALUES (datetime('now'), ?, ?, ?, ?)
    ''', (symbol, price, amount, signal_type))
    conn.commit()
    conn.close()

# Telegram
def send_telegram(message):
    url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
    payload = {
        "chat_id": telegram_chat_id,
        "text": message
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print("Error al enviar mensaje:", e)

# Data OHLC
def get_ohlcv():
    candles = exchange.fetch_ohlcv(symbol, timeframe='5m', limit=100)
    df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    return df

# Estrategia
def check_trade_signal(df):
    df['ema20'] = ta.ema(df['close'], length=20)
    df['ema50'] = ta.ema(df['close'], length=50)
    df['rsi'] = ta.rsi(df['close'], length=14)
    macd = ta.macd(df['close'])
    df = pd.concat([df, macd], axis=1)

    last = df.iloc[-1]
    return (
        last['close'] < last['ema20'] < last['ema50']
        and last['rsi'] > 70
        and last['MACD_12_26_9'] < last['MACDs_12_26_9']
    )

# Ejecución de orden (simulada)
def execute_trade():
    balance = exchange.fetch_balance()
    mxn_balance = balance['total'].get('mxn', 0)
    ticker = exchange.fetch_ticker(symbol)
    price = ticker['last']
    amount = round((mxn_balance * trade_percent) / price, 6)

    log_trade(symbol, price, amount, "short")
    msg = f"💥 Señal SHORT para {symbol}\n💰 Precio: {price} MXN\n📉 Monto estimado: {amount}"
    send_telegram(msg)
    print(msg)

# Main
if __name__ == "__main__":
    init_db()
    df = get_ohlcv()
    if check_trade_signal(df):
        execute_trade()
    else:
        print("Sin señal de short.")
