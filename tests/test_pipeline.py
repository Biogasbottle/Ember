import json
import subprocess
import sys
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parent.parent


def test_project_scaffolding_files_exist():
    """#1: Verify scaffolding files and directories exist."""
    assert (ROOT / "requirements.txt").exists(), "requirements.txt missing"
    assert (ROOT / "ruff.toml").exists(), "ruff.toml missing"
    for d in ["data/raw", "feature_lab", "research", "models", "reports"]:
        assert (ROOT / d).is_dir(), f"directory {d} missing"


def test_pip_install_from_requirements():
    """#1: pip install succeeds."""
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", str(ROOT / "requirements.txt")],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"pip install failed:\n{result.stderr}"


# ── #2: Data Fetch ──────────────────────────────────────────────────────

RAW_SCHEMA = {"timestamp", "open", "high", "low", "close", "volume", "oi", "funding"}


def test_fetch_binance_produces_parquet(tmp_path, monkeypatch):
    """#2: Verify fetch produces correctly-schemed parquet with no placeholder columns."""
    kline_line = (
        "1700006400000,42000.0,42100.0,41900.0,42050.0,100.0,"
        "1700020799999,4200000.0,10,50.0,2100000.0,0"
    )
    kline_hdr = (
        "open_time,open,high,low,close,volume,close_time,"
        "quote_volume,count,taker_buy_volume,taker_buy_quote_volume,ignore"
    )
    kline_csv = kline_hdr + "\n" + kline_line

    premium_line = (
        "1700006400000,0.0001,0.00015,0.00005,0.0001,0,"
        "1700020799999,0,2880,0,0,0"
    )
    premium_hdr = (
        "open_time,open,high,low,close,volume,close_time,"
        "quote_volume,count,taker_buy_volume,taker_buy_quote_volume,ignore"
    )
    premium_csv = premium_hdr + "\n" + premium_line

    metrics_hdr = "create_time,symbol,sum_open_interest,sum_open_interest_value"
    metrics_hdr += ",count_toptrader_long_short_ratio,sum_toptrader_long_short_ratio"
    metrics_hdr += ",count_long_short_ratio,sum_taker_long_short_vol_ratio"
    metrics_csv = metrics_hdr + "\n2023-11-14 20:00:00,BTCUSDT,50000.0,2100000000.0,1.0,1.0,1.0,1.0"

    def fake_download(url):
        import io
        import zipfile
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            if "klines" in url:
                zf.writestr("k.csv", kline_csv)
            elif "premium" in url:
                zf.writestr("p.csv", premium_csv)
            elif "metrics" in url:
                zf.writestr("m.csv", metrics_csv)
            else:
                raise FileNotFoundError(url)
        return zipfile.ZipFile(io.BytesIO(buf.getvalue()))

    from data import fetch_binance
    monkeypatch.setattr(fetch_binance, "_download_zip", fake_download)

    output = tmp_path / "btcusdt_4h.parquet"
    fetch_binance.fetch_and_save(output)

    assert output.exists(), "output parquet not created"
    df = pl.read_parquet(output)
    assert set(df.columns) == RAW_SCHEMA, f"schema mismatch: {df.columns}"
    assert len(df) > 0, "output is empty"
    assert df["timestamp"].is_sorted(), "timestamp not sorted"


# ── #3: Feature Registry + Engineering ────────────────────────────────────

EXPECTED_FEATURE_COLS = {
    "timestamp",
    "ret_1", "ret_3", "ret_6", "ret_12", "ret_24",
    "volatility_20", "volatility_60", "high_low_range",
    "oi_ret_1", "oi_ret_3", "oi_ret_6", "oi_ret_12", "oi_ret_accel",
    "funding_z", "funding_change_1", "funding_signal",
    "volume_z", "volume_change_1", "volume_change_6", "relative_volume",
    "label_4h", "label_12h", "label_24h",
}


