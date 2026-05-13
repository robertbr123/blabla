from datetime import date

from ondeline_api.workers.partition_jobs import _next_n_month_windows


def test_next_n_month_windows_handles_year_boundary() -> None:
    windows = _next_n_month_windows(date(2026, 11, 14), n=3)
    assert [w[0] for w in windows] == [
        "mensagens_2026_11",
        "mensagens_2026_12",
        "mensagens_2027_01",
    ]
    assert windows[0][1:] == (date(2026, 11, 1), date(2026, 12, 1))
    assert windows[1][1:] == (date(2026, 12, 1), date(2027, 1, 1))
    assert windows[2][1:] == (date(2027, 1, 1), date(2027, 2, 1))


def test_next_n_month_windows_uses_first_of_month() -> None:
    windows = _next_n_month_windows(date(2026, 7, 31), n=1)
    assert windows[0] == ("mensagens_2026_07", date(2026, 7, 1), date(2026, 8, 1))
