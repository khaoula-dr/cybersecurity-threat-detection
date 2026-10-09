import sys

sys.path.insert(0, "/opt/ml/processing/lib")
import json

import pandas as pd
from preprocessing import fit_spec, stratified_split, to_csv_bytes, transform

IN, OUT = "/opt/ml/processing/input/", "/opt/ml/processing/output/"

full = pd.read_csv(IN + "UNSW_NB15_training-set.csv")
test = pd.read_csv(IN + "UNSW_NB15_testing-set.csv")

train, val = stratified_split(full)
spec = fit_spec(train)

for name, df in [("train", train), ("validation", val), ("test", test)]:
    with open(f"{OUT}{name}/{name}.csv", "wb") as f:
        f.write(to_csv_bytes(df, transform(df, spec)))
    print(name, len(df))

with open(OUT + "spec/columns.json", "w") as f:
    json.dump(spec, f)