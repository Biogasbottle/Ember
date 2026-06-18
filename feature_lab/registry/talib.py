TALIB = [
    # ── Momentum ──
    {
        "id": "T01", "name": "rsi_14", "category": "talib",
        "expression": "_talib_rsi_14",
        "depends_on": ["_talib_rsi_14"],
    },
    {
        "id": "T02", "name": "rsi_6", "category": "talib",
        "expression": "_talib_rsi_6",
        "depends_on": ["_talib_rsi_6"],
    },
    {
        "id": "T03", "name": "macd", "category": "talib",
        "expression": "_talib_macd",
        "depends_on": ["_talib_macd"],
    },
    {
        "id": "T04", "name": "macd_signal", "category": "talib",
        "expression": "_talib_macd_signal",
        "depends_on": ["_talib_macd_signal"],
    },
    {
        "id": "T05", "name": "macd_hist", "category": "talib",
        "expression": "_talib_macd - _talib_macd_signal",
        "depends_on": ["_talib_macd", "_talib_macd_signal"],
    },
    {
        "id": "T06", "name": "bb_upper", "category": "talib",
        "expression": "_talib_bb_upper",
        "depends_on": ["_talib_bb_upper"],
    },
    {
        "id": "T07", "name": "bb_middle", "category": "talib",
        "expression": "_talib_bb_middle",
        "depends_on": ["_talib_bb_middle"],
    },
    {
        "id": "T08", "name": "bb_lower", "category": "talib",
        "expression": "_talib_bb_lower",
        "depends_on": ["_talib_bb_lower"],
    },
    {
        "id": "T09", "name": "bb_width", "category": "talib",
        "expression": "(_talib_bb_upper - _talib_bb_lower) / (_talib_bb_middle + 0.00000001)",
        "depends_on": ["_talib_bb_upper", "_talib_bb_lower", "_talib_bb_middle"],
    },
    {
        "id": "T10", "name": "bb_pct", "category": "talib",
        "expression": "(close - _talib_bb_lower) / (_talib_bb_upper - _talib_bb_lower + 0.00000001)",
        "depends_on": ["_talib_bb_upper", "_talib_bb_lower"],
    },
    {
        "id": "T11", "name": "atr_14", "category": "talib",
        "expression": "_talib_atr_14",
        "depends_on": ["_talib_atr_14"],
    },
    {
        "id": "T12", "name": "atr_pct", "category": "talib",
        "expression": "_talib_atr_14 / (close + 0.00000001)",
        "depends_on": ["_talib_atr_14"],
    },
    {
        "id": "T13", "name": "adx_14", "category": "talib",
        "expression": "_talib_adx_14",
        "depends_on": ["_talib_adx_14"],
    },
    {
        "id": "T14", "name": "cci_14", "category": "talib",
        "expression": "_talib_cci_14",
        "depends_on": ["_talib_cci_14"],
    },
    {
        "id": "T15", "name": "willr_14", "category": "talib",
        "expression": "_talib_willr_14",
        "depends_on": ["_talib_willr_14"],
    },
    {
        "id": "T16", "name": "stoch_k", "category": "talib",
        "expression": "_talib_stoch_k",
        "depends_on": ["_talib_stoch_k"],
    },
    {
        "id": "T17", "name": "stoch_d", "category": "talib",
        "expression": "_talib_stoch_d",
        "depends_on": ["_talib_stoch_d"],
    },
    {
        "id": "T18", "name": "mfi_14", "category": "talib",
        "expression": "_talib_mfi_14",
        "depends_on": ["_talib_mfi_14"],
    },
    {
        "id": "T19", "name": "roc_6", "category": "talib",
        "expression": "_talib_roc_6",
        "depends_on": ["_talib_roc_6"],
    },
    {
        "id": "T20", "name": "roc_12", "category": "talib",
        "expression": "_talib_roc_12",
        "depends_on": ["_talib_roc_12"],
    },
    {
        "id": "T21", "name": "ema_12", "category": "talib",
        "expression": "_talib_ema_12",
        "depends_on": ["_talib_ema_12"],
    },
    {
        "id": "T22", "name": "ema_26", "category": "talib",
        "expression": "_talib_ema_26",
        "depends_on": ["_talib_ema_26"],
    },
    {
        "id": "T23", "name": "ema_ratio", "category": "talib",
        "expression": "_talib_ema_12 / (_talib_ema_26 + 0.00000001)",
        "depends_on": ["_talib_ema_12", "_talib_ema_26"],
    },
]
