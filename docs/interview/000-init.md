# interview.md

## Project

Crypto Alpha Research Platform

目标：

构建一个以 Crypto Perpetual Futures 为研究对象的 Alpha Research Pipeline。

重点研究：

- Price
- Open Interest (OI)
- Funding Rate
- Liquidation

目标不是开发指标策略，而是构建专业量化研究流水线：

Raw Data
→ Feature Engineering
→ Label Generation
→ Machine Learning
→ Alpha Discovery
→ Backtest
→ Live Trading

---

# Philosophy

本项目采用 Research-First 架构。

不以策略为中心：

```python
if rsi < 30:
    buy()
```

而以 Alpha 为中心：

```text
Feature
↓
Model
↓
Expected Return
↓
Portfolio
↓
Execution
```

核心目标：

预测未来收益率。

---

# Tech Stack

## Data

- Python 3.12+
- Polars

原因：

- 比 Pandas 更快
- 更适合大型时间序列
- Lazy Execution
- Arrow Native

---

## ML

- LightGBM

第一阶段不考虑：

- LSTM
- Transformer
- LLM Agent

原因：

金融时序数据量有限。

LightGBM 是最强基线。

---

## Backtest

- VectorBT

用途：

- Alpha Validation
- Portfolio Simulation

不是执行引擎。

---

## Execution

V1:

- Freqtrade

用途：

- Dry Run
- Live Trading

---

# Data Schema

统一周期：

4H

主表：

```text
timestamp

open
high
low
close
volume

oi

funding

long_liq
short_liq
```

数据源暂不限定。

要求：

所有字段严格按 timestamp 对齐。

---

# Research Objective

预测：

future_return_24h

定义：

```python
future_return_24h =
close.shift(-6) / close - 1
```

原因：

4H × 6 = 24H

未来可扩展：

- 12H
- 24H
- 48H
- 72H

---

# Phase 1 Goal

先不要构建完整 Feature Registry。

目标：

完成：

features_v1.parquet

并训练第一版 LightGBM。

---

# Directory Structure

```text
crypto-alpha/

data/
    raw/

feature_lab/
    registry.py
    build_features.py

research/
    train_lightgbm.py

models/

reports/
```

---

# Feature Registry V1

## Price

### P01

ret_1

```python
close / close.shift(1) - 1
```

### P02

ret_3

```python
close / close.shift(3) - 1
```

### P03

ret_6

```python
close / close.shift(6) - 1
```

---

## OI

### O01

oi_ret_1

```python
oi / oi.shift(1) - 1
```

---

## Funding

### F01

funding_z

```python
(
 funding
 -
 rolling_mean(180)
)
/
rolling_std(180)
```

180 = 30 days

---

## Liquidation

### L01

liq_total

```python
long_liq + short_liq
```

### L02

liq_shock

```python
liq_total
/
rolling_mean(liq_total, 180)
```

---

# Label

future_return_24h

```python
close.shift(-6)
/
close
-
1
```

---

# Output Dataset

目标输出：

features_v1.parquet

列：

```text
timestamp

ret_1
ret_3
ret_6

oi_ret_1

funding_z

liq_total

liq_shock

future_return_24h
```

---

# Build Feature Task

实现：

feature_lab/build_features.py

职责：

1. 读取 raw parquet

2. 计算 Feature

3. 生成 Label

4. drop_nulls()

5. 保存：

```text
data/features_v1.parquet
```

---

# LightGBM V1

目标：

回归

预测：

future_return_24h

---

Input

```python
X = [
    ret_1,
    ret_3,
    ret_6,
    oi_ret_1,
    funding_z,
    liq_shock
]
```

Output

```python
pred_return
```

示例：

```python
0.021
```

解释：

未来24H预测收益率 +2.1%

---

# Train Task

实现：

research/train_lightgbm.py

要求：

1. 读取 features_v1.parquet

2. Time Series Split

禁止随机切分

3. Train LightGBM Regressor

4. 输出：

```text
models/lgbm_v1.pkl
```

5. 输出指标：

- RMSE
- MAE
- Correlation(pred, y)

---

# Phase 2 Feature Registry

完成 V1 后扩展到完整 Registry。

分类：

## Price

10

## OI

15

## Funding

10

## Liquidation

10

## Price × OI

10

## Funding × OI

10

## Liq × OI × Funding

10

总计：

75 Features

---

# Validation Roadmap

V1

```text
6 Features
↓
LightGBM
```

V2

```text
20 Features
↓
LightGBM
```

V3

```text
75 Features
↓
LightGBM
↓
SHAP
```

V4

```text
Walk Forward Validation
```

V5

```text
VectorBT Portfolio Backtest
```

V6

```text
Freqtrade Dry Run
```

---

# Important Rules

禁止：

- 随机 Train/Test Split
- 数据泄露
- 使用未来数据构造 Feature
- 使用未来数据计算 Rolling Statistics

所有 Feature 必须只依赖：

```text
t
及以前
```

Label 才允许引用：

```text
t + n
```

---

# Success Criteria

Phase 1 完成标准：

成功生成：

```text
data/features_v1.parquet
```

成功训练：

```text
models/lgbm_v1.pkl
```

并输出：

```text
Prediction
Actual Return
Correlation
```

至此完成第一条 Alpha Research Pipeline。
