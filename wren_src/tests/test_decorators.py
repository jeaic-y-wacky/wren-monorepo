"""Tests for wren.triggers module."""

import pytest
from wren.triggers import on_schedule, on_email
from wren.core.registry import registry


@pytest.fixture
def clean_registry():
    """Provide a clean registry for each test."""
    registry.clear()
    yield registry
    registry.clear()


def get_triggers_of_type(metadata, trigger_type):
    """Helper to filter triggers by type."""
    return [t for t in metadata["triggers"] if t["type"] == trigger_type]


class TestOnScheduleDecorator:
    """Test @on_schedule decorator."""

    def test_registers_schedule(self, clean_registry):
        """Decorator should register schedule in registry."""
        @on_schedule("0 9 * * *")
        def daily_task():
            pass

        metadata = clean_registry.get_metadata()
        schedules = get_triggers_of_type(metadata, "schedule")
        assert len(schedules) == 1
        assert schedules[0]["config"]["cron"] == "0 9 * * *"
        assert schedules[0]["func"] == "daily_task"

    def test_registers_schedule_with_timezone(self, clean_registry):
        """Decorator should record timezone when provided."""
        @on_schedule("0 9 * * *", timezone="America/New_York")
        def ny_task():
            pass

        metadata = clean_registry.get_metadata()
        schedules = get_triggers_of_type(metadata, "schedule")
        assert schedules[0]["config"]["timezone"] == "America/New_York"

    def test_returns_original_function(self, clean_registry):
        """Decorator should return the original function unchanged."""
        def original():
            return "test"

        decorated = on_schedule("0 9 * * *")(original)

        assert decorated is original
        assert decorated() == "test"

    def test_preserves_function_attributes(self, clean_registry):
        """Decorator should preserve function name and docstring."""
        @on_schedule("0 9 * * *")
        def documented_task():
            """This is a documented task."""
            pass

        assert documented_task.__name__ == "documented_task"
        assert documented_task.__doc__ == "This is a documented task."

    def test_multiple_schedules(self, clean_registry):
        """Multiple decorators should register multiple schedules."""
        @on_schedule("0 9 * * *")
        def task1():
            pass

        @on_schedule("0 18 * * *")
        def task2():
            pass

        metadata = clean_registry.get_metadata()
        schedules = get_triggers_of_type(metadata, "schedule")
        assert len(schedules) == 2


class TestOnEmailDecorator:
    """Test @on_email decorator."""

    def test_registers_email_trigger(self, clean_registry):
        """Decorator should register email trigger in registry."""
        @on_email(filter={"subject": "urgent"})
        def handle_urgent():
            pass

        metadata = clean_registry.get_metadata()
        emails = get_triggers_of_type(metadata, "email")
        assert len(emails) == 1
        assert emails[0]["config"]["filter"] == {"subject": "urgent"}
        assert emails[0]["func"] == "handle_urgent"

    def test_registers_with_kwargs(self, clean_registry):
        """Decorator should accept filter as kwargs."""
        @on_email(subject="invoice", from_addr="*@vendor.com")
        def handle_invoice():
            pass

        metadata = clean_registry.get_metadata()
        emails = get_triggers_of_type(metadata, "email")
        expected_filter = {"subject": "invoice", "from_addr": "*@vendor.com"}
        assert emails[0]["config"]["filter"] == expected_filter

    def test_registers_with_empty_filter(self, clean_registry):
        """Decorator with no filter should register empty dict."""
        @on_email()
        def handle_all():
            pass

        metadata = clean_registry.get_metadata()
        emails = get_triggers_of_type(metadata, "email")
        assert emails[0]["config"]["filter"] == {}

    def test_returns_original_function(self, clean_registry):
        """Decorator should return the original function unchanged."""
        def original(email):
            return email["subject"]

        decorated = on_email(subject="test")(original)

        assert decorated is original
        assert decorated({"subject": "hello"}) == "hello"

    def test_combined_filter_and_kwargs(self, clean_registry):
        """Filter dict and kwargs should be merged."""
        @on_email(filter={"subject": "test"}, from_addr="*@example.com")
        def combined_filter():
            pass

        metadata = clean_registry.get_metadata()
        emails = get_triggers_of_type(metadata, "email")
        expected = {"subject": "test", "from_addr": "*@example.com"}
        assert emails[0]["config"]["filter"] == expected


class TestDecoratorInteraction:
    """Test decorators working together."""

    def test_multiple_decorators_on_same_function(self, clean_registry):
        """A function can have both schedule and email decorators."""
        @on_schedule("0 9 * * *")
        @on_email(subject="manual-trigger")
        def dual_trigger():
            pass

        metadata = clean_registry.get_metadata()
        schedules = get_triggers_of_type(metadata, "schedule")
        emails = get_triggers_of_type(metadata, "email")
        assert len(schedules) == 1
        assert len(emails) == 1

    def test_import_style_usage(self, clean_registry):
        """Test wren.on_schedule style imports work."""
        import wren

        @wren.on_schedule("0 12 * * *")
        def lunch_reminder():
            pass

        metadata = wren.get_metadata()
        schedules = get_triggers_of_type(metadata, "schedule")
        assert len(schedules) == 1
        assert schedules[0]["func"] == "lunch_reminder"
