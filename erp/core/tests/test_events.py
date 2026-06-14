"""Fault-isolation contract: a failing subscriber must not break the publisher."""
from __future__ import annotations

from erp.core.events import EventBus


def test_failing_subscriber_does_not_break_publish():
    bus = EventBus()
    seen = []

    def bad_handler(_event):
        raise RuntimeError("subscriber blew up")

    def good_handler(event):
        seen.append(event.payload["x"])

    bus.subscribe("Thing.Happened", bad_handler)
    bus.subscribe("Thing.Happened", good_handler)

    # Publish must succeed despite bad_handler raising...
    event = bus.publish("Thing.Happened", {"x": 42})

    # ...and the healthy subscriber still ran.
    assert event.name == "Thing.Happened"
    assert seen == [42]


def test_publish_attaches_correlation_id():
    from erp.core.correlation import correlation_scope

    bus = EventBus()
    with correlation_scope("CID-TEST") as cid:
        event = bus.publish("X.Y")
    assert event.correlation_id == cid == "CID-TEST"
