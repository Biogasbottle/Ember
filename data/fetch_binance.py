import logging
import time

import ccxt
import polars as pl

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

SYMBOL = "BTC/USDT:USDT"
TIMEFRAME = "4h"
SINCE_MS = 1609459200000  # 2021-01-01
RETRY_COUNT = 3
RETRY_DELAYS = [1, 2, 4]
OUTPUT_PATH = "data/raw/btcusdt_4h.parquet"


def _fetch_with_retry(exchange, method_name, *args, **kwargs):
    last_error = None
    for attempt in range(1, RETRY_COUNT + 1):
        try:
            method = getattr(exchange, method_name)
            return method(*args, **kwargs)
        except Exception as exc:
            last_error = exc
            if attempt < RETRY_COUNT:
                delay = RETRY_DELAYS[attempt - 1]
                logger.warning(
                    "%s attempt %d failed: %s. Retrying in %ds...",
                    method_name, attempt, exc, delay,
                )
                time.sleep(delay)
    logger.error("%s failed after %d attempts: %s", method_name, RETRY_COUNT, last_error)
    raise last_error


def fetch_and_save(output_path=OUTPUT_PATH):
    exchange = ccxt.binance()
    logger.info("Fetching OHLCV for %s %s since %s", SYMBOL, TIMEFRAME, SINCE_MS)
    ohlcv = _fetch_with_retry(exchange, "fetch_ohlcv", SYMBOL, TIMEFRAME, since=SINCE_MS)
    logger.info("Fetched %d OHLCV candles", len(ohlcv))

    logger.info("Fetching OI history")
    oi = _fetch_with_retry(exchange, "fetch_open_interest_history", SYMBOL, TIMEFRAME, since=SINCE_MS)
    logger.info("Fetched %d OI records", len(oi))

    logger.info("Fetching funding rate history")
    funding = _fetch_with_retry(exchange, "fetch_funding_rate_history", SYMBOL, since=SINCE_MS)
    logger.info("Fetched %d funding rate records", len(funding))

    logger.info("Fetching liquidations")
    liq = _fetch_with_retry(exchange, "fetch_liquidations", SYMBOL, since=SINCE_MS)
    logger.info("Fetched %d liquidation records", len(liq))

    df_ohlcv = pl.DataFrame(
        ohlcv,
        schema=["timestamp", "open", "high", "low", "close", "volume"],
        orient="row",
    )
    df_oi = pl.DataFrame(
        oi, schema=["timestamp", "oi"], orient="row",
    )
    df_funding = pl.DataFrame(
        funding, schema=["timestamp", "funding"], orient="row",
    )
    df_liq = pl.DataFrame(
        liq, schema=["timestamp", "long_liq", "short_liq"], orient="row",
    )

    df = (
        df_ohlcv
        .join(df_oi, on="timestamp", how="left")
        .join(df_funding, on="timestamp", how="left")
        .join(df_liq, on="timestamp", how="left")
        .sort("timestamp")
    )

    null_counts = {col: df[col].null_count() for col in df.columns}
    null_cols = {k: v for k, v in null_counts.items() if v > 0}
    if null_cols:
        logger.warning("Columns with nulls after join: %s", null_cols)

    df.write_parquet(output_path)
    logger.info("Saved %d rows to %s", len(df), output_path)


if __name__ == "__main__":
    fetch_and_save()
