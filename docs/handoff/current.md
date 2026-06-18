# Current Handoff

Local short-term context for unfinished work. This file may be gitignored and should not replace long-term memory.

## Current task

V1 Alpha Research Pipeline — implemented and tested.

## Relevant files

- `data/fetch_binance.py` — fetches BTCUSDT 4H from Binance, retry + logging
- `feature_lab/registry.py` — 7 declarative features (P01-P03, O01, F01, L01-L02)
- `feature_lab/build_features.py` — forward-fill + topological sort + Polars SQL + label
- `research/train_lightgbm.py` — 60/20/20 time split, LightGBM + early stopping
- `tests/test_pipeline.py` — 7 CF + unit tests covering all 4 issues
- `requirements.txt` — polars, lightgbm, ccxt, pyarrow, vectorbt, pytest, scipy
- `ruff.toml` — ruff config (line-length=120, py312)

## Decisions made

- Rolling stats (funding_z, liq_shock) use Polars native API pre-computed as helper columns (`_funding_rm180`, etc.) because Polars SQL only supports `ROWS UNBOUNDED PRECEDING`
- Registry stores SQL expressions that reference pre-computed helper columns
- `min_periods` → `min_samples` for rolling_* in newer Polars

## Next steps

1. Run `python data/fetch_binance.py` to get real data
2. Run `python feature_lab/build_features.py` to build features
3. Run `python research/train_lightgbm.py` to train model
4. Verify real-world metrics in `reports/metrics_v1.json`