def _make_raw_dataset(n_rows=300):
    import numpy as np
    base = 1700000000000
    rng = np.random.default_rng(42)
    close_vals = [42000.0]
    open_vals = [42000.0]
    high_vals = [42100.0]
    low_vals = [41900.0]
    oi_vals = [50000.0]
    funding_vals = [0.0001]
    for i in range(1, n_rows):
        ret = rng.normal(0, 0.02)
        close = close_vals[-1] * (1 + ret)
        close_vals.append(max(close, 1.0))
        open_vals.append(close_vals[-2])
        high_vals.append(close_vals[-1] * (1 + abs(rng.normal(0, 0.005))))
        low_vals.append(close_vals[-1] * (1 - abs(rng.normal(0, 0.005))))
        oi_vals.append(oi_vals[-1] * (1 + rng.normal(0, 0.01)))
        funding_vals.append(funding_vals[-1] + rng.normal(0, 0.0001))
    return pl.DataFrame({
        "timestamp": [base + i * 14400000 for i in range(n_rows)],
        "open": open_vals, "high": high_vals, "low": low_vals, "close": close_vals,
        "volume": [100.0 + i * 2 + rng.uniform(0, 50) for i in range(n_rows)],
        "oi": oi_vals,
        "funding": funding_vals,
    })


def test_registry_has_all_features():
    """#3: Unit — registry exports 20 base features with correct structure."""
    from feature_lab.registry import BASE

    assert len(BASE) == 20, f"expected 20 base features, got {len(BASE)}"
    for f in BASE:
        for key in ["id", "name", "category", "expression"]:
            assert key in f, f"missing key {key} in {f['id']}"
        assert isinstance(f["expression"], str) and len(f["expression"]) > 0


def test_registry_combo_features():
    """V2.2: Unit — combo registry exports features with dependencies."""
    from feature_lab.registry import COMBO

    assert len(COMBO) == 12, f"expected 12 combo features, got {len(COMBO)}"
    for f in COMBO:
        assert "depends_on" in f
        assert len(f["depends_on"]) >= 1, f"{f['id']} should depend on base features"


def test_registry_talib_features():
    """V2.2: Unit — talib registry exports features with _talib_ helpers."""
    from feature_lab.registry import TALIB

    assert len(TALIB) == 23, f"expected 23 talib features, got {len(TALIB)}"
    for f in TALIB:
        assert any("_talib_" in d for d in f.get("depends_on", [])), \
            f"{f['id']} should depend on _talib_ helper"


def test_registry_topological_order():
    """#3: Unit — helper columns precede dependent features."""
    from graphlib import TopologicalSorter
    from feature_lab.registry import ALL

    name_to_deps = {f["name"]: set(f.get("depends_on", [])) for f in ALL}
    graph = {name: deps for name, deps in name_to_deps.items()}
    ts = TopologicalSorter(graph)
    order = list(ts.static_order())

    assert "_funding_rm180" in order
    assert order.index("_funding_rm180") < order.index("funding_z")


def test_build_features_produces_parquet(tmp_path):
    """#3: CF — build_features produces correct output with triple barrier labels."""
    raw_path = tmp_path / "raw.parquet"
    _make_raw_dataset(300).write_parquet(raw_path)

    from feature_lab.build_features import build_features
    output = tmp_path / "features_v1.parquet"
    build_features(raw_path, output, registries=["base"])

    assert output.exists(), "output parquet not created"
    df = pl.read_parquet(output)
    assert set(df.columns) == EXPECTED_FEATURE_COLS, f"schema mismatch: {df.columns}"
    total_nulls = sum(df[col].null_count() for col in df.columns)
    assert total_nulls == 0, f"output contains {total_nulls} nulls"
    assert df["timestamp"].is_sorted(), "timestamp not sorted"
    for lbl in ["label_4h", "label_12h", "label_24h"]:
        vals = df[lbl].unique().to_list()
        assert all(v in (-1, 0, 1) for v in vals), f"{lbl} has invalid values: {vals}"


