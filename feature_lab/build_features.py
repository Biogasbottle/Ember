import logging
from graphlib import TopologicalSorter

import polars as pl

from feature_lab.labels import generate_triple_barrier_labels
from feature_lab.registry import ALL
from feature_lab.registry.base import BASE
from feature_lab.registry.combo import COMBO
from feature_lab.registry.talib import TALIB

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

LABEL_COLS = ["label_4h", "label_12h", "label_24h"]
LABEL_HORIZONS = [1, 3, 6]
OUTPUT_PATH = "data/features_v1.parquet"

REGISTRY_MAP = {"base": BASE, "combo": COMBO, "talib": TALIB}


def _frac_diff(series, d=0.3, window=180):
    import numpy as np
    n = len(series)
    weights = [1.0]
    for k in range(1, window):
        weights.append(weights[-1] * (k - 1 - d) / k)
    weights = np.array(weights)
    result = np.full(n, np.nan)
    for i in range(window - 1, n):
        result[i] = np.dot(weights, series[i - window + 1:i + 1][::-1])
    return result


def _compute_helpers(df, features):
    needs_funding_rm = any("_funding_rm180" in f.get("depends_on", []) for f in features)
    if needs_funding_rm:
        df = df.with_columns([
            pl.col("funding").rolling_mean(180, min_samples=1).alias("_funding_rm180"),
            pl.col("funding").rolling_std(180, min_samples=1).alias("_funding_rs180"),
        ])

    needs_price_vol = any("_price_vol20" in f.get("depends_on", []) for f in features)
    if needs_price_vol:
        ret = pl.col("close") / pl.col("close").shift(1) - 1
        df = df.with_columns([
            ret.rolling_std(20, min_samples=2).alias("_price_vol20"),
            ret.rolling_std(60, min_samples=2).alias("_price_vol60"),
        ])

    needs_vol_rm = any("_vol_rm180" in f.get("depends_on", []) for f in features)
    if needs_vol_rm:
        df = df.with_columns([
            pl.col("volume").rolling_mean(180, min_samples=1).alias("_vol_rm180"),
            pl.col("volume").rolling_std(180, min_samples=1).alias("_vol_rs180"),
            pl.col("volume").rolling_mean(20, min_samples=1).alias("_vol_rm20"),
        ])

    needs_frac = any(
        f["name"].startswith("ret_") or f["name"].startswith("oi_ret_")
        for f in features if "category" in f
    )
    if needs_frac:
        for col in ["close", "oi", "funding", "volume"]:
            series = df[col].to_numpy()
            frac = _frac_diff(series, d=0.3, window=180)
            df = df.with_columns(pl.Series(frac).alias(f"_frac_{col}_d03"))

    needs_talib = any("_talib_" in d for f in features for d in f.get("depends_on", []))
    if needs_talib:
        try:
            import talib
            import numpy as np

            high = df["high"].to_numpy()
            low = df["low"].to_numpy()
            close = df["close"].to_numpy()
            volume = df["volume"].to_numpy().astype("float64")

            df = df.with_columns(pl.Series(talib.RSI(close, timeperiod=14)).alias("_talib_rsi_14"))
            df = df.with_columns(pl.Series(talib.RSI(close, timeperiod=6)).alias("_talib_rsi_6"))
            macd, macd_signal, _ = talib.MACD(close)
            df = df.with_columns(pl.Series(macd).alias("_talib_macd"))
            df = df.with_columns(pl.Series(macd_signal).alias("_talib_macd_signal"))
            upper, middle, lower = talib.BBANDS(close)
            df = df.with_columns(pl.Series(upper).alias("_talib_bb_upper"))
            df = df.with_columns(pl.Series(middle).alias("_talib_bb_middle"))
            df = df.with_columns(pl.Series(lower).alias("_talib_bb_lower"))
            df = df.with_columns(pl.Series(talib.ATR(high, low, close, timeperiod=14)).alias("_talib_atr_14"))
            df = df.with_columns(pl.Series(talib.ADX(high, low, close, timeperiod=14)).alias("_talib_adx_14"))
            df = df.with_columns(pl.Series(talib.CCI(high, low, close, timeperiod=14)).alias("_talib_cci_14"))
            df = df.with_columns(pl.Series(talib.WILLR(high, low, close, timeperiod=14)).alias("_talib_willr_14"))
            stoch_k, stoch_d = talib.STOCH(high, low, close)
            df = df.with_columns(pl.Series(stoch_k).alias("_talib_stoch_k"))
            df = df.with_columns(pl.Series(stoch_d).alias("_talib_stoch_d"))
            df = df.with_columns(pl.Series(talib.MFI(high, low, close, volume, timeperiod=14)).alias("_talib_mfi_14"))
            df = df.with_columns(pl.Series(talib.ROC(close, timeperiod=6)).alias("_talib_roc_6"))
            df = df.with_columns(pl.Series(talib.ROC(close, timeperiod=12)).alias("_talib_roc_12"))
            df = df.with_columns(pl.Series(talib.EMA(close, timeperiod=12)).alias("_talib_ema_12"))
            df = df.with_columns(pl.Series(talib.EMA(close, timeperiod=26)).alias("_talib_ema_26"))
            logger.info("TA-Lib helpers computed")
        except ImportError:
            logger.warning("TA-Lib not installed, skipping TALIB features")

    return df


def build_features(raw_path, output_path=OUTPUT_PATH, registries=None):
    if registries is None:
        registries = ["base"]
    features = []
    for name in registries:
        features.extend(REGISTRY_MAP[name])
    logger.info("Using registries: %s (%d features)", registries, len(features))

    df = pl.read_parquet(raw_path)

    null_cols = [col for col in df.columns if df[col].null_count() > 0]
    if null_cols:
        logger.warning("Forward-filling nulls in columns: %s", null_cols)
        for col in null_cols:
            null_mask = df[col].is_null()
            filled_timestamps = df.filter(null_mask)["timestamp"].to_list()
            logger.info("Filled %d nulls in %s at timestamps: %s", len(filled_timestamps), col, filled_timestamps)
        df = df.with_columns(pl.all().forward_fill())

    df = _compute_helpers(df, features)

    name_to_feat = {f["name"]: f for f in features}
    graph = {f["name"]: set(f.get("depends_on", [])) for f in features}
    ts = TopologicalSorter(graph)
    order = list(ts.static_order())
    logger.info("Topological order: %s", order[:10])

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

    for name, horizon in zip(LABEL_COLS, LABEL_HORIZONS):
        logger.info("Computing label: %s (horizon=%d)", name, horizon)
        df = df.with_columns(
            generate_triple_barrier_labels(df, horizon).alias(name)
        )

    before = len(df)
    df = df.drop_nulls()
    logger.info("drop_nulls: %d rows removed, %d remaining", before - len(df), len(df))

    feature_cols = [f["name"] for f in features]
    output_cols = ["timestamp"] + feature_cols + LABEL_COLS
    df.select(output_cols).write_parquet(output_path)
    logger.info("Saved %d rows x %d cols to %s", len(df), len(output_cols), output_path)


if __name__ == "__main__":
    import sys
    registries = sys.argv[1:] if len(sys.argv) > 1 else ["base"]
    build_features("data/raw/btcusdt_4h.parquet", registries=registries)
