import pytest

from holdem.db import make_engine


@pytest.fixture
def engine(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'test.sqlite'}")
    yield engine
    engine.dispose()
