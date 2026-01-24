"""Tests for wren.integrations module."""

import pytest
from wren.integrations import integrations, IntegrationInitializer
from wren.integrations.base import BaseIntegration
from wren.integrations.cron import CronIntegration
from wren.integrations.messaging import MessagingIntegration, Message
from wren.core.registry import registry


@pytest.fixture
def clean_registry():
    """Provide a clean registry for each test."""
    registry.clear()
    yield registry
    registry.clear()


class TestIntegrationManager:
    """Test IntegrationManager class."""

    def test_getattr_returns_initializer(self):
        """Accessing integration name should return initializer."""
        result = integrations.cron
        assert isinstance(result, IntegrationInitializer)

    def test_unknown_integration_raises_error(self, clean_registry):
        """Initializing unknown integration should raise ValueError."""
        with pytest.raises(ValueError, match="Unknown integration"):
            integrations.nonexistent.init()


class TestIntegrationInitializer:
    """Test IntegrationInitializer class."""

    def test_init_registers_integration(self, clean_registry):
        """init() should register integration in registry."""
        integrations.cron.init()

        metadata = clean_registry.get_metadata()
        assert "cron" in metadata["integrations"]

    def test_init_returns_integration_instance(self, clean_registry):
        """init() should return an integration instance."""
        cron = integrations.cron.init()
        assert isinstance(cron, CronIntegration)

    def test_init_passes_config(self, clean_registry):
        """init() should pass config to integration."""
        messaging = integrations.messaging.init(default_channel="#test")
        assert messaging.config["default_channel"] == "#test"


class TestBaseIntegration:
    """Test BaseIntegration class behavior."""

    def test_lazy_connection(self, clean_registry):
        """Integration should not connect until method called."""
        messaging = integrations.messaging.init()

        assert not messaging.is_connected

    def test_ensure_connected_connects(self, clean_registry):
        """_ensure_connected should establish connection."""
        messaging = integrations.messaging.init()
        messaging._ensure_connected()

        assert messaging.is_connected

    def test_disconnect_resets_state(self, clean_registry):
        """disconnect() should reset connection state."""
        messaging = integrations.messaging.init()
        messaging._ensure_connected()
        messaging.disconnect()

        assert not messaging.is_connected


class TestCronIntegration:
    """Test CronIntegration class."""

    def test_manual_schedule_registration(self, clean_registry):
        """schedule() should register task in registry."""
        cron = integrations.cron.init()

        def my_task():
            pass

        cron.schedule("*/5 * * * *", my_task, "UTC")

        metadata = clean_registry.get_metadata()
        schedules = [t for t in metadata["triggers"] if t["type"] == "schedule" and t["func"] == "my_task"]
        assert len(schedules) == 1
        assert schedules[0]["config"]["cron"] == "*/5 * * * *"

    def test_get_schedules(self, clean_registry):
        """get_schedules() should return registered schedules."""
        cron = integrations.cron.init()
        cron.schedule("0 9 * * *", lambda: None)

        schedules = cron.get_schedules()
        assert len(schedules) >= 1


class TestMessagingIntegration:
    """Test MessagingIntegration class."""

    def test_default_channel(self, clean_registry):
        """default_channel should use config value."""
        messaging = integrations.messaging.init(default_channel="#alerts")
        assert messaging.default_channel == "#alerts"

    def test_default_channel_fallback(self, clean_registry):
        """default_channel should fallback to #general."""
        messaging = integrations.messaging.init()
        assert messaging.default_channel == "#general"

    def test_send_message_connects_lazily(self, clean_registry):
        """send_message should connect on first call."""
        messaging = integrations.messaging.init()
        assert not messaging.is_connected

        messaging.send_message("#test", "Hello")
        assert messaging.is_connected

    def test_send_message_returns_response(self, clean_registry):
        """send_message should return API-like response."""
        messaging = integrations.messaging.init()
        result = messaging.send_message("#test", "Hello")

        assert result["ok"] is True
        assert result["channel"] == "#test"
        assert result["message"]["text"] == "Hello"
        assert "ts" in result

    def test_post_uses_default_channel(self, clean_registry):
        """post() should send to default channel."""
        messaging = integrations.messaging.init(default_channel="#alerts")
        result = messaging.post("Alert!")

        assert result["channel"] == "#alerts"

    def test_message_tracking(self, clean_registry):
        """Sent messages should be trackable."""
        messaging = integrations.messaging.init()
        messaging.send_message("#ch1", "First")
        messaging.send_message("#ch2", "Second")

        messages = messaging.get_sent_messages()
        assert len(messages) == 2
        assert messages[0].channel == "#ch1"
        assert messages[0].text == "First"
        assert messages[1].channel == "#ch2"

    def test_clear_messages(self, clean_registry):
        """clear_messages should reset message history."""
        messaging = integrations.messaging.init()
        messaging.post("Test")
        messaging.clear_messages()

        messages = messaging.get_sent_messages()
        assert len(messages) == 0


class TestIntegrationUsagePattern:
    """Test the full usage pattern as documented."""

    def test_module_level_init_pattern(self, clean_registry):
        """Test the typical module-level initialization pattern."""
        # Simulating top of a user's script
        cron = integrations.cron.init()
        messaging = integrations.messaging.init(default_channel="#alerts")

        # Verify registrations happened
        metadata = clean_registry.get_metadata()
        assert "cron" in metadata["integrations"]
        assert "messaging" in metadata["integrations"]

    def test_full_workflow(self, clean_registry):
        """Test complete workflow: init, decorate, use."""
        import wren

        # Module level setup
        messaging = wren.integrations.messaging.init(default_channel="#dev")

        @wren.on_schedule("0 9 * * *")
        def daily_report():
            messaging.post("Daily report generated")

        # Check metadata is correct
        metadata = wren.get_metadata()
        assert "messaging" in metadata["integrations"]
        schedules = [t for t in metadata["triggers"] if t["type"] == "schedule"]
        assert len(schedules) == 1
        assert schedules[0]["func"] == "daily_report"

        # Simulate running the function
        daily_report()

        # Verify message was sent
        messages = messaging.get_sent_messages()
        assert len(messages) == 1
        assert messages[0].text == "Daily report generated"
