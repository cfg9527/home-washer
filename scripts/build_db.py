#!/usr/bin/env python3
"""Build home-washer.sqlite from curated shortlist data (stdlib only)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "home-washer.sqlite"

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE models (
  id            INTEGER PRIMARY KEY,
  slug          TEXT NOT NULL UNIQUE,
  brand         TEXT NOT NULL,
  model         TEXT NOT NULL,
  capacity_kg   REAL,
  spin_rpm      INTEGER,
  width_mm      INTEGER,
  height_mm     INTEGER,
  depth_mm      INTEGER,
  energy_grade  INTEGER,
  annual_kwh    REAL,
  water_l       REAL,
  esp           REAL,
  drain         TEXT,          -- high_low | high | low | unknown
  air_jet_kg    REAL,
  glass_lid     INTEGER,       -- 0/1
  status        TEXT,          -- complete | identified | rejected
  shortlist     TEXT,          -- primary | alt | demote | drop | watch
  under_2000    INTEGER,       -- 0/1
  emsd_ref      TEXT,
  emsd_url      TEXT,
  notes         TEXT,
  md_path       TEXT
);

CREATE TABLE prices (
  id            INTEGER PRIMARY KEY,
  model_id      INTEGER NOT NULL REFERENCES models(id) ON DELETE CASCADE,
  channel       TEXT NOT NULL,
  price_hkd     REAL NOT NULL,
  list_hkd      REAL,
  observed_on   TEXT NOT NULL,  -- YYYY-MM-DD
  url           TEXT,
  note          TEXT
);

CREATE TABLE sources (
  id            INTEGER PRIMARY KEY,
  model_id      INTEGER REFERENCES models(id) ON DELETE SET NULL,
  kind          TEXT NOT NULL,  -- emsd | retailer | official | forum | photo
  title         TEXT,
  url           TEXT,
  note          TEXT
);

CREATE VIEW v_shortlist AS
SELECT
  m.slug, m.brand, m.model, m.capacity_kg, m.spin_rpm, m.width_mm,
  m.energy_grade, m.annual_kwh, m.water_l, m.esp, m.drain, m.shortlist,
  m.under_2000,
  MIN(p.price_hkd) AS min_price_hkd
FROM models m
LEFT JOIN prices p ON p.model_id = m.id
GROUP BY m.id
ORDER BY
  CASE m.shortlist
    WHEN 'primary' THEN 1
    WHEN 'alt' THEN 2
    WHEN 'demote' THEN 3
    WHEN 'watch' THEN 4
    WHEN 'drop' THEN 5
    ELSE 9
  END,
  min_price_hkd;
"""

