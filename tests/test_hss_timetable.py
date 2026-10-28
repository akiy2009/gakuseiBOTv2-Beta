import asyncio
import sys
from types import SimpleNamespace

from cogs.normal import timetable


def test_hss_integration_is_disabled_when_not_configured(monkeypatch):
    for name in timetable._REQUIRED_ENV:
        monkeypatch.delenv(name, raising=False)

    cog = timetable.HssTimetableCog(bot=object())
    asyncio.run(cog.cog_load())

    assert cog.state == "not_configured"
    assert cog.client is None
    asyncio.run(cog.cog_unload())


def test_format_lessons_handles_empty_and_missing_values():
    assert timetable.format_lessons([]) == "この曜日には登録された授業がありません。"

    lesson = SimpleNamespace(name="数学", place="第1教室", is_event=False)
    assert timetable.format_lessons([lesson]) == "**1限** 数学 — 第1教室"


def test_hss_integration_initializes_and_closes_client(monkeypatch):
    for name, value in {
        "HSS_API_TOKEN": "test-token-not-for-logs",
        "HSS_SCHOOL_ID": "123",
        "HSS_GRADE": "2",
        "HSS_CLASS": "3",
    }.items():
        monkeypatch.setenv(name, value)

    lessons = [SimpleNamespace(name="数学", place="第1教室", is_event=False)]
    classroom = SimpleNamespace(
        timeline=SimpleNamespace(mon=SimpleNamespace(lessons=lessons))
    )
    school = SimpleNamespace(name="テスト高専", classes={2: {3: classroom}})

    class FakeClient:
        def __init__(self):
            self.token = None
            self.closed = False

        async def setup(self, token):
            self.token = token

        def get_school(self, school_id):
            assert school_id == 123
            return school

        async def close(self):
            self.closed = True

    fake_client = FakeClient()
    monkeypatch.setitem(sys.modules, "hss", SimpleNamespace(Client=lambda: fake_client))
    monkeypatch.setattr(timetable, "sys", SimpleNamespace(version_info=(3, 11)))

    cog = timetable.HssTimetableCog(bot=object())
    asyncio.run(cog.cog_load())

    assert cog.state == "ready"
    assert cog.school is school
    assert cog.classroom is classroom
    assert fake_client.token == "test-token-not-for-logs"

    asyncio.run(cog.cog_unload())
    assert fake_client.closed
