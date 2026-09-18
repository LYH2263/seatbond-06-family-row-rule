from app.services.bond_engine import (
    HoldSpan,
    SeatCell,
    conflicts_with,
    contiguous_runs,
    find_bond_across_rows,
    find_contiguous_block,
    free_seat_count,
)


def _row(cols, aisles=()):
    return [SeatCell(row=1, col=c, is_aisle=(c in aisles)) for c in cols]


def test_aisle_breaks_runs():
    cells = _row(range(1, 11), aisles={5, 6})
    assert contiguous_runs(cells) == [(1, 4), (7, 10)]


def test_find_contiguous_skips_occupied():
    cells = _row(range(1, 9))
    holds = [HoldSpan(row=1, start_col=2, end_col=3)]
    block = find_contiguous_block(cells, holds, 1, 3)
    assert block == HoldSpan(row=1, start_col=4, end_col=6)


def test_party_too_large_returns_none():
    cells = _row(range(1, 5), aisles={3})
    assert find_contiguous_block(cells, [], 1, 3) is None


def test_conflict_overlap():
    existing = [HoldSpan(row=2, start_col=4, end_col=6)]
    cand = HoldSpan(row=2, start_col=6, end_col=8)
    assert conflicts_with(existing, cand) == existing


def test_find_across_rows():
    seats = {
        1: _row(range(1, 5)),
        2: [SeatCell(row=2, col=c) for c in range(1, 9)],
    }
    holds = [HoldSpan(row=1, start_col=1, end_col=4)]
    block = find_bond_across_rows(seats, holds, 4)
    assert block == HoldSpan(row=2, start_col=1, end_col=4)


def _grid(rows, cols, aisles=()):
    return {
        r: [SeatCell(row=r, col=c, is_aisle=(c in aisles)) for c in range(1, cols + 1)]
        for r in range(1, rows + 1)
    }


def test_allowed_rows_restricts_child_to_family():
    seats = _grid(3, 6)
    # Rows 1 and 2 are wide open; only allowed row 3 is searched.
    block = find_bond_across_rows(seats, [], 4, allowed_rows={3})
    assert block == HoldSpan(row=3, start_col=1, end_col=4)


def test_child_does_not_spill_out_of_family_rows():
    seats = _grid(3, 6)
    # Family row 1 fully taken; rows 2-3 free but must not be used.
    holds = [HoldSpan(row=1, start_col=1, end_col=6)]
    assert find_bond_across_rows(seats, holds, 2, allowed_rows={1}) is None


def test_normal_party_searches_non_family_rows():
    seats = _grid(3, 6)
    # Family row 1 free; normal rows 2-3. Search must skip row 1 and land row 2.
    block = find_bond_across_rows(seats, [], 4, allowed_rows={2, 3})
    assert block == HoldSpan(row=2, start_col=1, end_col=4)


def test_free_seat_count_ignores_aisles_and_holds():
    seats = _grid(2, 6, aisles={4})
    holds = [HoldSpan(row=1, start_col=1, end_col=2)]
    # Row 1: 5 non-aisle seats minus 2 held = 3 free; row 2: 5 free.
    assert free_seat_count(seats, holds, {1, 2}) == 8
    assert free_seat_count(seats, holds, {1}) == 3


def test_aisle_and_holds_shrink_family_run():
    # Family row split by aisle into 1-3 and 6-10; occupying 6-8 leaves 9-10.
    seats = {1: [SeatCell(row=1, col=c, is_aisle=(c in {4, 5})) for c in range(1, 11)]}
    holds = [HoldSpan(row=1, start_col=6, end_col=8)]
    # Party of 4 fits nowhere (runs are 1-3 and 9-10), even though 5 seats free.
    assert find_contiguous_block(seats[1], holds, 1, 4) is None
    assert free_seat_count(seats, holds, {1}) == 5
