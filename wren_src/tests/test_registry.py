"""Tests for wren.core.registry module."""

import pytest

from wren.core.registry import get_metadata, registry


@pytest.fixture
def clean_registry():
    """Provide a clean registry for each test."""
    registry.clear()
    yield registry
    registry.clear()


class TestWrenRegistry:
    """Test WrenRegistry class."""

    def test_register_integration(self, clean_registry):
        """Integration registration should add to list."""
        clean_registry.register_integration("gmail")
        clean_registry.register_integration("slack")

        metadata = clean_registry.get_metadata()
        assert metadata["integrations"] == ["gmail", "slack"]

    def test_register_integration_deduplication(self, clean_registry):
        """Same integration should not be registered twice."""
        clean_registry.register_integration("gmail")
        clean_registry.register_integration("gmail")

        metadata = clean_registry.get_metadata()
        assert metadata["integrations"] == ["gmail"]

    def test_register_trigger_schedule(self, clean_registry):
        """Trigger registration should record type, config, and function."""

        def my_job():
            pass

        config = {"cron": "0 9 * * *", "timezone": "UTC"}
        clean_registry.register_trigger("schedule", config, my_job)

        metadata = clean_registry.get_metadata()
        assert len(metadata["triggers"]) == 1
        assert metadata["schedules"] == [{"cron": "0 9 * * *", "func_name": "my_job"}]
        assert metadata["triggers"][0]["type"] == "schedule"
        assert metadata["triggers"][0]["func"] == "my_job"
        assert metadata["triggers"][0]["config"]["cron"] == "0 9 * * *"
        assert metadata["triggers"][0]["config"]["timezone"] == "UTC"

    def test_register_trigger_email(self, clean_registry):
        """Email trigger registration should record filter in config."""

        def handle_email():
            pass

        filter_config = {"subject": "urgent", "from_addr": "*@company.com"}
        config = {"filter": filter_config}
        clean_registry.register_trigger("email", config, handle_email)

        metadata = clean_registry.get_metadata()
        assert len(metadata["triggers"]) == 1
        assert metadata["triggers"][0]["type"] == "email"
        assert metadata["triggers"][0]["func"] == "handle_email"
        assert metadata["triggers"][0]["config"]["filter"] == filter_config

    def test_register_trigger_custom_type(self, clean_registry):
        """Custom trigger types should be supported."""

        def webhook_handler():
            pass

        config = {"url": "/api/webhook", "method": "POST"}
        clean_registry.register_trigger("webhook", config, webhook_handler)

        metadata = clean_registry.get_metadata()
        assert metadata["triggers"][0]["type"] == "webhook"
        assert metadata["triggers"][0]["config"]["url"] == "/api/webhook"

    def test_get_triggers_by_type(self, clean_registry):
        """get_triggers_by_type should filter triggers."""

        def schedule_job():
            pass

        def email_handler():
            pass

        clean_registry.register_trigger("schedule", {"cron": "0 9 * * *"}, schedule_job)
        clean_registry.register_trigger("email", {"filter": {}}, email_handler)

        schedules = clean_registry.get_triggers_by_type("schedule")
        assert len(schedules) == 1
        assert schedules[0].func_name == "schedule_job"

        emails = clean_registry.get_triggers_by_type("email")
        assert len(emails) == 1
        assert emails[0].func_name == "email_handler"

    def test_get_metadata_structure(self, clean_registry):
        """Metadata should have correct structure."""
        metadata = clean_registry.get_metadata()

        assert "integrations" in metadata
        assert "triggers" in metadata
        assert isinstance(metadata["integrations"], list)
        assert isinstance(metadata["triggers"], list)

    def test_get_functions(self, clean_registry):
        """get_functions should return callable mapping."""

        def daily_job():
            return "daily"

        def email_handler():
            return "email"

        clean_registry.register_trigger("schedule", {"cron": "0 9 * * *"}, daily_job)
        clean_registry.register_trigger("email", {"filter": {}}, email_handler)

        funcs = clean_registry.get_functions()
        assert "daily_job" in funcs
        assert "email_handler" in funcs
        assert funcs["daily_job"]() == "daily"
        assert funcs["email_handler"]() == "email"

    def test_clear(self, clean_registry):
        """Clear should reset all registrations."""
        clean_registry.register_integration("test")
        clean_registry.register_trigger("schedule", {}, lambda: None)
        clean_registry.register_trigger("email", {}, lambda: None)

        clean_registry.clear()

        metadata = clean_registry.get_metadata()
        assert metadata["integrations"] == []
        assert metadata["triggers"] == []


class TestModuleLevelRegistry:
    """Test module-level registry and get_metadata function."""

    def test_global_registry_exists(self):
        """Global registry should be importable."""
        from wren import registry as wren_registry

        assert wren_registry is not None

    def test_get_metadata_function(self, clean_registry):
        """get_metadata function should return registry data."""
        clean_registry.register_integration("test")

        metadata = get_metadata()
        assert "test" in metadata["integrations"]
