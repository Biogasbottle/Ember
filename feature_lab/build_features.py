import logging
from graphlib import TopologicalSorter

import polars as pl

from feature_lab.registry import FEATURES

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

LABEL_EXPRESSION = "close / LEAD(close, 6) OVER (ORDER BY timestamp) - 1"
LABEL_NAME = "future_return_24h"
OUTPUT_PATH = "data/features_v1.parquet"


def build_features(raw_path, output_path=OUTPUT_PATH):
    df = pl.read_parquet(raw_path)

    null_cols = [col for col in df.columns if df[col].null_count() > 0]
    if null_cols:
        logger.warning("Forward-filling nulls in columns: %s", null_cols)
        for col in null_cols:
            null_mask = df[col].is_null()
            filled_timestamps = df.filter(null_mask)["timestamp"].to_list()
            logger.info("Filled %d nulls in %s at timestamps: %s", len(filled_timestamps), col, filled_timestamps)
        df = df.with_columns(pl.all().forward_fill())

    needs_funding_rm = any("_funding_rm180" in f.get("depends_on", []) for f in FEATURES)
    if needs_funding_rm:
        df = df.with_columns([
            pl.col("funding").rolling_mean(180, min_samples=1).alias("_funding_rm180"),
            pl.col("funding").rolling_std(180, min_samples=1).alias("_funding_rs180"),
        ])

    name_to_feat = {f["name"]: f for f in FEATURES}
    graph = {f["name"]: set(f.get("depends_on", [])) for f in FEATURES}
    ts = TopologicalSorter(graph)
    order = list(ts.static_order())
    logger.info("Topological order: %s", order)

    ctx = pl.SQLContext(df=df)
    for name in order:
        if name not in name_to_feat:
            continue
        feat = name_to_feat[name]
        logger.info("Computing %s (%s)", feat["id"], feat["name"])
        df = ctx.execute(
            f"SELECT *, {feat['expression']} AS {name} FROM df"
        ).collect()
        ctx = pl.SQLContext(df=df)

        needs_liq_rm = any("_liq_rm180" in f.get("depends_on", []) for f in FEATURES)
        if name == "liq_total" and needs_liq_rm:
                df = df.with_columns(
                    pl.col("liq_total").rolling_mean(180, min_samples=1).alias("_liq_rm180"),
                )
                ctx = pl.SQLContext(df=df)

    logger.info("Computing label: %s", LABEL_NAME)
    df = ctx.execute(
        f"SELECT *, {LABEL_EXPRESSION} AS {LABEL_NAME} FROM df"
    ).collect()

    before = len(df)
    df = df.drop_nulls()
    logger.info("drop_nulls: %d rows removed, %d remaining", before - len(df), len(df))

    feature_cols = [f["name"] for f in FEATURES]
    output_cols = ["timestamp"] + feature_cols + [LABEL_NAME]
    df.select(output_cols).write_parquet(output_path)
    logger.info("Saved %d rows x %d cols to %s", len(df), len(output_cols), output_path)


if __name__ == "__main__":
    build_features("data/raw/btcusdt_4h.parquet")
