# Bitso Short Bot 🤖

Bot de trading en corto para Bitso con estrategia técnica simple (EMA, RSI, MACD), logging en SQLite y notificaciones por Telegram.

## 🚀 Requisitos

- Cuenta en Bitso con API key
- Bot de Telegram y chat ID
- Docker

## 🛠️ Instalación

1. Copia `.env.template` a `.env` y agrega tus claves
2. Construye el contenedor:

```bash
docker build -t bitso-short-bot .
```

3. Ejecuta:

```bash
docker run --env-file .env bitso-short-bot
```

## 📊 Indicadores

- EMA 20 & 50
- RSI 14
- MACD

## 📌 Logging

Se guarda cada operación en una base de datos SQLite (`trades.db`).

## 📩 Telegram

Recibirás alertas cada vez que se detecte una señal de short.

---

Hecho con ❤️ para Hugo.
