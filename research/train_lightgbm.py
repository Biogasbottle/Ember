import json
import logging

import lightgbm as lgb
import numpy as np
import polars as pl
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

LABEL_COLS = ["label_4h", "label_12h", "label_24h"]
FEATURES_PATH = "data/features_v1.parquet"
MODEL_DIR = "models"
REPORTS_DIR = "reports"

HYPERPARAMS = {
    "objective": "binary", "metric": "auc",
    "num_leaves": 31, "learning_rate": 0.05,
    "n_estimators": 500, "early_stopping_rounds": 50,
    "random_state": 42, "verbosity": -1,
}


def _train_one_model(X_train, y_train, X_val, y_val):
    callbacks = [lgb.early_stopping(50), lgb.log_evaluation(0)]
    model = lgb.train(
        {k: v for k, v in HYPERPARAMS.items() if k != "early_stopping_rounds"},
        lgb.Dataset(X_train, y_train),
        valid_sets=[lgb.Dataset(X_val, y_val)],
        num_boost_round=500, callbacks=callbacks,
    )
    return model


def train(features_path=FEATURES_PATH, model_dir=MODEL_DIR, reports_dir=REPORTS_DIR):
    import os
    os.makedirs(model_dir, exist_ok=True)
    os.makedirs(reports_dir, exist_ok=True)

    df = pl.read_parquet(features_path)
    feature_cols = [c for c in df.columns if c not in ("timestamp", "label_4h", "label_12h", "label_24h")]
    n = len(df)

    train_end = int(n * 0.6)
    val_end = int(n * 0.8)
    train_df = df[:train_end]
    val_df = df[train_end:val_end]
    test_df = df[val_end:]

    models = {}
    metrics_all = {}

    for label_name in LABEL_COLS:
        logger.info("=== Training model for %s ===", label_name)

        tr = train_df.filter(pl.col(label_name) != 0)
        va = val_df.filter(pl.col(label_name) != 0)
        te = test_df.filter(pl.col(label_name) != 0)

        logger.info("Samples: train=%d val=%d test=%d (excl. timeout 0)", len(tr), len(va), len(te))

        X_tr = np.nan_to_num(tr.select(feature_cols).to_numpy(), nan=0.0, posinf=0.0, neginf=0.0)
        y_tr = tr[label_name].to_numpy().astype(int)
        X_va = np.nan_to_num(va.select(feature_cols).to_numpy(), nan=0.0, posinf=0.0, neginf=0.0)
        y_va = va[label_name].to_numpy().astype(int)
        X_te = np.nan_to_num(te.select(feature_cols).to_numpy(), nan=0.0, posinf=0.0, neginf=0.0)
        y_te = te[label_name].to_numpy().astype(int)

        if len(np.unique(y_tr)) < 2 or len(np.unique(y_va)) < 2:
            logger.warning("Skip %s: single-class labels", label_name)
            continue

        y_tr_bin = (y_tr == 1).astype(int)
        y_va_bin = (y_va == 1).astype(int)

        model = _train_one_model(X_tr, y_tr_bin, X_va, y_va_bin)
        models[label_name] = model

        model.save_model(os.path.join(model_dir, f"lgbm_v2.1_{label_name}.pkl"))

        y_prob = model.predict(X_te)
        y_pred = (y_prob >= 0.5).astype(int)
        y_te_bin = (y_te == 1).astype(int)

        m = {
            "auc": float(roc_auc_score(y_te_bin, y_prob)) if len(np.unique(y_te_bin)) >= 2 else 0.5,
            "accuracy": float(accuracy_score(y_te_bin, y_pred)),
            "precision": float(precision_score(y_te_bin, y_pred, zero_division=0)),
            "recall": float(recall_score(y_te_bin, y_pred, zero_division=0)),
            "f1": float(f1_score(y_te_bin, y_pred, zero_division=0)),
        }
        metrics_all[label_name] = m
        logger.info("%s: AUC=%.4f Acc=%.4f", label_name, m["auc"], m["accuracy"])

    # Consensus
    if len(models) >= 2:
        logger.info("=== Computing consensus ===")
        test_df_full = test_df
        probs = {}
        for label_name, model in models.items():
            probs[label_name] = model.predict(
                np.nan_to_num(test_df_full.select(feature_cols).to_numpy(), nan=0.0, posinf=0.0, neginf=0.0)
            )
        direction = {ln: (probs[ln] >= 0.5).astype(int) for ln in probs}
        all_dirs = np.column_stack(list(direction.values()))
        consensus = np.where(all_dirs.sum(axis=1) >= 2, 1, 0) if len(models) == 3 else np.zeros(len(test_df_full))
        consensus_ratio = all_dirs.std(axis=1).mean()
        logger.info("Consensus ratio: %.3f (mean std across models)", consensus_ratio)

        preds = pl.DataFrame({
            "timestamp": test_df_full["timestamp"].to_list(),
        })
        for ln in LABEL_COLS:
            if ln in probs:
                preds = preds.with_columns([
                    pl.Series(probs[ln]).alias(f"prob_{ln}"),
                    pl.Series(direction.get(ln, np.zeros(len(test_df_full))).astype(int)).alias(f"dir_{ln}"),
                ])
        preds = preds.with_columns(pl.Series(consensus.astype(int)).alias("consensus_dir"))
        for ln in LABEL_COLS:
            preds = preds.with_columns(pl.Series(test_df_full[ln].to_numpy().astype(int)).alias(f"actual_{ln}"))
        preds.write_parquet(os.path.join(reports_dir, "predictions_v2.1.parquet"))

        consensus_acc = (
            (consensus == test_df_full[LABEL_COLS[0]].to_numpy().astype(int)).mean()
            if len(models) == 3 else 0
        )
        metrics_all["consensus"] = {"consensus_accuracy": float(consensus_acc), "num_models": len(models)}
        logger.info("Consensus accuracy: %.4f", consensus_acc)

    meta = {"features": feature_cols, "labels": LABEL_COLS, "hyperparams": HYPERPARAMS}
    with open(os.path.join(model_dir, "lgbm_v2.1_meta.json"), "w") as f:
        json.dump(meta, f, indent=2)

    with open(os.path.join(reports_dir, "metrics_v2.1.json"), "w") as f:
        json.dump(metrics_all, f, indent=2)

    logger.info("Saved %d models, metrics, predictions", len(models))


if __name__ == "__main__":
    train()
