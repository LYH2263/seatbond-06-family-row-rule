from datetime import datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.router import api_router
from app.database import Base, get_db
from app.models.models import Hall, SeatHold, Showtime


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(bind=engine, autoflush=False)
    Base.metadata.create_all(bind=engine)

    app = FastAPI()
    app.include_router(api_router, prefix="/api")

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    seed = TestingSession()
    # 6 rows x 10 cols, aisles at 4-5 -> segments 1-3 (len 3) and 6-10 (len 5).
    # Row 3 is the family row.
    hall = Hall(name="家庭测试厅", rows=6, cols=10, aisle_cols="4,5", family_rows="3")
    seed.add(hall)
    seed.flush()
    st = Showtime(
        hall_id=hall.id,
        film_title="亲子场",
        start_at=datetime(2026, 9, 18, 10, 0, 0) + timedelta(hours=1),
    )
    seed.add(st)
    seed.commit()
    hall_id, showtime_id = hall.id, st.id
    seed.close()

    with TestClient(app) as c:
        c.Session = TestingSession
        c.hall_id = hall_id
        c.showtime_id = showtime_id
        yield c


def _hold(client, party_size, **kw):
    body = {"showtime_id": client.showtime_id, "party_size": party_size}
    body.update(kw)
    return client.post("/api/holds", json=body)


def occupy(client, row, start, end, is_child=False):
    """Place an existing hold directly (bypasses search) to pre-fill seats."""
    s = client.Session()
    s.add(
        SeatHold(
            showtime_id=client.showtime_id,
            order_code=f"OCC-{row}-{start}",
            row=row,
            start_col=start,
            end_col=end,
            party_size=end - start + 1,
            is_child=is_child,
        )
    )
    s.commit()
    s.close()


def test_child_lock_placed_in_family_row(client):
    r = _hold(client, 3, is_child=True)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["row"] == 3
    assert data["start_col"] == 1  # leftmost segment 1-3
    assert data["is_child"] is True


def test_normal_lock_avoids_family_row(client):
    # Even with the family row empty, an ordinary party must not take it.
    r = _hold(client, 2, is_child=False)
    assert r.status_code == 200, r.text
    assert r.json()["row"] != 3
    assert r.json()["is_child"] is False


def test_child_segment_too_short_fails_but_normal_succeeds(client):
    # Occupy 6-8 in family row 3: free runs are col 3? no — 1-3 all free (len 3),
    # and 9-10 (len 2). Longest family run = 3, so a party of 4 cannot fit.
    occupy(client, 3, 6, 8)
    r_child = _hold(client, 4, is_child=True)
    assert r_child.status_code == 409
    detail = r_child.json()["detail"]
    # Must explain it as a family-row shortfall, not fall back to a normal row.
    assert "家庭排" in detail
    assert "连续" in detail

    # Non-family rows still have room: a normal party of 4 fits the 6-10 run.
    r_normal = _hold(client, 4, is_child=False)
    assert r_normal.status_code == 200, r_normal.text
    assert r_normal.json()["row"] != 3
    assert r_normal.json()["start_col"] == 6


def test_child_fails_when_family_completely_full(client):
    # Fill every family-row seat: aisle splits into 1-3 and 6-10.
    occupy(client, 3, 1, 3)
    occupy(client, 3, 6, 10)
    r = _hold(client, 2, is_child=True)
    assert r.status_code == 409
    detail = r.json()["detail"]
    assert "家庭排" in detail
    assert "空座不足" in detail
    assert "仅剩 0 座" in detail


def test_aisle_overlays_occupancy_failure_branch(client):
    # Aisle + occupancy together shrink every family run below party size:
    # occupy 1-2 (leaves col 3, run len 1) and 6-8 (leaves 9-10, run len 2).
    occupy(client, 3, 1, 2)
    occupy(client, 3, 6, 8)
    r = _hold(client, 3, is_child=True)
    assert r.status_code == 409
    detail = r.json()["detail"]
    assert "家庭排" in detail
    assert "连续" in detail  # 3 free seats exist but none are contiguous


def test_child_with_no_family_rows_reports_clear_reason(client):
    client.put(f"/api/halls/{client.hall_id}/family-rows", json={"family_rows": []})
    r = _hold(client, 2, is_child=True)
    assert r.status_code == 409
    assert "未设置家庭排" in r.json()["detail"]


def test_conflict_log_persists_family_reason(client):
    occupy(client, 3, 1, 3)
    occupy(client, 3, 6, 10)
    assert _hold(client, 4, is_child=True).status_code == 409
    conflicts = client.get("/api/conflicts").json()
    assert any("家庭排" in c["reason"] for c in conflicts)


def test_family_rows_read_write(client):
    r = client.put(f"/api/halls/{client.hall_id}/family-rows", json={"family_rows": [2, 5, 2]})
    assert r.status_code == 200
    assert r.json()["family_rows"] == [2, 5]  # de-duplicated + sorted

    # Out-of-range rows are dropped.
    r = client.put(f"/api/halls/{client.hall_id}/family-rows", json={"family_rows": [1, 99, 0]})
    assert r.json()["family_rows"] == [1]

    assert client.get("/api/halls").json()[0]["family_rows"] == [1]


def test_update_family_rows_unknown_hall(client):
    r = client.put("/api/halls/9999/family-rows", json={"family_rows": [1]})
    assert r.status_code == 404


def test_seatmap_flags_family_rows(client):
    r = client.get(f"/api/seatmap/{client.showtime_id}")
    assert r.status_code == 200
    data = r.json()
    assert data["family_rows"] == [3]
    assert {c["row"] for c in data["cells"] if c["is_family"]} == {3}
    assert all(c["is_family"] for c in data["cells"] if c["row"] == 3)
    assert not any(c["is_family"] for c in data["cells"] if c["row"] != 3)


def test_preferred_non_family_row_ignored_for_child(client):
    # A child preferring a non-family row must not be seated there.
    r = _hold(client, 2, is_child=True, preferred_row=1)
    assert r.status_code == 200
    assert r.json()["row"] == 3
