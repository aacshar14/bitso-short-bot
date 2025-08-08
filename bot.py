import os
import time
import logging
import sqlite3

import ccxt
import pandas as pd
import pandas_ta as ta
import requests
from dotenv import load_dotenv

load_dotenv()

# Configuración por entorno
api_key = os.getenv("BITSO_API_KEY")
api_secret = os.getenv("BITSO_SECRET_KEY")
symbol = os.getenv("TRADE_SYMBOL", "btc_mxn")
trade_percent = float(os.getenv("TRADE_PERCENT", 0.03))

# Indicadores / estrategia
ema_fast_len = int(os.getenv("EMA_FAST", 20))
ema_slow_len = int(os.getenv("EMA_SLOW", 50))
rsi_threshold = float(os.getenv("RSI_THRESHOLD", 70))
macd_fast = int(os.getenv("MACD_FAST", 12))
macd_slow = int(os.getenv("MACD_SLOW", 26))
macd_signal = int(os.getenv("MACD_SIGNAL", 9))

# Ejecución
interval_seconds = int(os.getenv("INTERVAL_SECONDS", 300))
run_once = os.getenv("RUN_ONCE", "0") == "1"

# Heartbeat (alerta aunque no haya señal)
heartbeat_on_no_signal = os.getenv("HEARTBEAT_ON_NO_SIGNAL", "0") == "1"
heartbeat_every_cycles = max(1, int(os.getenv("HEARTBEAT_EVERY_CYCLES", 1)))
heartbeat_prefix = os.getenv("HEARTBEAT_PREFIX", "Estado")

# Telegram
telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")

# Logging
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="%(asctime)s | %(levelname)s | %(message)s",
)

# Conexión a Bitso
exchange = ccxt.bitso({
    "apiKey": api_key,
    "secret": api_secret,
    "enableRateLimit": True,
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
def get_ohlcv() -> pd.DataFrame:
    candles = exchange.fetch_ohlcv(symbol, timeframe="5m", limit=200)
    df = pd.DataFrame(
        candles,
        columns=["timestamp", "open", "high", "low", "close", "volume"],
    )
    return df

# Estrategia
def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    # EMA
    df["ema_fast"] = ta.ema(df["close"], length=ema_fast_len)
    df["ema_slow"] = ta.ema(df["close"], length=ema_slow_len)
    # RSI
    df["rsi"] = ta.rsi(df["close"], length=14)
    # MACD
    macd_df = ta.macd(
        df["close"], fast=macd_fast, slow=macd_slow, signal=macd_signal
    )
    df = pd.concat([df, macd_df], axis=1)
    return df


def check_trade_signal(df: pd.DataFrame) -> tuple[bool, pd.Series]:
    df = compute_indicators(df)
    df = df.dropna()
    if df.empty:
        return False, pd.Series()

    last = df.iloc[-1]
    has_trend = last["close"] < last["ema_fast"] < last["ema_slow"]
    is_overbought = last["rsi"] > rsi_threshold
    # pandas_ta: MACD column names
    macd_val = last.get(f"MACD_{macd_fast}_{macd_slow}_{macd_signal}")
    macd_signal_val = last.get(f"MACDs_{macd_fast}_{macd_slow}_{macd_signal}")
    macd_confirm = (
        pd.notna(macd_val)
        and pd.notna(macd_signal_val)
        and macd_val < macd_signal_val
    )

    signal = bool(has_trend and is_overbought and macd_confirm)
    return signal, last


def log_indicators(last: pd.Series) -> None:
    macd_key = f"MACD_{macd_fast}_{macd_slow}_{macd_signal}"
    macds_key = f"MACDs_{macd_fast}_{macd_slow}_{macd_signal}"
    macdh_key = f"MACDh_{macd_fast}_{macd_slow}_{macd_signal}"
    logging.info(
        "Indicadores | close=%.2f ema_fast=%.2f ema_slow=%.2f rsi=%.2f macd=%.4f macds=%.4f macdh=%.4f",
        float(last.get("close", float("nan"))),
        float(last.get("ema_fast", float("nan"))),
        float(last.get("ema_slow", float("nan"))),
        float(last.get("rsi", float("nan"))),
        float(last.get(macd_key, float("nan"))),
        float(last.get(macds_key, float("nan"))),
        float(last.get(macdh_key, float("nan"))),
    )

# Ejecución de orden (simulada)
def execute_trade():
    balance = exchange.fetch_balance()
    mxn_balance = balance["total"].get("mxn", 0)
    ticker = exchange.fetch_ticker(symbol)
    price = ticker["last"]
    amount = round((mxn_balance * trade_percent) / price, 6)

    log_trade(symbol, price, amount, "short")
    msg = (
        f"💥 Señal SHORT para {symbol}\n💰 Precio: {price} MXN\n📉 Monto estimado: {amount}"
    )
    send_telegram(msg)
    logging.info(msg)

# Main
if __name__ == "__main__":
    logging.info(
        "Inicio Bot | symbol=%s ema_fast=%d ema_slow=%d rsi_thr=%.2f interval=%ds",
        symbol,
        ema_fast_len,
        ema_slow_len,
        rsi_threshold,
        interval_seconds,
    )

    init_db()

    def run_cycle(cycle_index: int):
        try:
            df = get_ohlcv()
            signal, last = check_trade_signal(df)
            if not last.empty:
                log_indicators(last)
            if signal:
                execute_trade()
            else:
                logging.info("Sin señal de short.")
                if heartbeat_on_no_signal and (cycle_index % heartbeat_every_cycles == 0):
                    try:
                        price_val = None
                        try:
                            price_val = float(last.get("close")) if not last.empty else None
                        except Exception:
                            price_val = None
                        msg = (
                            f"⏰ {heartbeat_prefix}: sin señal para {symbol}"
                            + (f" | precio≈{price_val:.2f} MXN" if price_val else "")
                        )
                        send_telegram(msg)
                        logging.info("Heartbeat enviado: %s", msg)
                    except Exception as hb_e:
                        logging.warning("No se pudo enviar heartbeat: %s", hb_e)
        except Exception as e:
            logging.exception("Error en ciclo: %s", e)

    if run_once:
        run_cycle(cycle_index=1)
    else:
        cycle = 1
        while True:
            start_ts = time.time()
            run_cycle(cycle_index=cycle)
            elapsed = time.time() - start_ts
            sleep_for = max(1, interval_seconds - int(elapsed))
            time.sleep(sleep_for)
            cycle += 1
