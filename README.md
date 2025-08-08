# Bitso Short Bot 🤖

Bot de trading en corto para Bitso con estrategia técnica simple (EMA, RSI, MACD), logging en SQLite y notificaciones por Telegram.

## 🚀 Requisitos

- Cuenta en Bitso con API key
- Docker
- (Opcional) Bot de Telegram y chat ID

## 🛠️ Instalación

1. Crea tu `.env` a partir de `.env.example` y agrega tus claves
2. Construye el contenedor:

```bash
docker build -t bitso-short-bot .
```

3. Ejecuta:

```bash
docker run --env-file .env bitso-short-bot
```

## ⚙️ Variables de entorno (`.env.example`)

```
BITSO_API_KEY=
BITSO_SECRET_KEY=

# Estrategia
TRADE_SYMBOL=btc_mxn
TRADE_PERCENT=0.03
EMA_FAST=20
EMA_SLOW=50
RSI_THRESHOLD=70
MACD_FAST=12
MACD_SLOW=26
MACD_SIGNAL=9

# Ejecución
INTERVAL_SECONDS=300
RUN_ONCE=0
LOG_LEVEL=INFO

# Heartbeat (alertas sin señal)
HEARTBEAT_ON_NO_SIGNAL=0
HEARTBEAT_EVERY_CYCLES=1
HEARTBEAT_PREFIX=Estado

# Telegram (opcional)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

## 📊 Indicadores y señales

- EMA rápida vs lenta: condición de tendencia (precio < EMA rápida < EMA lenta)
- RSI 14 > umbral (por defecto 70)
- MACD < línea de señal

## 🔎 Diagnóstico y ejecuciones

- Ejecución única con logs (debug):

```bash
docker run --rm --env-file .env -e RUN_ONCE=1 -e LOG_LEVEL=INFO bitso-short-bot
```

- Ejecución continua cada N segundos:

```bash
docker run --rm --env-file .env -e INTERVAL_SECONDS=60 bitso-short-bot
```

### ⏰ Heartbeat cada 30 minutos

Para enviar un mensaje de “estado” aunque no haya señal, cada 30 minutos:

```bash
docker run -d --name bitso-short-bot \
  --restart unless-stopped \
  --env-file .env \
  -e INTERVAL_SECONDS=1800 \
  -e HEARTBEAT_ON_NO_SIGNAL=1 \
  -e HEARTBEAT_EVERY_CYCLES=1 \
  bitso-short-bot
```

Ver logs:

```bash
docker logs -f bitso-short-bot
```

## 📌 Logging y base de datos

- Logs en stdout con nivel configurable por `LOG_LEVEL`
- Bitácora de operaciones en `trades.db` (SQLite)

## 📩 Telegram

Recibirás alertas cuando se detecte una señal de short si configuras el bot y chat ID.

---

Hecho con ❤️ para Hugo.
