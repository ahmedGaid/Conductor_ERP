from erp.purchasing.events import PR_SUBMITTED, PO_APPROVED
from erp.sales.events import ORDER_CONFIRMED
from erp.workflow.trigger_catalog import TRIGGER_DISPLAY, TRIGGER_FIELDS


def test_every_used_trigger_has_both_language_labels():
    used_events = [PR_SUBMITTED, PO_APPROVED, ORDER_CONFIRMED]
    for name in used_events:
        assert name in TRIGGER_DISPLAY, f"missing display entry for {name}"
        assert TRIGGER_DISPLAY[name]["ar"], f"missing Arabic label for {name}"
        assert TRIGGER_DISPLAY[name]["en"], f"missing English label for {name}"


def test_trigger_fields_have_both_language_labels():
    fields = TRIGGER_FIELDS.get(PR_SUBMITTED, [])
    assert fields, "PR_SUBMITTED needs at least one condition field"
    for f in fields:
        assert f["label"]["ar"] and f["label"]["en"]


def test_trigger_display_never_leaks_raw_event_name_as_label():
    for name, labels in TRIGGER_DISPLAY.items():
        assert labels["ar"] != name
        assert labels["en"] != name