# Curated rows from compare / model pages (2026-09-14)
MODELS = [
    # slug, brand, model, cap, rpm, w, h, d, grade, kwh, water, esp, drain, air_jet, glass, status, shortlist, u2k, emsd, notes, md
    (
        "hitachi-ltl065sm00", "Hitachi", "LTL 065SM00",
        6.5, 830, 500, 850, 535, 1, 15, 85, 0.00890, "high_low", 1.5, 0,
        "complete", "primary", 1, "U3-W250072",
        "One-person primary candidate; narrowest Hitachi; Air Jet 1.5kg",
        "models/hitachi-ltl065sm00.md",
    ),
    (
        "whirlpool-vemc65811", "Whirlpool", "VEMC65811",
        6.5, 850, 500, 890, 530, 1, 13, 87, 0.00770, "high_low", None, 1,
        "complete", "primary", 1, "U3-W240039",
        "CYE $1880; rivals 065 on spin/Esp; 500mm",
        "models/whirlpool-vemc65811.md",
    ),
    (
        "toshiba-aw-q751aph", "Toshiba", "AW-Q751APH(WW)",
        6.5, 680, 515, 940, 525, 1, 16, 98, 0.00920, "high_low", None, 1,
        "complete", "alt", 1, "U3-W250105",
        "CYE $1799 cheapest Grade-1 band; weak spin",
        "models/toshiba-aw-q751aph.md",
    ),
    (
        "toshiba-aw-q801aph", "Toshiba", "AW-Q801APH(WW)",
        7.0, 680, 515, 940, 525, 1, 15, 92, 0.00830, "high_low", None, 1,
        "complete", "alt", 1, "U3-W250106",
        "CYE $1880; 7kg + Grade 1 better value than LTL 07",
        "models/toshiba-aw-q801aph.md",
    ),
    (
        "hitachi-ltl07sm00", "Hitachi", "LTL 07SM00",
        7.0, 760, 540, 892, 565, 2, 19, 111, 0.01050, "high_low", 2.0, 1,
        "complete", "alt", 1, "U3-W250032",
        "Glass lid; EMSD Grade 2; CYE $1980",
        "models/hitachi-ltl07sm00.md",
    ),
    (
        "fortress-fjw75m25", "Fortress", "FJW75M25",
        7.5, 650, 522, 920, 520, 1, 16, 88, 0.00800, "high", None, 0,
        "complete", "alt", 1, "U3-W250157",
        "Cheapest; confirm high drain; dims from price tag approx",
        "models/fortress-fjw75m25.md",
    ),
    (
        "hitachi-ltl08sm00", "Hitachi", "LTL 08SM00",
        8.0, 760, 540, 892, 565, 2, 22, 127, 0.01030, "high_low", 2.0, 1,
        "complete", "demote", 0, "U3-W250033",
        "CYE $2080 slightly over $2k; Grade 2; overkill for one person",
        "models/hitachi-ltl08sm00.md",
    ),
    (
        "fortress-fjw85m25", "Fortress", "FJW85M25",
        8.5, 650, None, None, None, 1, 18, 97, 0.00820, "unknown", None, 0,
        "identified", "drop", 0, "U3-W250158",
        "Suggested drop; panel photo incomplete",
        "models/fortress-fjw85m25.md",
    ),
]

PRICES = [
    # slug, channel, price, list, date, url, note
    ("hitachi-ltl065sm00", "Fortress in-store", 1880, 2580, "2026-09-12", None, "Photo price tag"),
    ("whirlpool-vemc65811", "CYE", 1880, 2798, "2026-09-14", "https://www.cyeshop.com/540-Tub-Washers", None),
    ("toshiba-aw-q751aph", "CYE", 1799, 2880, "2026-09-14", "https://www.cyeshop.com/540-Tub-Washers", None),
    ("toshiba-aw-q801aph", "CYE", 1880, 3380, "2026-09-14",
     "https://www.cyeshop.com/Tub-Washers/10760-12968-%E6%9D%B1%E8%8A%9D-toshiba-aw-q801aphww-7%E5%85%AC%E6%96%A4-%E6%97%A5%E5%BC%8F%E6%B4%97%E8%A1%A3%E6%A9%9F-%E7%B5%90%E5%90%88%E9%AB%98%E4%BD%8E%E6%B0%B4%E4%BD%8D.html",
     None),
    ("hitachi-ltl07sm00", "CYE", 1980, 2880, "2026-09-14", "https://www.cyeshop.com/540-Tub-Washers", None),
    ("hitachi-ltl07sm00", "EEH FPS", 1920, 2880, "2026-09-14", "https://www.eeh.hk/LTL07SM00WH", None),
    ("hitachi-ltl07sm00", "Fortress", 2180, 2880, "2026-09-14", None, "Often over $2k"),
    ("fortress-fjw75m25", "Fortress in-store", 1780, 2890, "2026-09-12", None, "Photo price tag"),
    ("hitachi-ltl08sm00", "Fortress in-store", 2180, 3180, "2026-09-12", None, "Photo"),
    ("hitachi-ltl08sm00", "CYE", 2080, 3180, "2026-09-14", "https://www.cyeshop.com/540-Tub-Washers", None),
    ("fortress-fjw85m25", "Fortress web", 2200, 3099, "2026-09-14", None, "List price band"),
]

