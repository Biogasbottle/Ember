import io
import logging
import os
import time
import urllib.request
import zipfile
from datetime import date, timedelta

import polars as pl

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

BASE_URL = "https://data.binance.vision/data/futures/um/daily"
SYMBOL = "BTCUSDT"
INTERVAL = "4h"
START_DATE = date(2020, 9, 1)
OUTPUT_PATH = "data/raw/btcusdt_4h.parquet"
TF_MS = 4 * 3600 * 1000


def _to_bucket(ts_ms):
    return (ts_ms // TF_MS) * TF_MS


def _date_range(start, end):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def _download_zip(url):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                return zipfile.ZipFile(io.BytesIO(resp.read()))
        except Exception as e:
            delay = [1, 2, 4][attempt]
            logger.warning("Download attempt %d failed for %s: %s. Retrying in %ds...", attempt + 1, url, e, delay)
            time.sleep(delay)
    raise RuntimeError(f"Failed to download {url} after 3 attempts")


def _fetch_klines(end_date):
    logger.info("Downloading klines from %s to %s", START_DATE, end_date)
    all_rows = []
    for d in _date_range(START_DATE, end_date):
        url = f"{BASE_URL}/klines/{SYMBOL}/{INTERVAL}/{SYMBOL}-{INTERVAL}-{d.isoformat()}.zip"
        try:
            zf = _download_zip(url)
            csv_name = zf.namelist()[0]
            data = zf.read(csv_name).decode()
            for line in data.strip().split("\n")[1:]:
                parts = line.split(",")
                all_rows.append({
                    "timestamp": int(parts[0]),
                    "open": float(parts[1]),
                    "high": float(parts[2]),
                    "low": float(parts[3]),
                    "close": float(parts[4]),
                    "volume": float(parts[5]),
                })
        except Exception as e:
            logger.warning("Skipping klines %s: %s", d, e)
        if len(all_rows) % 1000 == 0:
            logger.info("Klines: %d rows so far", len(all_rows))
    logger.info("Total klines: %d rows", len(all_rows))
    return pl.DataFrame(all_rows).sort("timestamp").unique(subset="timestamp")


def _fetch_premium_index(end_date):
    logger.info("Downloading premium index klines (funding rate)")
    earliest_funding = date(2021, 5, 1)
    all_rows = []
    for d in _date_range(max(START_DATE, earliest_funding), end_date):
        url = f"{BASE_URL}/premiumIndexKlines/{SYMBOL}/{INTERVAL}/{SYMBOL}-{INTERVAL}-{d.isoformat()}.zip"
        try:
            zf = _download_zip(url)
            csv_name = zf.namelist()[0]
            data = zf.read(csv_name).decode()
            for line in data.strip().split("\n")[1:]:
                parts = line.split(",")
                all_rows.append({
                    "timestamp": int(parts[0]),
                    "funding": float(parts[4]),
                })
        except Exception as e:
            logger.warning("Skipping premium %s: %s", d, e)
    logger.info("Total funding rows: %d", len(all_rows))
    return pl.DataFrame(all_rows).sort("timestamp").unique(subset="timestamp")


def _fetch_metrics(end_date):
    logger.info("Downloading metrics (OI) from %s to %s", START_DATE, end_date)
    all_rows = []
    for d in _date_range(START_DATE, end_date):
        url = f"{BASE_URL}/metrics/{SYMBOL}/{SYMBOL}-metrics-{d.isoformat()}.zip"
        try:
            zf = _download_zip(url)
            csv_name = zf.namelist()[0]
            data = zf.read(csv_name).decode()
            for line in data.strip().split("\n")[1:]:
                parts = line.split(",")
                ts_raw = parts[0].replace(" ", "T")
                import datetime as _dt
                ts = int(_dt.datetime.fromisoformat(ts_raw + "+00:00").timestamp() * 1000)
                all_rows.append({
                    "ts": ts,
                    "oi": float(parts[2]),
                })
        except Exception as e:
            logger.warning("Skipping metrics %s: %s", d, e)
        if len(all_rows) % 50000 == 0:
            logger.info("Metrics: %d rows so far", len(all_rows))
    logger.info("Total OI raw: %d rows", len(all_rows))
    if not all_rows:
        return pl.DataFrame(schema={"timestamp": pl.Int64, "oi": pl.Float64})
    df = pl.DataFrame(all_rows).with_columns(
        ((pl.col("ts") // TF_MS) * TF_MS).alias("timestamp")
    )
    df = df.group_by("timestamp").agg(pl.col("oi").last()).sort("timestamp")
    logger.info("Total OI bucketed: %d rows", len(df))
    return df


def fetch_and_save(output_path=OUTPUT_PATH):
    end_date = date.today() - timedelta(days=1)

    df_klines = _fetch_klines(end_date)
    df_funding = _fetch_premium_index(end_date)
    df_oi = _fetch_metrics(end_date)

    df = (
        df_klines
        .join(df_funding, on="timestamp", how="left")
        .join(df_oi, on="timestamp", how="left")
        .sort("timestamp")
    )

    null_counts = {col: df[col].null_count() for col in df.columns}
    null_cols = {k: v for k, v in null_counts.items() if v > 0}
    if null_cols:
        logger.warning("Nulls after join: %s", null_cols)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.write_parquet(output_path)
    logger.info("Saved %d rows x %d cols to %s", len(df), len(df.columns), output_path)


if __name__ == "__main__":
    fetch_and_save()
