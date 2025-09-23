from . import strategies as strategies


def given(**strategy_map):
    """Very small stub of hypothesis.given for unit tests."""

    def decorator(func):
        def wrapper(*args, **kwargs):
            generated = {name: strat.example() for name, strat in strategy_map.items()}
            return func(*args, **generated)

        wrapper.__name__ = getattr(func, '__name__', wrapper.__name__)
        wrapper.__doc__ = getattr(func, '__doc__', None)
        return wrapper

    return decorator


__all__ = ['given', 'strategies']
