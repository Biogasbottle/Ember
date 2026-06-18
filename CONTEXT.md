# Project Context

This file defines stable domain language for the project. Keep it concise.

## Language

### Core domain

**Alpha Research Pipeline**:
The end-to-end process: Raw Data → Feature Engineering → Label Generation → Machine Learning → Alpha Discovery → Backtest → Live Trading.
_Avoid_: "strategy pipeline", "trading bot".

**Feature**:
A derived input variable computed from raw market data, used to predict future returns. Only depends on data at time `t` or earlier.
_Avoid_: "indicator", "signal".

**Label**:
The target variable the model predicts — `future_return_24h`, defined as `close.shift(-6) / close - 1` (4H candles × 6 = 24H). Labels are the only constructs allowed to reference `t + n` data.
_Avoid_: "target", "y".

**Alpha**:
A predictive signal — feature(s) + model → expected return. Not a trading rule.
_Avoid_: "strategy", "signal".

**Registry**:
The catalogue of all features, each with a unique ID (e.g. P01, O01, F01, L01), expression, category, and dependency list. Used by `build_features.py` to compute features in topological order.
_Avoid_: "feature list", "column list".

**Topological Sort**:
Resolves the computation order of features with cross-dependencies (e.g. L02 depends on L01's output column). Uses `graphlib.TopologicalSorter` from the Python standard library.

### Data primitives

**4H candles**: Uniform 4-hour OHLCV bars. All data is aligned to this timeframe.
**OI (Open Interest)**: Total outstanding perpetual futures contracts.
**Funding Rate**: Periodic payment between long and short positions in perpetual futures.
**Liquidation**: Forced closure of positions, tracked as `long_liq` and `short_liq`.

### Data operations

**Forward Fill**: Fill a null in a raw data column by carrying forward the last observed value from a prior row. Used when the exchange API returns occasional gaps. Logged with timestamp of each fill.
_Avoid_: "ffill", "impute".

**Epsilon**: A small constant added to denominators (`1e-8`) to avoid division-by-zero in feature formulas involving standard deviation (e.g. funding_z).

### Feature categories

- **Price** (P): Returns-based features from OHLCV data
- **OI** (O): Open interest derived features
- **Funding** (F): Funding rate derived features
- **Liquidation** (L): Liquidation derived features
- **Cross** (Price×OI, Funding×OI, Liq×OI×Funding): Interaction features

### Model

**LightGBM Regressor**: The primary ML model. Predicts continuous `future_return_24h`. Tree-based gradient boosting.
_Avoid_: "LSTM", "Transformer", "deep learning" (deferred to later phases).

**Early Stopping**: Training halts when validation loss fails to improve for `early_stopping_rounds` consecutive rounds. Prevents overfitting on the limited financial time series dataset.

### Validation

**Time Series Split**: Train/val/test split that preserves temporal order. Random splitting is prohibited. V1 uses fixed 60/20/20 split.
**Walk-Forward Validation**: Rolling window backtest where the model retrains periodically (deferred to V4).
**VectorBT**: Portfolio-level backtesting (alpha validation, not execution).
**Freqtrade**: Execution framework for dry-run and live trading.

## Relationships

- Features → Model → Expected Return → Portfolio → Execution
- Features depend only on `t` and prior data. Labels depend on `t + n`.
- The Registry feeds Feature Engineering, which produces `features_v1.parquet`.
- LightGBM trains on features to predict labels, outputting `models/lgbm_v1.pkl`.

## Example dialogue

> **Dev**: I need a column that calculates RSI for the model.
> **Domain expert**: RSI is a Feature, not a Label. Register it in the Registry under the Price category (Pxx). It must only use data at `t` or earlier. Then add it to the Feature Engineering pipeline and rebuild `features_v1.parquet`.

> **Dev**: Can I use `train_test_split` from sklearn?
> **Domain expert**: No. Random splitting causes data leakage in time series. Use Time Series Split instead. See the Important Rules in the project spec.

> **Dev**: L02 depends on L01 — which runs first?
> **Domain expert**: Topological sort handles that. Declare `depends_on` in registry.py and build_features.py will compute them in the right order automatically.

## Flagged ambiguities

- "Strategy" is overloaded — use "Alpha" for the predictive component and "Execution" for the trading component.
- "Target" means `future_return_24h` specifically; "Label" is the preferred term.
