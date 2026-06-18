# Python Conventions

## Tooling

- **Package manager**: pip with `requirements.txt`
- **Linter**: Ruff
- **Python version**: 3.12+

## Logging

Use the `logging` module, not `print()`. Configure a root logger in each script:

```python
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)
```

## Retry policy

Network calls (Binance API via CCXT) use 3 retries with exponential backoff: 1s, 2s, 4s. Log each attempt and the final outcome.

## Code style

- Ruff with default rules. No additional strictness for V1.
- Type annotations: optional in V1. Can be added later.
- Docstrings: one-line for simple functions, triple-quoted for public API.
