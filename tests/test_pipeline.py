import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_project_scaffolding_files_exist():
    """#1: Verify requirements.txt, ruff.toml, and directory tree exist."""
    assert (ROOT / "requirements.txt").exists(), "requirements.txt missing"
    assert (ROOT / "ruff.toml").exists(), "ruff.toml missing"

    dirs = ["data/raw", "feature_lab", "research", "models", "reports"]
    for d in dirs:
        assert (ROOT / d).is_dir(), f"directory {d} missing"


def test_pip_install_from_requirements():
    """#1: Verify pip install -r requirements.txt works."""
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", str(ROOT / "requirements.txt")],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"pip install failed:\n{result.stderr}"


# ── #2: Data Fetch ──────────────────────────────────────────────────────

FAKE_OHLCV = [
    [1700000000000, 42000.0, 42100.0, 41900.0, 42050.0, 100.0],
    [1700014400000, 42050.0, 42200.0, 42000.0, 42150.0, 120.0],
    [1700028800000, 42150.0, 42300.0, 42100.0, 42200.0, 110.0],
]

FAKE_OI = [
    [1700000000000, 50000.0],
    [1700014400000, 51000.0],
    [1700028800000, 50500.0],
]

FAKE_FUNDING = [
    [1700000000000, 0.0001],
    [1700014400000, 0.0002],
    [1700028800000, 0.00015],
]

FAKE_LIQ = [
    [1700000000000, 500.0, 300.0],
    [1700014400000, 700.0, 400.0],
    [1700028800000, 200.0, 600.0],
]

EXPECTED_SCHEMA = {
    "timestamp", "open", "high", "low", "close", "volume",
    "oi", "funding", "long_liq", "short_liq",
}


def test_fetch_binance_produces_parquet(tmp_path, monkeypatch):
    """#2: Verify fetch_and_save produces a correctly-schemed parquet file."""
    import ccxt
    import polars as pl

    class FakeExchange:
        def fetch_ohlcv(self, *args, **kwargs):
            return FAKE_OHLCV

        def fetch_open_interest_history(self, *args, **kwargs):
            return FAKE_OI

        def fetch_funding_rate_history(self, *args, **kwargs):
            return FAKE_FUNDING

        def fetch_liquidations(self, *args, **kwargs):
            return FAKE_LIQ

    fake = FakeExchange()
    fake.has = {"watchOHLCV": False}
    monkeypatch.setattr(ccxt, "binance", lambda: fake)

    from data.fetch_binance import fetch_and_save

    output = tmp_path / "btcusdt_4h.parquet"
    fetch_and_save(output)

    assert output.exists(), "output parquet not created"
    df = pl.read_parquet(output)
    assert set(df.columns) == EXPECTED_SCHEMA, f"schema mismatch: {df.columns}"
    total_nulls = sum(df[col].null_count() for col in df.columns)
    assert total_nulls == 0, f"output contains {total_nulls} nulls"
    assert df["timestamp"].is_sorted(), "timestamp not sorted"


# ── #3: Feature Registry + Engineering ────────────────────────────────────

EXPECTED_FEATURE_COLS = {
    "timestamp",
    "ret_1", "ret_3", "ret_6",
    "oi_ret_1",
    "funding_z",
    "liq_total", "liq_shock",
    "future_return_24h",
}


def _make_raw_dataset(n_rows=300):
    """Create a synthetic raw parquet with enough rows to survive roll(180)+drop_nulls."""
    import polars as pl

    base = 1700000000000
    df = pl.DataFrame({
        "timestamp": [base + i * 14400000 for i in range(n_rows)],
        "open": [42000.0 + i * 10 + (i % 7) * 50 for i in range(n_rows)],
        "high": [42100.0 + i * 10 + (i % 7) * 50 for i in range(n_rows)],
        "low": [41900.0 + i * 10 + (i % 7) * 50 for i in range(n_rows)],
        "close": [42050.0 + i * 10 + (i % 7) * 50 for i in range(n_rows)],
        "volume": [100.0 + i * 2 for i in range(n_rows)],
        "oi": [50000.0 + i * 100 + (i % 13) * 1000 for i in range(n_rows)],
        "funding": [0.0001 + (i % 20) * 0.00005 - 0.0005 for i in range(n_rows)],
        "long_liq": [500.0 + (i % 5) * 200 for i in range(n_rows)],
        "short_liq": [300.0 + (i % 7) * 150 for i in range(n_rows)],
    })
    return df


def test_registry_has_all_features():
    """#3: Unit — registry exports 7 features with correct structure."""
    from feature_lab.registry import FEATURES

    assert len(FEATURES) == 7, f"expected 7 features, got {len(FEATURES)}"

    expected_ids = {"P01", "P02", "P03", "O01", "F01", "L01", "L02"}
    actual_ids = {f["id"] for f in FEATURES}
    assert actual_ids == expected_ids, f"feature ids mismatch: {actual_ids}"

    for f in FEATURES:
        assert "id" in f
        assert "name" in f
        assert "category" in f
        assert "expression" in f
        assert isinstance(f["expression"], str) and len(f["expression"]) > 0


def test_registry_topological_order():
    """#3: Unit — L02 depends on liq_total; topological sort places liq_total before liq_shock."""
    from graphlib import TopologicalSorter

    from feature_lab.registry import FEATURES

    name_to_deps = {f["name"]: set(f.get("depends_on", [])) for f in FEATURES}
    graph = {name: deps for name, deps in name_to_deps.items()}
    ts = TopologicalSorter(graph)
    order = list(ts.static_order())

    # liq_total must appear before liq_shock (L02 depends on L01's output + _liq_rm180)
    assert order.index("liq_total") < order.index("liq_shock"), \
        f"liq_total must come before liq_shock but order is {order}"
    # _liq_rm180 helper must appear before liq_shock
    assert order.index("liq_total") < order.index("liq_shock"), \
        "liq_total must come before liq_shock"


def test_build_features_produces_parquet(tmp_path):
    """#3: CF — build_features reads raw, produces features_v1 parquet with correct columns."""
    import polars as pl

    raw_path = tmp_path / "raw.parquet"
    raw = _make_raw_dataset(300)
    raw.write_parquet(raw_path)

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
    """#4: CF — train LightGBM, verify model/metrics/predictions files exist and are valid."""
    import json

    import lightgbm as lgb
    import polars as pl

    raw_path = tmp_path / "raw.parquet"
    raw = _make_raw_dataset(400)
    raw.write_parquet(raw_path)

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

    assert pkl_path.exists(), "model pkl missing"
    assert meta_path.exists(), "model meta missing"
    assert metrics_path.exists(), "metrics missing"
    assert preds_path.exists(), "predictions missing"

    model = lgb.Booster(model_file=str(pkl_path))
    assert model is not None

    meta = json.loads(meta_path.read_text())
    assert "features" in meta and len(meta["features"]) == 7
    assert "label" in meta
    assert "hyperparams" in meta

    metrics = json.loads(metrics_path.read_text())
    for key in ["rmse", "mae", "correlation"]:
        assert key in metrics, f"metric {key} missing"
        assert isinstance(metrics[key], float), f"metric {key} not float"

    preds = pl.read_parquet(preds_path)
    assert set(preds.columns) >= {"timestamp", "pred", "actual"}, f"bad columns: {preds.columns}"
    total_nulls = sum(preds[col].null_count() for col in preds.columns)
    assert total_nulls == 0, f"predictions contain {total_nulls} nulls"
    assert preds["timestamp"].is_sorted(), "predictions timestamp not sorted"
    assert len(preds) > 0
