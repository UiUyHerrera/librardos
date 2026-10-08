from datetime import time

import pytest

from reservini.hours import format_ranges, parse_ranges


def test_parses_several_blocks_in_order(app):
    with app.test_request_context():
        assert parse_ranges("15:00-19:00, 9:00 - 13:00") == [(time(9, 0), time(13, 0)), (time(15, 0), time(19, 0))]


def test_empty_text_means_closed(app):
    with app.test_request_context():
        assert parse_ranges("  ") == []


@pytest.mark.parametrize("text", ["13:00-09:00", "09:00-12:00, 11:30-14:00", "25:00-26:00", "9am-5pm"])
def test_rejects_invalid_hours(app, text):
    with app.test_request_context(), pytest.raises(ValueError):
        parse_ranges(text)


def test_formats_blocks_back_to_text():
    assert format_ranges([(time(9, 0), time(13, 0)), (time(15, 0), time(19, 30))]) == "09:00-13:00, 15:00-19:30"
