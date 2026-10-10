import json
import time

import boto3

lam = boto3.client("lambda", region_name="eu-north-1")

CASES = [
    ("Attaque Exploits", "Suspicious", {"proto": "zero", "service": "-", "state": "INT", "sttl": 254.0, "dur": 8e-06, "spkts": 2.0, "dpkts": 0.0, "sbytes": 200.0, "dbytes": 0.0, "rate": 125000.0003, "dttl": 0.0, "smean": 100.0, "dmean": 0.0}),
    ("Normal sttl=62", "Normal", {"proto": "tcp", "service": "http", "state": "FIN", "sttl": 62.0, "dur": 1.687215, "spkts": 10.0, "dpkts": 10.0, "sbytes": 848.0, "dbytes": 1262.0, "rate": 11.261161, "dttl": 252.0, "smean": 85.0, "dmean": 126.0}),
    ("Normal sttl=254 (limite connue)", "Suspicious", {"proto": "tcp", "service": "-", "state": "FIN", "sttl": 254.0, "dur": 1.009307, "spkts": 10.0, "dpkts": 8.0, "sbytes": 2516.0, "dbytes": 354.0, "rate": 16.84324, "dttl": 252.0, "smean": 252.0, "dmean": 44.0}),
]


def call(event):
    t = time.time()
    r = lam.invoke(FunctionName="ctds-inference", Payload=json.dumps(event).encode())
    body = json.loads(r["Payload"].read())
    return r.get("FunctionError"), body, (time.time() - t) * 1000


import sys

if len(sys.argv) > 1 and sys.argv[1] == "error":
    err, body, ms = call({"sttl": "abc"})
    print("Erreur volontaire :", "OK (erreur levée)" if err else "KO (pas d'erreur)")
    print(body.get("errorType"), "-", body.get("errorMessage"))
    sys.exit()

for name, expected, event in CASES:
    for i in (1, 2):
        err, body, ms = call(event)
        if err:
            print(f"{name} #{i}: ERREUR {body}")
            continue
        ok = "PASS" if body["prediction"] == expected else "FAIL"
        print(f"{ok} {name} #{i}: {body['prediction']} ({body['probability']}) {ms:.0f} ms")