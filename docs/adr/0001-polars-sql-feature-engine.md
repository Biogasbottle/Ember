# ADR 0001: Polars SQL for Feature Expression Evaluation

Feature expressions are stored as SQL strings in the registry and evaluated by Polars' SQL context.

## Context

Features are declared in `registry.py` as structured entries. Each expression must be evaluated against the raw data to produce a column. Three approaches were considered: SQL eval, Python lambda, and string-based `eval()`.

## Decision

Use **Polars SQL** (`pl.SQLContext`). Registry entries contain valid SQL SELECT expressions. `build_features.py` wraps the raw DataFrame in a SQL context and executes each expression.

## Rejected options

- **Python lambda**: Registry entries would contain `lambda df: df["close"] / df["close"].shift(1) - 1`. Rejected because it couples registry to Python runtime, makes the registry unreadable as documentation, and prevents static analysis.
- **`eval()` with Polars namespace**: Map column names to `pl.col()` and eval the string. Rejected because it requires a custom expression mini-parser and is error-prone with complex window functions.

## Consequences

- Positive: Registry is pure declarative data. Complex window functions (rolling mean/std, shift) are native SQL. High readability.
- Negative: SQL shift syntax (`LAG` / `LEAD`) is more verbose than Polars' `.shift()`. Type-checking is deferred to runtime.
- Follow-up: Consider migrating to Polars' native expression API if SQL overhead becomes a bottleneck at scale.
