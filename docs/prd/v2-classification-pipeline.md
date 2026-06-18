# PRD: V2 Classification Pipeline

## Problem Statement

V1's continuous regression approach (`future_return_24h`) produced a model that predicts near-constant values — Correlation ≈ 0.008, direction accuracy ≈ 49% (coin flip). Financial return series have extreme signal-to-noise ratios; predicting magnitude is far harder than predicting direction. The model never learned anything useful because the problem was framed incorrectly.

## Solution

Convert the prediction target from **continuous regression** to **binary classification**: predict whether the 24H forward return will be positive or negative.

Three concurrent improvements:

1. **Label redesign**: Replace `future_return_24h` (regression) with `direction_24h = sign(future_return_24h)` (binary classification)
2. **Feature expansion**: Add volatility, momentum, and volume features to increase signal dimensionality from 5 to approximately 20
3. **Training improvement**: Time-series cross-validation (Purged K-Fold), Optuna hyperparameter tuning, ensemble of LightGBM + Random Forest

## User Stories

1. As a quant researcher, I want the model to predict direction (up/down) instead of magnitude, so that the prediction task is aligned with what is actually tradable
2. As a quant researcher, I want an expanded feature set including volatility and momentum features, so that the model has more dimensions of market data to learn from
3. As a quant researcher, I want time-series-aware cross-validation, so that evaluation is not contaminated by temporal data leakage
4. As a quant researcher, I want automated hyperparameter tuning via Optuna, so that model parameters are optimized objectively
5. As a quant researcher, I want an ensemble of LightGBM and Random Forest, so that predictions are more robust than any single model
6. As a quant researcher, I want SHAP feature importance analysis, so that I can understand which features drive predictions
7. As a quant researcher, I want AUC-ROC and precision/recall as evaluation metrics, so that classification performance is measured correctly
8. As a quant researcher, I want direction accuracy > 52% (statistically better than random), so that the model has practical value
9. As a quant researcher, I want the training script to log training vs validation performance per fold, so that I can detect overfitting
10. As a quant researcher, I want the existing V1 infrastructure (registry, topological sort, SQL eval) to remain compatible, so that V1 work is not wasted

## Implementation Decisions

### Label Design

- Binary label: `direction_24h = 1 if close.shift(-6) > close else 0`
- Replace `future_return_24h` in `build_features.py` with `direction_24h`
- Label stored as integer column in `features_v1.parquet`

### Feature Expansion

New feature categories in `registry.py`:

| Category | Count | Example features |
|---|---|---|
| Price (P) | 10 | ret_1/3/6/12/24, momentum_4h, volatility_20/60, high_low_range |
| OI (O) | 5 | oi_ret_1/3/6, oi_delta_z, oi_ret_accel |
| Funding (F) | 3 | funding_z (existing), funding_change_1, funding_direction |
| Volume (V) | 5 | volume_z, volume_ratio_taker, volume_trend, relative_volume, vwap_deviation |

Total: ~23 features

Each feature uses the same declarative format (id, name, category, expression, depends_on). Existing SQL eval + topological sort infrastructure is reused without modification.

### Training Pipeline

- **Model**: LightGBM Classifier with `objective: binary`, `metric: auc`
- **Ensemble**: Random Forest Classifier, predictions averaged with LightGBM
- **Cross-validation**: Purged K-Fold (5 folds, gap between train/val to prevent leakage)
- **Hyperparameter tuning**: Optuna, 50 trials, maximizing validation AUC
- **Metrics**: AUC-ROC, accuracy, precision, recall, F1 score

### Output Artifacts

```
models/
  lgbm_v2.pkl              ← Trained LightGBM
  rf_v2.pkl                ← Trained Random Forest
  lgbm_v2_meta.json        ← Features, label, best hyperparams
reports/
  metrics_v2.json          ← AUC, accuracy, precision, recall, F1
  predictions_v2.parquet   ← timestamp, prob_up, direction, actual
  feature_importance.json  ← SHAP importance per feature
```

## Testing Decisions

Tests verify behavior through public interfaces:

- CF test for `build_features.py`: feeds raw data, verifies output parquet has expanded columns + binary label, no nulls
- CF test for `train_lightgbm.py`: feeds features parquet, verifies 4 output files exist, AUC is a valid float, predictions are binary
- Unit test for `registry.py`: verifies expanded feature list has correct structure, topological sort resolves all dependencies
- Test synthetic dataset must include enough rows (400) to survive rolling window + purge gap

All tests follow existing pattern in `tests/test_pipeline.py`.

## Out of Scope

- Walk-Forward backtest (V4)
- SHAP analysis visualization (deferred)
- Multi-symbol support
- Liquidation features (no data source found)
- Deep learning models (LSTM, Transformer)
- Live trading integration (V6)

## Further Notes

- V1's `future_return_24h` column is replaced by `direction_24h`; the continuous regression label is removed
- Existing 5 features (P01-P03, O01, F01) are retained and supplemented with new features
- Correlation metric is replaced by AUC-ROC; RMSE/MAE are no longer relevant for classification
- The `feature_lab\build_features.py` entry point signature remains `build_features(raw_path, output_path)`
- The `research\train_lightgbm.py` entry point signature remains `train(features_path, model_dir, reports_dir)`
