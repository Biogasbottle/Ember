# V1 Operation Manual

## Prerequisites

- Python 3.12+
- Git

## Setup

```bash
# Clone
git clone https://github.com/Biogasbottle/Ember.git
cd Ember

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # Linux/macOS

# Install dependencies
pip install -r requirements.txt
```

## Pipeline

Run in order. Each step produces a file consumed by the next.

### Step 1 — Fetch Raw Data

```bash
python data/fetch_binance.py
```

Fetches BTCUSDT 4H data (2021-01-01 to present) from Binance: OHLCV candles, Open Interest, Funding Rate, Liquidations. Merges all on timestamp.

Retries failed API calls 3 times with backoff. Logs to stdout.

**Output**: `data/raw/btcusdt_4h.parquet`

**Schema**:

```
timestamp | open | high | low | close | volume | oi | funding | long_liq | short_liq
```

### Step 2 — Build Features

```bash
python feature_lab/build_features.py
```

Reads raw parquet, forward-fills any nulls, computes 7 features plus the label using topological sort, drops rows with NaN from rolling windows or shift operations.

**Output**: `data/features_v1.parquet`

**Columns**:

```
timestamp | ret_1 | ret_3 | ret_6 | oi_ret_1 | funding_z | liq_total | liq_shock | future_return_24h
```

### Step 3 — Train Model

```bash
python research/train_lightgbm.py
```

Reads features, splits 60/20/20 by time order, trains LightGBM Regressor with early stopping. Prints RMSE, MAE, Correlation to stdout.

**Outputs**:

| File | Content |
|---|---|
| `models/lgbm_v1.pkl` | Trained model |
| `models/lgbm_v1_meta.json` | Feature names, label name, hyperparams |
| `reports/metrics_v1.json` | RMSE, MAE, Correlation |
| `reports/predictions_v1.parquet` | timestamp, pred, actual |

## Verify

```bash
pytest tests/ -v
```

7 tests cover scaffolding, data fetch, feature engineering, and model training.

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: ccxt` | `pip install -r requirements.txt` |
| Binance API rate limit | Script retries automatically; wait 1 minute and rerun |
| `data/raw/btcusdt_4h.parquet` not found | Run Step 1 first |
| Low correlation in metrics | Expected for V1 with 7 features; more features in V2-V3 |
