# PRD: V1 Alpha Research Pipeline

## Overview

Build the first end-to-end Alpha Research Pipeline for Crypto Perpetual Futures.
Target: **BTCUSDT**, 4H candles, 2021-01-01 to present.

The pipeline outputs a trained LightGBM model that predicts forward 24H returns.

## Scope

### In scope

- Fetch BTCUSDT 4H data from Binance (OHLCV + OI + Funding + Liquidation)
- 7 declarative features across 4 categories (Price, OI, Funding, Liquidation)
- Feature expression evaluation via Polars SQL
- Topological sort for cross-feature dependencies
- LightGBM regressor training with early stopping
- Time series split (60/20/20)
- Model, metrics, and predictions persisted to disk

### Out of scope (deferred to V2+)

- Multi-symbol support
- Walk-Forward Validation (V4)
- Full 75-feature registry (V2-V3)
- SHAP analysis (V3)
- VectorBT portfolio backtest (V5)
- Freqtrade dry run (V6)
- Hyperparameter tuning

## Features (V1)

| ID | Name | Category | Description |
|---|---|---|---|
| P01 | ret_1 | Price | 1-bar return |
| P02 | ret_3 | Price | 3-bar return |
| P03 | ret_6 | Price | 6-bar return |
| O01 | oi_ret_1 | OI | 1-bar OI change |
| F01 | funding_z | Funding | Z-score vs 30-day mean |
| L01 | liq_total | Liquidation | Total liquidations |
| L02 | liq_shock | Liquidation | liq_total / 30-day rolling mean |

## Label

`future_return_24h` = `close.shift(-6) / close - 1`

## Deliverables

| File | Description |
|---|---|
| `data/raw/btcusdt_4h.parquet` | Fetched and aligned raw data |
| `data/features_v1.parquet` | Feature set + label, cleaned |
| `models/lgbm_v1.pkl` | Trained LightGBM model |
| `models/lgbm_v1_meta.json` | Feature names, label name, hyperparams |
| `reports/metrics_v1.json` | RMSE, MAE, Correlation |
| `reports/predictions_v1.parquet` | timestamp, y_pred, y_true |

## Scripts

| Script | Responsibility |
|---|---|
| `data/fetch_binance.py` | Fetch raw data from Binance, retry 3x, save parquet |
| `feature_lab/registry.py` | Feature catalogue (list of dicts) |
| `feature_lab/build_features.py` | Compute features from raw data, save parquet |
| `research/train_lightgbm.py` | Train model, save artifacts |

## Constraints

- No random train/test split
- Features only use data at `t` or earlier
- Labels are the only constructs allowed to reference `t + n`
- Forward-fill API gaps; drop NaN from rolling/shift windows

## Data flow

```
fetch_binance.py
  → data/raw/btcusdt_4h.parquet
    → build_features.py
      → data/features_v1.parquet
        → train_lightgbm.py
          → models/lgbm_v1.pkl + lgbm_v1_meta.json
          → reports/metrics_v1.json
          → reports/predictions_v1.parquet
```

## Directory structure

```
Ember/
├── data/
│   ├── raw/
│   ├── features_v1.parquet
│   └── fetch_binance.py
├── feature_lab/
│   ├── registry.py
│   └── build_features.py
├── research/
│   └── train_lightgbm.py
├── models/
├── reports/
├── requirements.txt
├── ruff.toml
└── docs/
```

## Success criteria

- `data/features_v1.parquet` generated with 7 features + label, no nulls
- `models/lgbm_v1.pkl` trained successfully
- `reports/predictions_v1.parquet` contains valid (timestamp, pred, actual) triples
- RMSE, MAE, and Correlation printed and saved to `metrics_v1.json`

## Tech stack

- Python 3.12+
- Polars (data processing)
- LightGBM (model)
- CCXT (exchange data)
- pyarrow (parquet I/O)
- pip + requirements.txt (dependency management)
- Ruff (linting)
