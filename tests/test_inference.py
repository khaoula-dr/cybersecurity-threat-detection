import sys
sys.path.insert(0, "lambda")
from inference import build_row, classify

SPEC = {
    "numeric": ["dur", "sttl"],
    "protos": ["tcp", "udp"],
    "service": ["-", "http"],
    "state": ["FIN"],
    "columns": ["dur", "sttl", "proto_tcp", "proto_udp", "proto_other",
                "service_-", "service_http", "state_FIN"],
}
DEFAULTS = {"dur": 0.5, "sttl": 100.0}


def test_order_defaults_and_onehot():
    row = build_row({"sttl": 254, "proto": "tcp", "service": "http", "state": "FIN"}, SPEC, DEFAULTS)
    assert row == [0.5, 254.0, 1, 0, 0, 0, 1, 1]


def test_unknown_values_become_zero_or_other():
    row = build_row({"proto": "icmp", "state": "ACC"}, SPEC, DEFAULTS)
    assert len(row) == len(SPEC["columns"])
    assert row[4] == 1.0 and row[7] == 0.0


def test_threshold():
    assert classify(0.97)["prediction"] == "Suspicious"
    assert classify(0.2)["prediction"] == "Normal"