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
    "ret_1", "ret_3", "ret_6",
    "oi_ret_1",
    "funding_z",
    "future_return_24h",
}


def _make_raw_dataset(n_rows=300):
    base = 1700000000000
    return pl.DataFrame({
        "timestamp": [base + i * 14400000 for i in range(n_rows)],
        "open": [42000.0 + i * 10 + (i % 7) * 50 for i in range(n_rows)],
        "high": [42100.0 + i * 10 + (i % 7) * 50 for i in range(n_rows)],
        "low": [41900.0 + i * 10 + (i % 7) * 50 for i in range(n_rows)],
        "close": [42050.0 + i * 10 + (i % 7) * 50 for i in range(n_rows)],
        "volume": [100.0 + i * 2 for i in range(n_rows)],
        "oi": [50000.0 + i * 100 + (i % 13) * 1000 for i in range(n_rows)],
        "funding": [0.0001 + (i % 20) * 0.00005 - 0.0005 for i in range(n_rows)],
    })


def test_registry_has_all_features():
    """#3: Unit — registry exports 5 features with correct structure."""
    from feature_lab.registry import FEATURES

    assert len(FEATURES) == 5, f"expected 5 features, got {len(FEATURES)}"
    expected_ids = {"P01", "P02", "P03", "O01", "F01"}
    actual_ids = {f["id"] for f in FEATURES}
    assert actual_ids == expected_ids, f"feature ids mismatch: {actual_ids}"
    for f in FEATURES:
        for key in ["id", "name", "category", "expression"]:
            assert key in f, f"missing key {key} in {f['id']}"
        assert isinstance(f["expression"], str) and len(f["expression"]) > 0


def test_registry_topological_order():
    """#3: Unit — helper columns precede dependent features."""
    from graphlib import TopologicalSorter

    from feature_lab.registry import FEATURES

    name_to_deps = {f["name"]: set(f.get("depends_on", [])) for f in FEATURES}
    graph = {name: deps for name, deps in name_to_deps.items()}
    ts = TopologicalSorter(graph)
    order = list(ts.static_order())

    assert "_funding_rm180" in order
    assert order.index("_funding_rm180") < order.index("funding_z")


def test_build_features_produces_parquet(tmp_path):
    """#3: CF — build_features produces correct output."""
    raw_path = tmp_path / "raw.parquet"
    _make_raw_dataset(300).write_parquet(raw_path)

    from feature_lab.build_features import build_features
    output = tmp_path / "features_v1.parquet"
    build_features(raw_path, output)

    assert output.exists(), "output parquet not created"
    df = pl.read_parquet(output)
    assert set(df.columns) == EXPECTED_FEATURE_COLS, f"schema mismatch: {df.columns}"
    total_nulls = sum(df[col].null_count() for col in df.columns)
    assert total_nulls == 0, f"output contains {total_nulls} nulls"
    assert df["timestamp"].is_sorted(), "timestamp not sorted"


# ── #4: Model Training ────────────────────────────────────────────────────


def test_train_lightgbm_produces_artifacts(tmp_path):
    """#4: CF — train LightGBM produces valid artifacts."""
    import lightgbm as lgb

    raw_path = tmp_path / "raw.parquet"
    _make_raw_dataset(400).write_parquet(raw_path)

    from feature_lab.build_features import build_features
    features_path = tmp_path / "features_v1.parquet"
    build_features(raw_path, features_path)

    model_dir = tmp_path / "models"
    reports_dir = tmp_path / "reports"
    model_dir.mkdir()
    reports_dir.mkdir()

    from research.train_lightgbm import train
    train(features_path, model_dir, reports_dir)

    pkl_path = model_dir / "lgbm_v1.pkl"
    meta_path = model_dir / "lgbm_v1_meta.json"
    metrics_path = reports_dir / "metrics_v1.json"
    preds_path = reports_dir / "predictions_v1.parquet"

    assert pkl_path.exists()
    assert meta_path.exists()
    assert metrics_path.exists()
    assert preds_path.exists()

    model = lgb.Booster(model_file=str(pkl_path))
    assert model is not None

    meta = json.loads(meta_path.read_text())
    assert "features" in meta and len(meta["features"]) == 5
    assert "label" in meta
    assert "hyperparams" in meta

    metrics = json.loads(metrics_path.read_text())
    for key in ["rmse", "mae", "correlation"]:
        assert key in metrics
        assert isinstance(metrics[key], float)

    preds = pl.read_parquet(preds_path)
    assert set(preds.columns) >= {"timestamp", "pred", "actual"}
    total_nulls = sum(preds[col].null_count() for col in preds.columns)
    assert total_nulls == 0
    assert preds["timestamp"].is_sorted()
    assert len(preds) > 0
