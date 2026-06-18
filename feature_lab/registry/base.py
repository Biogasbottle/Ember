BASE = [
    # ── Price (P) ──
    {
        "id": "P01", "name": "ret_1", "category": "price",
        "expression": "_frac_close_d03 / LAG(_frac_close_d03, 1) OVER (ORDER BY timestamp) - 1",
        "depends_on": [],
    },
    {
        "id": "P02", "name": "ret_3", "category": "price",
        "expression": "_frac_close_d03 / LAG(_frac_close_d03, 3) OVER (ORDER BY timestamp) - 1",
        "depends_on": [],
    },
    {
        "id": "P03", "name": "ret_6", "category": "price",
        "expression": "_frac_close_d03 / LAG(_frac_close_d03, 6) OVER (ORDER BY timestamp) - 1",
        "depends_on": [],
    },
    {
        "id": "P04", "name": "ret_12", "category": "price",
        "expression": "_frac_close_d03 / LAG(_frac_close_d03, 12) OVER (ORDER BY timestamp) - 1",
        "depends_on": [],
    },
    {
        "id": "P05", "name": "ret_24", "category": "price",
        "expression": "_frac_close_d03 / LAG(_frac_close_d03, 24) OVER (ORDER BY timestamp) - 1",
        "depends_on": [],
    },
    {
        "id": "P06", "name": "volatility_20", "category": "price",
        "expression": "_price_vol20",
        "depends_on": ["_price_vol20"],
    },
    {
        "id": "P07", "name": "volatility_60", "category": "price",
        "expression": "_price_vol60",
        "depends_on": ["_price_vol60"],
    },
    {
        "id": "P08", "name": "high_low_range", "category": "price",
        "expression": "(high - low) / close",
        "depends_on": [],
    },
    # ── Open Interest (O) ──
    {
        "id": "O01", "name": "oi_ret_1", "category": "oi",
        "expression": "_frac_oi_d03 / LAG(_frac_oi_d03, 1) OVER (ORDER BY timestamp) - 1",
        "depends_on": [],
    },
    {
        "id": "O02", "name": "oi_ret_3", "category": "oi",
        "expression": "_frac_oi_d03 / LAG(_frac_oi_d03, 3) OVER (ORDER BY timestamp) - 1",
        "depends_on": [],
    },
    {
        "id": "O03", "name": "oi_ret_6", "category": "oi",
        "expression": "_frac_oi_d03 / LAG(_frac_oi_d03, 6) OVER (ORDER BY timestamp) - 1",
        "depends_on": [],
    },
    {
        "id": "O04", "name": "oi_ret_12", "category": "oi",
        "expression": "_frac_oi_d03 / LAG(_frac_oi_d03, 12) OVER (ORDER BY timestamp) - 1",
        "depends_on": [],
    },
    {
        "id": "O05", "name": "oi_ret_accel", "category": "oi",
        "expression": "oi_ret_1 - LAG(oi_ret_1, 1) OVER (ORDER BY timestamp)",
        "depends_on": ["oi_ret_1"],
    },
    # ── Funding (F) ──
    {
        "id": "F01", "name": "funding_z", "category": "funding",
        "expression": "(funding - _funding_rm180) / (_funding_rs180 + 0.00000001)",
        "depends_on": ["_funding_rm180", "_funding_rs180"],
    },
    {
        "id": "F02", "name": "funding_change_1", "category": "funding",
        "expression": "funding - LAG(funding, 1) OVER (ORDER BY timestamp)",
        "depends_on": [],
    },
    {
        "id": "F03", "name": "funding_signal", "category": "funding",
        "expression": "CASE WHEN funding > LAG(funding, 1) OVER (ORDER BY timestamp) THEN 1 ELSE 0 END",
        "depends_on": [],
    },
    # ── Volume (V) ──
    {
        "id": "V01", "name": "volume_z", "category": "volume",
        "expression": "(volume - _vol_rm180) / (_vol_rs180 + 0.00000001)",
        "depends_on": ["_vol_rm180", "_vol_rs180"],
    },
    {
        "id": "V02", "name": "volume_change_1", "category": "volume",
        "expression": "volume / LAG(volume, 1) OVER (ORDER BY timestamp) - 1",
        "depends_on": [],
    },
    {
        "id": "V03", "name": "volume_change_6", "category": "volume",
        "expression": "volume / LAG(volume, 6) OVER (ORDER BY timestamp) - 1",
        "depends_on": [],
    },
    {
        "id": "V04", "name": "relative_volume", "category": "volume",
        "expression": "volume / (_vol_rm20 + 0.00000001)",
        "depends_on": ["_vol_rm20"],
    },
]
