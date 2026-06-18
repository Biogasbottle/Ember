COMBO = [
    # ── Price × OI ──
    {
        "id": "X01", "name": "px_oi_ret_1", "category": "combo",
        "expression": "ret_1 * oi_ret_1",
        "depends_on": ["ret_1", "oi_ret_1"],
    },
    {
        "id": "X02", "name": "px_oi_ret_6", "category": "combo",
        "expression": "ret_6 * oi_ret_6",
        "depends_on": ["ret_6", "oi_ret_6"],
    },
    {
        "id": "X03", "name": "px_oi_diff", "category": "combo",
        "expression": "ret_1 - oi_ret_1",
        "depends_on": ["ret_1", "oi_ret_1"],
    },
    # ── Price × Volume ──
    {
        "id": "X04", "name": "ret_x_vol", "category": "combo",
        "expression": "ret_1 * volume_z",
        "depends_on": ["ret_1", "volume_z"],
    },
    {
        "id": "X05", "name": "ret_x_relvol", "category": "combo",
        "expression": "ret_6 * relative_volume",
        "depends_on": ["ret_6", "relative_volume"],
    },
    # ── OI × Funding ──
    {
        "id": "X06", "name": "oi_funding_z", "category": "combo",
        "expression": "oi_ret_1 * funding_z",
        "depends_on": ["oi_ret_1", "funding_z"],
    },
    {
        "id": "X07", "name": "oi_funding_dir", "category": "combo",
        "expression": "CASE WHEN oi_ret_1 > 0 AND funding_z > 0 THEN 1 WHEN oi_ret_1 < 0 AND funding_z < 0 THEN -1 ELSE 0 END",
        "depends_on": ["oi_ret_1", "funding_z"],
    },
    # ── Volatility × Volume ──
    {
        "id": "X08", "name": "vol_vol_chg", "category": "combo",
        "expression": "volatility_20 * volume_change_6",
        "depends_on": ["volatility_20", "volume_change_6"],
    },
    {
        "id": "X09", "name": "highvol_ret", "category": "combo",
        "expression": "CASE WHEN volatility_20 > volatility_60 THEN ret_1 ELSE 0 END",
        "depends_on": ["volatility_20", "volatility_60", "ret_1"],
    },
    # ── Momentum × Funding ──
    {
        "id": "X10", "name": "mom_funding", "category": "combo",
        "expression": "CASE WHEN ret_6 > 0 AND funding_change_1 > 0 THEN 1 WHEN ret_6 < 0 AND funding_change_1 < 0 THEN -1 ELSE 0 END",
        "depends_on": ["ret_6", "funding_change_1"],
    },
    # ── Price × Volatility ──
    {
        "id": "X11", "name": "ret_risk_adj_6", "category": "combo",
        "expression": "ret_6 / (volatility_60 + 0.00000001)",
        "depends_on": ["ret_6", "volatility_60"],
    },
    {
        "id": "X12", "name": "ret_risk_adj_1", "category": "combo",
        "expression": "ret_1 / (volatility_20 + 0.00000001)",
        "depends_on": ["ret_1", "volatility_20"],
    },
]
