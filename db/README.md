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
| `v_shortlist` | models + min price |

Edit seed data in `scripts/build_db.py`, then rebuild.
