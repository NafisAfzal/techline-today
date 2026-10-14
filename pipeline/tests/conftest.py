from datetime import UTC, datetime

import pytest

from pipeline.fixtures import fixture_data
from pipeline.models import SourceConfig


@pytest.fixture
def now():
    return datetime(2026, 10, 3, 12, 0, tzinfo=UTC)


@pytest.fixture
def items(now):
    return fixture_data(now)


@pytest.fixture
def source():
    return SourceConfig(id="test", name="Test official", adapter="rss", source_class="primary",
                        endpoint="https://example.com/feed", allowed_hosts=["example.com"], categories=["ai"],
                        independence_group="test", terms_url="https://example.com/terms")
