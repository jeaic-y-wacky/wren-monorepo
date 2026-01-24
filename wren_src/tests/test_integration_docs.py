"""Tests for the integration documentation system."""

import pytest

from wren.integrations import (
    get_integration_docs,
    integrations,
    list_integrations,
    render_integration_docs,
)
from wren.integrations.docs import (
    AuthType,
    IntegrationDocs,
    MethodDoc,
    ParamDoc,
    render_all_docs,
)


class TestDocDataclasses:
    """Test the documentation dataclasses."""

    def test_param_doc_render_required(self):
        """ParamDoc should render required params correctly."""
        param = ParamDoc(
            name="query",
            type="str",
            description="The search query",
            required=True,
        )
        rendered = param.render_markdown()
        assert "`query`" in rendered
        assert "(str)" in rendered
        assert "The search query" in rendered
        assert "(optional)" not in rendered

    def test_param_doc_render_optional_with_default(self):
        """ParamDoc should render optional params with defaults."""
        param = ParamDoc(
            name="limit",
            type="int",
            description="Max results",
            required=False,
            default="50",
        )
        rendered = param.render_markdown()
        assert "(optional)" in rendered
        assert "default: `50`" in rendered

    def test_method_doc_render(self):
        """MethodDoc should render with params and returns."""
        method = MethodDoc(
            name="inbox",
            description="Get emails from inbox.",
            params=[
                ParamDoc("unread", "bool", "Only unread", required=False, default="False"),
            ],
            returns="list[Email]",
            example="gmail.inbox(unread=True)",
        )
        rendered = method.render_markdown()
        assert "#### `inbox()`" in rendered
        assert "Get emails from inbox." in rendered
        assert "**Parameters:**" in rendered
        assert "`unread`" in rendered
        assert "**Returns:** list[Email]" in rendered
        assert "**Example:**" in rendered
        assert "gmail.inbox(unread=True)" in rendered

    def test_integration_docs_render(self):
        """IntegrationDocs should render complete markdown."""
        docs = IntegrationDocs(
            name="test",
            description="A test integration.",
            auth_type=AuthType.API_KEY,
            init_params=[
                ParamDoc("token", "str", "Auth token", required=True),
            ],
            methods=[
                MethodDoc("do_thing", "Does a thing.", returns="None"),
            ],
            example="test = wren.integrations.test.init()",
        )
        rendered = docs.render_markdown()
        assert "### test" in rendered
        assert "A test integration." in rendered
        assert "**Requires:** API key" in rendered
        assert "**Init Parameters:**" in rendered
        assert "`token`" in rendered
        assert "**Quick Example:**" in rendered
        assert "**Methods:**" in rendered
        assert "`do_thing()`" in rendered

    def test_integration_docs_render_no_auth(self):
        """IntegrationDocs with no auth should not show Requires section."""
        docs = IntegrationDocs(
            name="test",
            description="A test integration.",
            auth_type=AuthType.NONE,
        )
        rendered = docs.render_markdown()
        assert "**Requires:**" not in rendered

    def test_integration_docs_to_dict(self):
        """IntegrationDocs.to_dict() should produce valid dict."""
        docs = IntegrationDocs(
            name="test",
            description="Test integration.",
            methods=[
                MethodDoc(
                    "method1",
                    "A method.",
                    params=[ParamDoc("arg1", "str", "An arg")],
                    returns="str",
                ),
            ],
            example="test.method1('hello')",
        )
        d = docs.to_dict()
        assert d["name"] == "test"
        assert d["description"] == "Test integration."
        assert len(d["methods"]) == 1
        assert d["methods"][0]["name"] == "method1"
        assert d["methods"][0]["params"][0]["name"] == "arg1"
        assert d["example"] == "test.method1('hello')"

    def test_render_all_docs(self):
        """render_all_docs should combine multiple integrations."""
        docs = [
            IntegrationDocs(name="a", description="Integration A."),
            IntegrationDocs(name="b", description="Integration B."),
        ]
        rendered = render_all_docs(docs)
        assert "# Wren Integrations Reference" in rendered
        assert "### a" in rendered
        assert "### b" in rendered
        assert "Integration A." in rendered
        assert "Integration B." in rendered


class TestIntegrationRegistry:
    """Test the integration docs registry."""

    def test_list_integrations_returns_all(self):
        """list_integrations should return all registered integrations."""
        available = list_integrations()
        assert isinstance(available, list)
        assert "gmail" in available
        assert "slack" in available
        assert "cron" in available
        assert "messaging" in available

    def test_list_integrations_sorted(self):
        """list_integrations should return sorted list."""
        available = list_integrations()
        assert available == sorted(available)

    def test_get_integration_docs_returns_docs(self):
        """get_integration_docs should return IntegrationDocs for known integration."""
        docs = get_integration_docs("gmail")
        assert docs is not None
        assert isinstance(docs, IntegrationDocs)
        assert docs.name == "gmail"

    def test_get_integration_docs_unknown_returns_none(self):
        """get_integration_docs should return None for unknown integration."""
        docs = get_integration_docs("nonexistent")
        assert docs is None


