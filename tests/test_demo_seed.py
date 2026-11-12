from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from runpy import run_path
from threading import Barrier
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import func, select

from jordy import crm
from jordy.models import Booking, Customer, IdempotencyRecord, Outbox, Resource

seed = run_path(str(Path(__file__).parents[1] / "scripts/seed_demo.py"))["seed"]
ZONE = ZoneInfo("America/Mexico_City")


def test_retry_after_interrupted_seed_and_concurrent_loads(empty_database, monkeypatch):
    def interrupted(*args):
        raise RuntimeError("synthetic interruption")

    with monkeypatch.context() as patch:
        patch.setattr(crm, "create_appointment", interrupted)
        with pytest.raises(RuntimeError, match="synthetic interruption"):
            seed(empty_database, ZONE)
    with empty_database.connect() as conn:
        for model in (Customer, Booking, Resource, IdempotencyRecord, Outbox):
            assert conn.scalar(select(func.count()).select_from(model)) == 0

    barrier = Barrier(2)

    def load():
        barrier.wait(timeout=10)
        return seed(empty_database, ZONE)

    with ThreadPoolExecutor(max_workers=2) as pool:
        attempts = [pool.submit(load) for _ in range(2)]
        assert sorted(f.result(timeout=30) for f in attempts) == [False, True]
    with empty_database.connect() as conn:
        assert conn.scalar(select(func.count()).select_from(Customer)) == 4
        assert conn.scalar(select(func.count()).select_from(Booking)) == 3
        assert list(conn.scalars(select(Outbox.topic))) == ["booking"]
