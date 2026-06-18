# ADR 0002: Fixed Time Series Split for V1

V1 uses a fixed 60/20/20 train/val/test split. Walk-Forward Validation is deferred to V4.

## Context

Time series data requires temporally ordered splits. Two approaches: a single fixed split (fast, simple) or Walk-Forward (rolling windows, produces multiple test folds for statistical robustness).

## Decision

Use **fixed 60/20/20 split** for V1. The earliest 60% of data is training, the next 20% is validation (for early stopping), and the final 20% is the test set.

## Rejected options

- **Walk-Forward Validation**: Produces multiple out-of-sample folds and reduces variance from a single test period. Rejected for V1 because it adds complexity and runtime. Will be reintroduced in V4 after the basic pipeline is proven.
- **80/20 without validation set**: Rejected because early stopping requires a hold-out validation set to detect overfitting.

## Consequences

- Positive: Simple to implement and reason about. One training run, one test evaluation.
- Negative: Performance metrics are sensitive to the chosen test window. A single test period may not be representative.
- Follow-up: V4 will reintroduce Walk-Forward with expanding or rolling windows for robust validation.
