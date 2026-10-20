"""PHM 2018 train CSV(장비 1대) + fault 파일 → runs / run_steps / faults.
usage: uv run python ingest_phm.py ../data/phm_data_challenge_2018/train/01_M01_DC_train.csv
"""
import csv
import math
import sys
from collections import defaultdict
from pathlib import Path

import db

META = ["time", "Tool", "stage", "Lot", "runnum", "recipe", "recipe_step"]


def step_name(v):
    return v[:-2] if v.endswith(".0") else (v or "NA")


def ingest(path):
    path = Path(path)
    runs = {}  # (tool, run_id) -> dict(meta)
    acc = defaultdict(lambda: [0, 0, 0.0, 0.0, math.inf, -math.inf])  # n, missing, sum, sumsq, min, max
    multi_recipe = set()
    with path.open() as f:
        r = csv.reader(f)
        head = next(r)
        sig = head[len(META):]
        for row in r:
            t, tool, stage, lot, runnum, recipe, step = row[:7]
            t = float(t)
            rid = f"{runnum}-{lot}"
            m = runs.get((tool, rid))
            if m is None:
                runs[(tool, rid)] = m = dict(runnum=int(runnum), lot=lot, stage=stage, recipe=recipe, start=t, end=t, n=0)
            elif m["recipe"] != recipe:
                multi_recipe.add((tool, rid))
            m["end"] = t
            m["n"] += 1
            step = step_name(step)
            for s, v in zip(sig, row[7:]):
                a = acc[(tool, rid, step, s)]
                a[0] += 1
                if v == "":
                    a[1] += 1
                    continue
                x = float(v)
                a[2] += x
                a[3] += x * x
                a[4] = min(a[4], x)
                a[5] = max(a[5], x)
    if multi_recipe:
        print(f"경고: recipe가 2개 이상인 run {len(multi_recipe)}건 (첫 recipe로 기록)")

    with db.pool.connection() as c:
        tools = {t for t, _ in runs}
        for t in tools:
            c.execute("DELETE FROM run_steps WHERE tool = %s", (t,))
            c.execute("DELETE FROM runs WHERE tool = %s", (t,))
            c.execute("DELETE FROM faults WHERE tool = %s", (t,))
        with c.cursor().copy("COPY runs (tool, run_id, runnum, lot, stage, recipe, start_time, end_time, n_rows) FROM STDIN") as cp:
            for (tool, rid), m in runs.items():
                cp.write_row((tool, rid, m["runnum"], m["lot"], m["stage"], m["recipe"], m["start"], m["end"], m["n"]))
        with c.cursor().copy("COPY run_steps (tool, run_id, recipe_step, signal, n, mean, std, min, max, missing_rate) FROM STDIN") as cp:
            for (tool, rid, step, s), (n, miss, sm, ss, mn, mx) in acc.items():
                k = n - miss
                mean = sm / k if k else None
                std = math.sqrt(max(0.0, ss / k - mean * mean)) if k else None
                cp.write_row((tool, rid, step, s, n, mean, std, mn if k else None, mx if k else None, miss / n))
        # fault 파일: train/train_faults/01_M01_train_fault_data.csv
        fault_file = path.parent / "train_faults" / path.name.replace("_DC_train", "_train_fault_data")
        nf = 0
        if fault_file.exists():
            with fault_file.open() as f, c.cursor().copy("COPY faults (tool, time, fault_name) FROM STDIN") as cp:
                for row in csv.DictReader(f):
                    cp.write_row((row["Tool"], float(row["time"]), row["fault_name"]))
                    nf += 1
    print(f"{path.name}: runs={len(runs)} run_steps={len(acc)} faults={nf}")


if __name__ == "__main__":
    db.init()
    for p in sys.argv[1:]:
        ingest(p)
    db.pool.close()
