import numpy as np
import polars as pl


def generate_triple_barrier_labels(df, horizon, vol_multiplier=2.0):
    close = df["close"].to_numpy()
    n = len(close)

    ret = np.diff(close) / close[:-1]
    ret = np.insert(ret, 0, np.nan)

    def _rolling_std(arr, window):
        result = np.full(len(arr), np.nan)
        for i in range(window - 1, len(arr)):
            s = np.nanstd(arr[max(0, i - window + 1):i + 1])
            if arr[i] is not None and not np.isnan(arr[i]):
                result[i] = s
        return result

    vol = _rolling_std(ret, 60)

    labels = []
    for i in range(n):
        if i + horizon >= n:
            labels.append(None)
            continue
        if np.isnan(vol[i]) or vol[i] < 1e-8:
            labels.append(None)
            continue
        entry = close[i]
        upper = entry * (1 + vol_multiplier * vol[i])
        lower = entry * (1 - vol_multiplier * vol[i])
        result = 0
        for j in range(1, horizon + 1):
            if close[i + j] >= upper:
                result = 1
                break
            elif close[i + j] <= lower:
                result = -1
                break
        labels.append(result)
    return pl.Series(labels, dtype=pl.Int32)
