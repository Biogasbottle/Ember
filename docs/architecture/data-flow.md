# Data Flow (V1)

```
[Binance API]
     │
     │  CCXT fetch
     ▼
fetch_binance.py ─────────────────────────────────────────────
     │  OHLCV + OI + Funding + Liquidation → JOIN on timestamp
     │  Retry: 3 attempts, exponential backoff
     │  Validate: log null columns
     ▼
data/raw/btcusdt_4h.parquet
     │
     │  Read by build_features.py
     ▼
build_features.py ────────────────────────────────────────────
     │  1. Forward-fill residual nulls (log timestamps)
     │  2. Load registry → Topological sort by depends_on
     │  3. Evaluate each expression via Polars SQL
     │  4. Compute label: future_return_24h
     │  5. drop_nulls() — removes rolling(180) and shift(-6) NaN rows
     ▼
data/features_v1.parquet
     │
     │  Read by train_lightgbm.py
     ▼
train_lightgbm.py ────────────────────────────────────────────
     │  1. 60/20/20 time series split (never random)
     │  2. Train LightGBM Regressor with early stopping on val set
     │  3. Predict on test set
     │  4. Compute RMSE, MAE, Correlation(y_pred, y_true)
     ▼
┌────────────────────┬──────────────────────┬────────────────────────┐
models/              reports/               reports/
  lgbm_v1.pkl          metrics_v1.json        predictions_v1.parquet
  lgbm_v1_meta.json                            [timestamp, pred, actual]
```
