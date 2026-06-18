import json
import logging

import lightgbm as lgb
import polars as pl
from scipy.stats import pearsonr

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

HYPERPARAMS = {
    "objective": "regression",
    "metric": "rmse",
    "num_leaves": 31,
    "learning_rate": 0.05,
    "n_estimators": 500,
    "early_stopping_rounds": 50,
    "random_state": 42,
    "verbosity": -1,
}

LABEL = "future_return_24h"
FEATURES_PATH = "data/features_v1.parquet"
MODEL_DIR = "models"
REPORTS_DIR = "reports"


def train(features_path=FEATURES_PATH, model_dir=MODEL_DIR, reports_dir=REPORTS_DIR):
    import os

    os.makedirs(model_dir, exist_ok=True)
    os.makedirs(reports_dir, exist_ok=True)

    df = pl.read_parquet(features_path)
    n = len(df)

    train_end = int(n * 0.6)
    val_end = int(n * 0.8)

    train_df = df[:train_end]
    val_df = df[train_end:val_end]
    test_df = df[val_end:]

    feature_cols = [c for c in df.columns if c not in ("timestamp", LABEL)]

    X_train = train_df.select(feature_cols).to_numpy()
    y_train = train_df[LABEL].to_numpy()
    X_val = val_df.select(feature_cols).to_numpy()
    y_val = val_df[LABEL].to_numpy()
    X_test = test_df.select(feature_cols).to_numpy()
    y_test = test_df[LABEL].to_numpy()

    logger.info("Split: train=%d val=%d test=%d", len(X_train), len(X_val), len(X_test))

    callbacks = [lgb.early_stopping(HYPERPARAMS["early_stopping_rounds"]), lgb.log_evaluation(0)]
    model = lgb.train(
        params={k: v for k, v in HYPERPARAMS.items() if k != "early_stopping_rounds"},
        train_set=lgb.Dataset(X_train, y_train),
        valid_sets=[lgb.Dataset(X_val, y_val)],
        num_boost_round=HYPERPARAMS["n_estimators"],
        callbacks=callbacks,
    )

    y_pred = model.predict(X_test)

    rmse = float(((y_pred - y_test) ** 2).mean() ** 0.5)
    mae = float(abs(y_pred - y_test).mean())
    corr, _ = pearsonr(y_pred, y_test)
    correlation = float(corr)

    logger.info("RMSE=%.6f MAE=%.6f Correlation=%.6f", rmse, mae, correlation)

    model_path = os.path.join(model_dir, "lgbm_v1.pkl")
    model.save_model(model_path)

    meta = {
        "features": feature_cols,
        "label": LABEL,
        "hyperparams": HYPERPARAMS,
    }
    with open(os.path.join(model_dir, "lgbm_v1_meta.json"), "w") as f:
        json.dump(meta, f, indent=2)

    metrics = {"rmse": rmse, "mae": mae, "correlation": correlation}
    with open(os.path.join(reports_dir, "metrics_v1.json"), "w") as f:
        json.dump(metrics, f, indent=2)

    preds = pl.DataFrame({
        "timestamp": test_df["timestamp"],
        "pred": y_pred,
        "actual": y_test,
    })
    preds.write_parquet(os.path.join(reports_dir, "predictions_v1.parquet"))

    logger.info("Saved model, metrics, predictions")


if __name__ == "__main__":
    train()