SOURCES = [
    (None, "official", "Hitachi single-tub lineup",
     "https://www.hitachi-homeappliances.com.hk/tc/products/single-tub.html", None),
    (None, "retailer", "CYE Tub Washers",
     "https://www.cyeshop.com/540-Tub-Washers", "Price-asc category URL blocked bots"),
    (None, "forum", "Baby Kingdom search notes",
     "https://www.baby-kingdom.com/", "No exact model threads"),
    ("hitachi-ltl065sm00", "emsd", "EMSD U3-W250072",
     "https://www.emsd.gov.hk/energylabel/en/households/wm/select_wm_detail.php?refid=U3-W250072", None),
    ("whirlpool-vemc65811", "emsd", "EMSD U3-W240039",
     "https://www.emsd.gov.hk/energylabel/en/households/wm/select_wm_detail.php?refid=U3-W240039", None),
    ("toshiba-aw-q751aph", "emsd", "EMSD U3-W250105",
     "https://www.emsd.gov.hk/energylabel/en/households/wm/select_wm_detail.php?refid=U3-W250105", None),
    ("toshiba-aw-q801aph", "emsd", "EMSD U3-W250106",
     "https://www.emsd.gov.hk/energylabel/en/households/wm/select_wm_detail.php?refid=U3-W250106", None),
    ("hitachi-ltl07sm00", "emsd", "EMSD U3-W250032",
     "https://www.emsd.gov.hk/energylabel/en/households/wm/select_wm_detail.php?refid=U3-W250032", None),
    ("hitachi-ltl08sm00", "emsd", "EMSD U3-W250033",
     "https://www.emsd.gov.hk/energylabel/en/households/wm/select_wm_detail.php?refid=U3-W250033", None),
    ("fortress-fjw75m25", "emsd", "EMSD U3-W250157",
     "https://www.emsd.gov.hk/energylabel/en/households/wm/select_wm_detail.php?refid=U3-W250157", None),
    ("fortress-fjw85m25", "emsd", "EMSD U3-W250158",
     "https://www.emsd.gov.hk/energylabel/en/households/wm/select_wm_detail.php?refid=U3-W250158", None),
]


def emsd_url(ref: str | None) -> str | None:
    if not ref:
        return None
    return f"https://www.emsd.gov.hk/energylabel/en/households/wm/select_wm_detail.php?refid={ref}"


def main() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()

    con = sqlite3.connect(DB_PATH)
    con.executescript(SCHEMA)

    slug_ids: dict[str, int] = {}
    for row in MODELS:
        (
            slug, brand, model, cap, rpm, w, h, d, grade, kwh, water, esp,
            drain, air_jet, glass, status, shortlist, u2k, emsd, notes, md,
        ) = row
        cur = con.execute(
            """
            INSERT INTO models (
              slug, brand, model, capacity_kg, spin_rpm, width_mm, height_mm, depth_mm,
              energy_grade, annual_kwh, water_l, esp, drain, air_jet_kg, glass_lid,
              status, shortlist, under_2000, emsd_ref, emsd_url, notes, md_path
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                slug, brand, model, cap, rpm, w, h, d, grade, kwh, water, esp,
                drain, air_jet, glass, status, shortlist, u2k, emsd,
                emsd_url(emsd), notes, md,
            ),
        )
        slug_ids[slug] = cur.lastrowid

    for slug, channel, price, list_p, date, url, note in PRICES:
        con.execute(
            """
            INSERT INTO prices (model_id, channel, price_hkd, list_hkd, observed_on, url, note)
            VALUES (?,?,?,?,?,?,?)
            """,
            (slug_ids[slug], channel, price, list_p, date, url, note),
        )

    for slug, kind, title, url, note in SOURCES:
        mid = slug_ids.get(slug) if slug else None
        con.execute(
            "INSERT INTO sources (model_id, kind, title, url, note) VALUES (?,?,?,?,?)",
            (mid, kind, title, url, note),
        )

    con.commit()

    n_models = con.execute("SELECT COUNT(*) FROM models").fetchone()[0]
    n_prices = con.execute("SELECT COUNT(*) FROM prices").fetchone()[0]
    print(f"Wrote {DB_PATH.name}: {n_models} models, {n_prices} prices")
    print("\nShortlist view:")
    for r in con.execute("SELECT slug, shortlist, min_price_hkd, spin_rpm, energy_grade FROM v_shortlist"):
        print(f"  {r[0]:28} {r[1]:8} ${r[2] or '-':>6}  {r[3]}rpm  G{r[4]}")
    con.close()


if __name__ == "__main__":
    main()
