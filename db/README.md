# SQLite

```bash
python3 scripts/build_db.py
```

Creates `home-washer.sqlite` at repo root.

| Object | Purpose |
| --- | --- |
| `models` | Specs, EMSD, shortlist |
| `prices` | HKD by channel |
| `sources` | URLs |
| `tco_5y` | 5-year TCO rows |
| `checkpoint_results` | CP1/CP2/CP3 + overall per model |
| `checkpoint_findings` | Per-rule pass/watch/fail messages |
| `v_shortlist` | models + min price + TCO |
| `v_checkpoints` | shortlist + three-gate board |

Filter rules: `scripts/checkpoints.py`（說明見 [[../2026-09-14-data-checkpoints|資料篩選三關]]）。

```bash
python3 -m unittest scripts.test_checkpoints
```

Edit seed data in `scripts/build_db.py`, then rebuild.
