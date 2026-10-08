import sys
sys.path.insert(0, "lambda")
import pandas as pd
from preprocessing import fit_spec, transform, stratified_split


def make_df(n=100):
    return pd.DataFrame({
        "id": range(n), "dur": [0.1] * n, "proto": ["tcp"] * (n - 2) + ["rare", "rare"],
        "service": ["-"] * n, "state": ["FIN"] * n, "sbytes": [10] * n,
        "stcpb": [0] * n, "dtcpb": [0] * n, "ct_ftp_cmd": [0] * n,
        "attack_cat": ["Normal"] * n, "label": [0, 1] * (n // 2),
    })


def test_columns_and_unknown_category():
    train = make_df()
    spec = fit_spec(train)
    unseen = make_df(10).assign(state="ACC")
    out = transform(unseen, spec)
    assert list(out.columns) == spec["columns"]
    assert "id" not in out.columns and "attack_cat" not in out.columns
    assert out["state_FIN"].sum() == 0


def test_split_is_stratified_and_disjoint():
    tr, va = stratified_split(make_df())
    assert set(tr.index).isdisjoint(va.index)
    assert abs(va["label"].mean() - 0.5) < 0.05