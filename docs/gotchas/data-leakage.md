# Data Leakage Gotchas

## Prohibited patterns

- **Random Train/Test Split**: `train_test_split()` from sklearn destroys temporal order. Always use a time-ordered split.
- **Future data in Features**: Feature formulas must only reference data at time `t` or earlier. Never use `.shift(-n)` in a feature — only in the label.
- **Rolling window contamination**: Rolling statistics must use only past data (e.g. `ROWS n PRECEDING` in SQL, not a centered window).

## NaN generation rules

| Source | Handling |
|---|---|
| rolling(180) → first 179 rows NaN | `drop_nulls()` after all features computed |
| `close.shift(-6)` → last 6 rows NaN | `drop_nulls()` after label computed |
| API gaps (exchange returned null) | Forward-fill at `build_features.py` entry; retry in `fetch_binance.py` |

Never forward-fill NaN produced by rolling windows or label shifts — those must be dropped.

## Placeholder data

Never fill missing raw data with constants (zeros, means, synthetic values). If a data source cannot provide a column (e.g. Binance liquidation API is offline), that column must not appear in the raw dataset. Features that depend on unavailable columns must be removed from the registry. The principle is: *no column in raw data without a real source*.

## Validation checklist

Before training, verify:
```
assert df["close"].is_null().sum() == 0
assert (df["timestamp"].diff() != timedelta(hours=4)).sum() == 0
assert df.select(pl.col("^.*ret.*$")).null_count().sum() == 0
```
