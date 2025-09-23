class _BaseStrategy:
    def example(self):  # pragma: no cover - interface method
        raise NotImplementedError


class _SampledFromStrategy(_BaseStrategy):
    def __init__(self, values):
        self._values = list(values)

    def example(self):
        if not self._values:
            return None
        return self._values[0]


class _IntegersStrategy(_BaseStrategy):
    def __init__(self, min_value=None, max_value=None):
        self._min = 0 if min_value is None else min_value
        self._max = self._min if max_value is None else max_value

    def example(self):
        return self._min


def sampled_from(values):
    return _SampledFromStrategy(values)


def integers(min_value=None, max_value=None):
    return _IntegersStrategy(min_value=min_value, max_value=max_value)


__all__ = ['sampled_from', 'integers']
