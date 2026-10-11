from pathlib import Path

from netsentinel.vendor import is_locally_administered, is_unicast, manufacturer_for_mac, normalize_prefix


def test_oui_prefix_normalization():
    assert normalize_prefix("aa-bb-cc") == "AABBCC"
    assert normalize_prefix("AA:BB:CC:D") == "AABBCCD"
    assert normalize_prefix("not-an-oui") is None


def test_vendor_lookup_supports_simple_and_ieee_csv(tmp_path: Path):
    csv_file = tmp_path / "oui.csv"
    csv_file.write_text(
        "Assignment,Organization Name\nAABBCC,Example Vendor LLC\nAABBCCD,Specific Vendor\n",
        encoding="utf-8",
    )
    assert manufacturer_for_mac("AA:BB:CC:00:00:01", csv_file) == "Example Vendor LLC"
    assert manufacturer_for_mac("AA:BB:CC:D0:00:01", csv_file) == "Specific Vendor"
    assert manufacturer_for_mac("AA:BB:CD:00:00:01", csv_file) is None


def test_locally_administered_and_unicast_bits():
    assert is_locally_administered("02:11:22:33:44:55")
    assert not is_locally_administered("00:11:22:33:44:55")
    assert is_unicast("00:11:22:33:44:55")
    assert not is_unicast("01:11:22:33:44:55")
