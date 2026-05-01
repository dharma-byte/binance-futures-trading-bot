# Binance Futures Testnet Trading Bot

A clean, well-structured Python CLI application for placing orders on the **Binance USDT-M Futures Testnet**.

---

## Features

| Feature | Details |
|---|---|
| Order types | MARKET, LIMIT, STOP_MARKET (bonus) |
| Sides | BUY and SELL |
| CLI | `argparse`-based with full help text |
| Logging | Timestamped log files (DEBUG to file, INFO to console) |
| Validation | Symbol, side, type, quantity, price, stop_price |
| Error handling | API errors, network failures, invalid input |
| Structure | Separate client / orders / validators / CLI layers |

---

## Project Structure

```
trading_bot/
├── bot/
│   ├── __init__.py
│   ├── client.py          # Low-level HMAC-signed REST client
│   ├── orders.py          # Order placement logic + OrderResult
│   ├── validators.py      # Input validation (raises ValueError)
│   └── logging_config.py  # File + console logging setup
├── logs/
│   ├── market_order_sample.log
│   └── limit_order_sample.log
├── cli.py                 # CLI entry point (argparse)
├── .env.example           # Environment variable template
├── requirements.txt
└── README.md
```

---

## Setup

### 1. Get Testnet Credentials

1. Go to [https://testnet.binancefuture.com](https://testnet.binancefuture.com)
2. Sign in with your GitHub account
3. Navigate to **API Management** → generate a new key pair
4. Copy your **API Key** and **Secret Key**

### 2. Clone & Install

```bash
git clone <your-repo-url>
cd trading_bot

# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### 3. Configure Credentials

```bash
cp .env.example .env
```

Edit `.env` and fill in your keys:

```env
BINANCE_API_KEY=your_testnet_api_key_here
BINANCE_API_SECRET=your_testnet_api_secret_here
```

> ⚠️ **Never commit `.env` to version control.** The `.gitignore` should exclude it.

---

## Running the Bot

### Test Connectivity

```bash
python cli.py ping
```

Expected output:
```
  ✓  Connected to Binance Futures Testnet. Server time: 1736934000000
```

---

### Place a MARKET Order

```bash
# Market BUY 0.001 BTC
python cli.py place --symbol BTCUSDT --side BUY --type MARKET --qty 0.001

# Market SELL 0.001 BTC
python cli.py place --symbol BTCUSDT --side SELL --type MARKET --qty 0.001
```

---

### Place a LIMIT Order

```bash
# Limit SELL at $100,000
python cli.py place --symbol BTCUSDT --side SELL --type LIMIT --qty 0.001 --price 100000

# Limit BUY at $80,000 with IOC time-in-force
python cli.py place --symbol BTCUSDT --side BUY --type LIMIT --qty 0.001 --price 80000 --tif IOC
```

---

### Place a STOP_MARKET Order (Bonus)

```bash
# Stop-market BUY triggered at $55,000
python cli.py place --symbol BTCUSDT --side BUY --type STOP_MARKET --qty 0.001 --stop-price 55000

# Stop-market SELL triggered at $90,000
python cli.py place --symbol BTCUSDT --side SELL --type STOP_MARKET --qty 0.001 --stop-price 90000
```

---

### Full Help

```bash
python cli.py --help
python cli.py place --help
```

---

## Sample Output

```
──────────────────────────────────────────────────
  ORDER REQUEST SUMMARY
──────────────────────────────────────────────────
  Symbol     : BTCUSDT
  Side       : BUY
  Type       : MARKET
  Quantity   : 0.001
──────────────────────────────────────────────────

──────────────────────────────────────────────────
  ORDER RESULT
──────────────────────────────────────────────────
  Order ID       : 3254786
  Client OID     : web_abc123
  Symbol         : BTCUSDT
  Side           : BUY
  Type           : MARKET
  Status         : FILLED
  Orig Qty       : 0.001
  Executed Qty   : 0.001
  Avg Price      : 97250.10
──────────────────────────────────────────────────

  ✓  Order placed successfully (orderId=3254786)
```

---

## Logging

Logs are written to `logs/trading_bot_<timestamp>.log`.

- **Console**: INFO level and above
- **File**: DEBUG level and above (includes full request/response bodies)

Sample log entries are in `logs/market_order_sample.log` and `logs/limit_order_sample.log`.

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| Missing API keys | Prints a clear error and exits |
| Invalid input (bad symbol, negative qty, etc.) | `[VALIDATION ERROR]` message and exits |
| Binance API error (e.g. -1121 Invalid symbol) | `[API Error]` with Binance error code and message |
| Network timeout or connection refused | Friendly message, logged as ERROR |

---

## Assumptions

- The bot targets the **USDT-M Futures Testnet** only (`https://testnet.binancefuture.com`)
- `timeInForce` defaults to **GTC** for LIMIT orders (configurable via `--tif`)
- Quantity precision must match the symbol's lot size filter — if Binance rejects with `-1111`, reduce decimal places
- No position-side (hedge mode) is assumed; the default one-way mode is used

---

## Dependencies

```
requests>=2.31.0      # HTTP client with retry support
urllib3>=2.0.0        # Underlying HTTP layer
python-dotenv>=1.0.0  # .env file loading
```

No `python-binance` dependency — this uses direct REST calls for transparency and control.