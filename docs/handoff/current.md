# Current Handoff

Local short-term context for unfinished work. This file may be gitignored and should not replace long-term memory.

## Current task

Implement V1 Alpha Research Pipeline.

## Relevant files

- `data/fetch_binance.py` — fetch BTCUSDT 4H from Binance via CCXT, save to `data/raw/btcusdt_4h.parquet`
- `feature_lab/registry.py` — declarative feature list with id/name/category/expression/depends_on
- `feature_lab/build_features.py` — topological sort + Polars SQL evaluation, output `data/features_v1.parquet`
- `research/train_lightgbm.py` — 60/20/20 time split, LightGBM train, save model + metrics + predictions
- `requirements.txt` — polars, lightgbm, ccxt, pyarrow, vectorbt
- `ruff.toml` — ruff config

## Decisions made

See `docs/adr/0001-polars-sql-feature-engine.md` and `docs/adr/0002-time-series-split.md`.

## Next steps

1. Create `requirements.txt` and `ruff.toml`
2. Implement `data/fetch_binance.py`
3. Implement `feature_lab/registry.py`
4. Implement `feature_lab/build_features.py`
5. Implement `research/train_lightgbm.py`
6. Run pipeline end-to-end and verify outputs exist
