from unittest.mock import patch

from erp.notifications.domain.models import NotificationChannel
from erp.workflow.engine.types import NodeInput
from erp.workflow.executors.notification import NotificationExecutor


def test_notification_executor_renders_templates_and_dispatches():
    executor = NotificationExecutor()
    node_input = NodeInput(
        instance_context={"owner": "ahmed", "ticket": "TKT-1"},
        node_config={
            "channel": "inapp",
            "recipient": "{{ ctx.owner }}",
            "subject": "Ticket {{ ctx.ticket }}",
            "body": "Ticket {{ ctx.ticket }} needs attention.",
        },
    )
    with patch("erp.notifications.services.dispatch") as mock_dispatch:
        output = executor.run(node_input)
    assert output.status == "success"
    mock_dispatch.assert_called_once_with(
        channel=NotificationChannel.INAPP,
        recipient="ahmed",
        subject="Ticket TKT-1",
        body="Ticket TKT-1 needs attention.",
        reference="",
        event_name="workflow.notification",
    )


def test_notification_executor_missing_recipient_fails_clearly():
    executor = NotificationExecutor()
    node_input = NodeInput(instance_context={}, node_config={"channel": "inapp", "subject": "x", "body": "y"})
    output = executor.run(node_input)
    assert output.status == "failed"
    assert "recipient" in (output.error or "")