# ── V2.1#1: Triple Barrier Labeling ─────────────────────────────────────


def test_triple_barrier_all_up():
    """V2.1#1: Unit — steadily rising price with high vol → all labels +1."""
    from feature_lab.labels import generate_triple_barrier_labels
    base = 1700000000000
    n = 120
    rng = __import__("numpy").random.default_rng(42)
    close_vals = [42000.0]
    for _ in range(n - 1):
        close_vals.append(close_vals[-1] * (1 + rng.uniform(0.01, 0.05)))
    df = pl.DataFrame({
        "timestamp": [base + i * 14400000 for i in range(n)],
        "close": close_vals,
    })
    labels = generate_triple_barrier_labels(df, horizon=6, vol_multiplier=1.0)
    vals = labels.drop_nulls().to_list()
    up_count = sum(1 for v in vals if v == 1)
    assert up_count > 0, f"expected some +1 labels, got none in {len(vals)} values"


def test_triple_barrier_all_down():
    """V2.1#1: Unit — steadily falling price → all labels -1."""
    from feature_lab.labels import generate_triple_barrier_labels
    base = 1700000000000
    n = 120
    rng = __import__("numpy").random.default_rng(42)
    close_vals = [42000.0]
    for _ in range(n - 1):
        close_vals.append(close_vals[-1] * (1 - rng.uniform(0.01, 0.05)))
    df = pl.DataFrame({
        "timestamp": [base + i * 14400000 for i in range(n)],
        "close": close_vals,
    })
    labels = generate_triple_barrier_labels(df, horizon=6, vol_multiplier=1.0)
    vals = labels.drop_nulls().to_list()
    down_count = sum(1 for v in vals if v == -1)
    assert down_count > 0, f"expected some -1 labels, got none in {len(vals)} values"


def test_triple_barrier_shape():
    """V2.1#1: Unit — output same length as input."""
    from feature_lab.labels import generate_triple_barrier_labels
    base = 1700000000000
    df = pl.DataFrame({
        "timestamp": [base + i * 14400000 for i in range(100)],
        "close": [42000.0 + (i % 5) * 10 for i in range(100)],
    })
    labels = generate_triple_barrier_labels(df, horizon=6, vol_multiplier=2.0)
    assert len(labels) == 100
    assert labels.null_count() >= 6  # last 6 rows are NaN (no forward data)


# ── #4: Model Training ────────────────────────────────────────────────────


def test_train_lightgbm_produces_artifacts(tmp_path):
    """V2.1: CF — multi-horizon training produces 3 models + consensus."""
    import lightgbm as lgb

    raw_path = tmp_path / "raw.parquet"
    _make_raw_dataset(1000).write_parquet(raw_path)

    from feature_lab.build_features import build_features
    features_path = tmp_path / "features_v1.parquet"
    build_features(raw_path, features_path, registries=["base"])

    model_dir = tmp_path / "models"
    reports_dir = tmp_path / "reports"
    model_dir.mkdir()
    reports_dir.mkdir()

    from research.train_lightgbm import train
    train(features_path, model_dir, reports_dir)

    for lbl in ["label_4h", "label_12h", "label_24h"]:
        pkl = model_dir / f"lgbm_v2.1_{lbl}.pkl"
        assert pkl.exists(), f"{pkl} missing"
        model = lgb.Booster(model_file=str(pkl))
        assert model is not None

    meta = json.loads((model_dir / "lgbm_v2.1_meta.json").read_text())
    assert "features" in meta and len(meta["features"]) == 20
    assert "labels" in meta and len(meta["labels"]) == 3

    metrics = json.loads((reports_dir / "metrics_v2.1.json").read_text())
    assert "consensus" in metrics

    preds = pl.read_parquet(reports_dir / "predictions_v2.1.parquet")
    assert "consensus_dir" in preds.columns
    assert len(preds) > 0
