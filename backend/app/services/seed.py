from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import ConflictLog, Hall, SeatHold, Showtime


def seed_if_empty(db: Session) -> None:
    if db.scalar(select(Hall.id).limit(1)):
        return
    h1 = Hall(name="一号厅", rows=8, cols=12, aisle_cols="5,6", family_rows="4")
    h2 = Hall(name="二号厅", rows=6, cols=10, aisle_cols="4,5", family_rows="3")
    db.add_all([h1, h2])
    db.flush()
    now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    s1 = Showtime(hall_id=h1.id, film_title="星际旅人", start_at=now + timedelta(hours=2))
    s2 = Showtime(hall_id=h1.id, film_title="雾都夜曲", start_at=now + timedelta(hours=5))
    s3 = Showtime(hall_id=h2.id, film_title="山海经异", start_at=now + timedelta(hours=3))
    db.add_all([s1, s2, s3])
    db.flush()
    db.add_all(
        [
            SeatHold(showtime_id=s1.id, order_code="SB-1001", row=3, start_col=2, end_col=4, party_size=3),
            SeatHold(showtime_id=s1.id, order_code="SB-1002", row=5, start_col=7, end_col=9, party_size=3),
            SeatHold(showtime_id=s3.id, order_code="SB-1003", row=2, start_col=1, end_col=2, party_size=2),
            # 家庭排（第3排）被过道切成 1-3 / 6-10 两段；占用 6-8 后最长连续空座仅 3，
            # 4 人儿童请求失败，但非家庭排（如第1排）仍有整段空位可供普通请求。
            SeatHold(showtime_id=s3.id, order_code="SB-1004", row=3, start_col=6, end_col=8, party_size=3),
        ]
    )
    db.add_all(
        [
            ConflictLog(showtime_id=s1.id, party_size=4, reason="与既有持座重叠：第3排 2-4"),
            ConflictLog(
                showtime_id=s3.id,
                party_size=4,
                reason="家庭排内无足够连续空座（需连座 4，过道或已占座位把连续段切短）",
            ),
        ]
    )
    db.commit()