class TestAllIntegrationsHaveDocs:
    """Validate that all registered integrations have documentation."""

    def test_all_integrations_have_docs(self):
        """Every registered integration should have DOCS defined."""
        for name in list_integrations():
            docs = get_integration_docs(name)
            assert docs is not None, f"Integration '{name}' is missing DOCS"

    def test_all_docs_have_required_fields(self):
        """All DOCS should have name, description, and example."""
        for name in list_integrations():
            docs = get_integration_docs(name)
            assert docs.name, f"Integration '{name}' DOCS missing name"
            assert docs.description, f"Integration '{name}' DOCS missing description"
            assert docs.example, f"Integration '{name}' DOCS missing example"

    def test_all_docs_have_methods(self):
        """All DOCS should have at least one method documented."""
        for name in list_integrations():
            docs = get_integration_docs(name)
            assert len(docs.methods) > 0, f"Integration '{name}' DOCS has no methods"


class TestRenderIntegrationDocs:
    """Test the render_integration_docs function."""

    def test_render_all(self):
        """render_integration_docs() should render all docs."""
        rendered = render_integration_docs()
        assert "# Wren Integrations Reference" in rendered
        # Should include all integrations
        for name in list_integrations():
            assert f"### {name}" in rendered

    def test_render_specific(self):
        """render_integration_docs(names) should render only specified."""
        rendered = render_integration_docs(["gmail", "slack"])
        assert "### gmail" in rendered
        assert "### slack" in rendered
        # Should NOT include cron
        assert "### cron" not in rendered

    def test_render_produces_valid_markdown(self):
        """Rendered docs should be valid-looking markdown."""
        rendered = render_integration_docs()
        # Check for proper markdown structure
        assert rendered.startswith("# Wren Integrations Reference")
        assert "---" in rendered  # Has separators
        assert "```python" in rendered  # Has code blocks


class TestIntegrationManagerDocsMethods:
    """Test the IntegrationManager.list/get_docs/render_docs methods."""

    def test_manager_list(self):
        """integrations.list() should work."""
        available = integrations.list()
        assert isinstance(available, list)
        assert "gmail" in available

    def test_manager_get_docs(self):
        """integrations.get_docs() should work."""
        docs = integrations.get_docs("gmail")
        assert docs is not None
        assert docs.name == "gmail"

    def test_manager_render_docs(self):
        """integrations.render_docs() should work."""
        rendered = integrations.render_docs()
        assert "# Wren Integrations Reference" in rendered

    def test_manager_render_docs_specific(self):
        """integrations.render_docs(names) should work."""
        rendered = integrations.render_docs(["slack"])
        assert "### slack" in rendered
        assert "### gmail" not in rendered


class TestSpecificIntegrationDocs:
    """Test that specific integrations have correct documentation."""

    def test_gmail_docs(self):
        """Gmail docs should have expected methods."""
        docs = get_integration_docs("gmail")
        method_names = {m.name for m in docs.methods}
        assert "inbox" in method_names
        assert "send_email" in method_names
        assert "search" in method_names

    def test_slack_docs(self):
        """Slack docs should have expected methods."""
        docs = get_integration_docs("slack")
        method_names = {m.name for m in docs.methods}
        assert "post" in method_names
        assert "send_message" in method_names
        assert "get_messages" in method_names

    def test_messaging_docs(self):
        """Messaging docs should have expected methods."""
        docs = get_integration_docs("messaging")
        method_names = {m.name for m in docs.methods}
        assert "post" in method_names
        assert "send_message" in method_names

    def test_cron_docs(self):
        """Cron docs should have expected methods."""
        docs = get_integration_docs("cron")
        method_names = {m.name for m in docs.methods}
        assert "schedule" in method_names
        assert "get_schedules" in method_names

    def test_oauth_integrations_have_auth_type(self):
        """OAuth integrations should have auth_type=OAUTH."""
        gmail_docs = get_integration_docs("gmail")
        slack_docs = get_integration_docs("slack")
        assert gmail_docs.auth_type == AuthType.OAUTH
        assert slack_docs.auth_type == AuthType.OAUTH

    def test_no_auth_integrations(self):
        """Cron and messaging should have auth_type=NONE."""
        cron_docs = get_integration_docs("cron")
        messaging_docs = get_integration_docs("messaging")
        assert cron_docs.auth_type == AuthType.NONE
        assert messaging_docs.auth_type == AuthType.NONE
