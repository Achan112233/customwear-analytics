import os

import pytest
from sqlalchemy import text

from app.database import engine


@pytest.mark.skipif(os.getenv("REQUIRE_POSTGRES") != "1", reason="PostgreSQL CI check")
def test_ci_uses_real_postgresql():
    assert engine.dialect.name == "postgresql"
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version()")).scalar_one().startswith("PostgreSQL")
