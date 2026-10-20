import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

sys.path.insert(0, "backend")
import data


class BeijingClock:
    value = datetime(2026, 10, 19, 14, 59)

    @classmethod
    def now(cls, tz=None):
        assert tz is not None
        assert getattr(tz, "key", None) == "Asia/Shanghai"
        return cls.value.replace(tzinfo=tz)


@pytest.fixture
def calendar_call(monkeypatch):
    calls = []

    def fake_call(method, **kwargs):
        calls.append((method, kwargs))
        return pd.DataFrame({"cal_date": ["20261016", "20261019"]})

    monkeypatch.setattr(data, "pro", object())
    monkeypatch.setattr(data, "_call", fake_call)
    monkeypatch.setattr(data, "datetime", BeijingClock)
    return calls


def test_calendar_uses_beijing_date_when_host_is_atlantic(calendar_call):
    calls = calendar_call
    result = data._calendar(limit=120)
    assert result == ["20261016", "20261019"]
    assert calls[0][1]["end_date"] == "20261019"


@pytest.mark.parametrize("clock", [
    datetime(2026, 10, 19, 14, 59),
    datetime(2026, 10, 19, 15, 1),
])
def test_calendar_before_and_after_close_keep_china_date(monkeypatch, clock):
    class Clock:
        @classmethod
        def now(cls, tz=None):
            assert getattr(tz, "key", None) == "Asia/Shanghai"
            return clock.replace(tzinfo=tz)

    captured = {}

    def fake_call(method, **kwargs):
        captured.update(kwargs)
        return pd.DataFrame({"cal_date": ["20261019"]})

    monkeypatch.setattr(data, "pro", object())
    monkeypatch.setattr(data, "_call", fake_call)
    monkeypatch.setattr(data, "datetime", Clock)
    assert data._calendar() == ["20261019"]
    assert captured["end_date"] == "20261019"


def test_calendar_weekend_uses_calendar_rows_without_inventing_dates(monkeypatch):
    class Clock:
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 10, 18, 12, 0, tzinfo=tz)

    monkeypatch.setattr(data, "pro", object())
    monkeypatch.setattr(data, "datetime", Clock)
    monkeypatch.setattr(data, "_call", lambda method, **kwargs: pd.DataFrame(
        {"cal_date": ["20261016", "20261015"]}
    ))
    assert data._calendar(limit=120) == ["20261015", "20261016"]


def test_calendar_limit_and_sort_are_backward_compatible(monkeypatch):
    class Clock:
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 10, 19, 12, 0, tzinfo=tz)

    monkeypatch.setattr(data, "pro", object())
    monkeypatch.setattr(data, "datetime", Clock)
    monkeypatch.setattr(data, "_call", lambda method, **kwargs: pd.DataFrame(
        {"cal_date": ["20261018", "20261016", "20261017"]}
    ))
    assert data._calendar(limit=2) == ["20261017", "20261018"]
