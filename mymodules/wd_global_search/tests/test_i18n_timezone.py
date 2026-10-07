from datetime import datetime
from unittest import TestCase

from ..services.i18n import format_datetime, translate, week_start


class TestI18nTimezone(TestCase):
    def test_translation_falls_back_to_english(self):
        labels = {"en_US": "Search", "zh_CN": "搜索"}
        self.assertEqual(translate(labels, "zh_CN"), "搜索")
        self.assertEqual(translate(labels, "fr_FR"), "Search")

    def test_datetime_uses_user_timezone(self):
        value = datetime(2026, 10, 3, 23, 30)
        self.assertTrue(format_datetime(value, "Asia/Shanghai").startswith("2026-10-04T07:30"))
        self.assertTrue(format_datetime(value, "UTC").startswith("2026-10-03T23:30"))

    def test_week_start_follows_language(self):
        self.assertEqual(week_start("en_US"), 6)
        self.assertEqual(week_start("zh_CN"), 0)
