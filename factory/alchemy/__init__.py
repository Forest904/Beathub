from types import SimpleNamespace

from .. import FactoryMeta, Sequence, LazyAttribute, LazyFunction, SubFactory, _evaluate_declarations


class SQLAlchemyModelFactory(metaclass=FactoryMeta):
    class Meta:
        abstract = True
        sqlalchemy_session = None
        sqlalchemy_session_persistence = None

    @classmethod
    def build(cls, **kwargs):
        values = _evaluate_declarations(cls, dict(kwargs))
        model = getattr(cls._meta, 'model', None)
        if model is None:
            raise RuntimeError('Factory Meta.model must be defined')
        return model(**values)

    @classmethod
    def create(cls, **kwargs):
        obj = cls.build(**kwargs)
        session = getattr(cls._meta, 'sqlalchemy_session', None)
        if session is None:
            raise RuntimeError('SQLAlchemy session not configured for factory')
        model = getattr(cls._meta, 'model', None)
        if model is not None and hasattr(obj, 'spotify_id'):
            existing = session.query(model).filter_by(spotify_id=obj.spotify_id).first()
            if existing is not None:
                return existing
        session.add(obj)
        persistence = getattr(cls._meta, 'sqlalchemy_session_persistence', None)
        if persistence == 'flush':
            try:
                session.flush()
            except Exception:
                session.rollback()
                raise
        return obj


__all__ = ['SQLAlchemyModelFactory']
