"""Minimal stub of the factory_boy API used by tests."""

from types import SimpleNamespace


class Sequence:
    def __init__(self, function):
        self.function = function


class LazyAttribute:
    def __init__(self, function):
        self.function = function


class LazyFunction:
    def __init__(self, function):
        self.function = function


class SubFactory:
    def __init__(self, factory_cls):
        self.factory_cls = factory_cls


class FactoryMeta(type):
    def __new__(mcls, name, bases, attrs):
        meta = attrs.get('Meta')
        declarations = {}
        for base in reversed(bases):
            if hasattr(base, '_declarations'):
                declarations.update(base._declarations)
        for key, value in list(attrs.items()):
            if isinstance(value, (Sequence, LazyAttribute, LazyFunction, SubFactory)):
                declarations[key] = value
                attrs.pop(key)
        cls = super().__new__(mcls, name, bases, attrs)
        cls._declarations = declarations
        cls._sequence_counters = {}
        if meta is not None:
            meta_dict = {
                k: v
                for k, v in meta.__dict__.items()
                if not k.startswith('__')
            }
        else:
            meta_dict = {}
        cls._meta = SimpleNamespace(**meta_dict)
        return cls

    def __call__(cls, *args, **kwargs):
        return cls.create(*args, **kwargs)


def _evaluate_declarations(cls, overrides):
    values = {}
    for name, declaration in cls._declarations.items():
        if name in overrides:
            values[name] = overrides.pop(name)
            continue
        if isinstance(declaration, Sequence):
            counter = cls._sequence_counters.get(name, 0)
            values[name] = declaration.function(counter)
            cls._sequence_counters[name] = counter + 1
        elif isinstance(declaration, LazyFunction):
            values[name] = declaration.function()
        elif isinstance(declaration, LazyAttribute):
            placeholder = SimpleNamespace(**values)
            values[name] = declaration.function(placeholder)
        elif isinstance(declaration, SubFactory):
            values[name] = declaration.factory_cls()
    values.update(overrides)
    return values


__all__ = [
    'Sequence',
    'LazyAttribute',
    'LazyFunction',
    'SubFactory',
    'FactoryMeta',
]
