#!/usr/bin/env python3
"""Build home-washer.sqlite from curated shortlist data (stdlib only)."""

from __future__ import annotations

import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
DB_PATH = ROOT / "home-washer.sqlite"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from checkpoints import attach_meta, evaluate_model  # noqa: E402

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

CREATE TABLE tco_5y (
  id              INTEGER PRIMARY KEY,
  model_id        INTEGER REFERENCES models(id) ON DELETE CASCADE,
  slug            TEXT NOT NULL UNIQUE,
  price_hkd       REAL NOT NULL,
  risk_tier       TEXT NOT NULL,   -- A..G
  p_fail_5y       REAL NOT NULL,
  repair_cost_hkd REAL NOT NULL,
  expected_repair REAL NOT NULL,
  install_extra   REAL NOT NULL,
  energy_5y_hkd   REAL NOT NULL,
  tco_hkd         REAL NOT NULL,
  note            TEXT
);

CREATE TABLE checkpoint_results (
  model_id INTEGER PRIMARY KEY REFERENCES models(id) ON DELETE CASCADE,
  cp1      TEXT NOT NULL,   -- pass | watch | fail
  cp2      TEXT NOT NULL,
  cp3      TEXT NOT NULL,
  overall  TEXT NOT NULL,
  summary  TEXT
);

CREATE TABLE checkpoint_findings (
  id          INTEGER PRIMARY KEY,
  model_id    INTEGER NOT NULL REFERENCES models(id) ON DELETE CASCADE,
  checkpoint  TEXT NOT NULL,  -- cp1 | cp2 | cp3
  rule        TEXT NOT NULL,
  status      TEXT NOT NULL,
  message     TEXT NOT NULL
);

CREATE VIEW v_shortlist AS
SELECT
  m.slug, m.brand, m.model, m.capacity_kg, m.spin_rpm, m.width_mm,
  m.energy_grade, m.annual_kwh, m.water_l, m.esp, m.drain, m.shortlist,
  m.under_2000,
  MIN(p.price_hkd) AS min_price_hkd,
  t.tco_hkd AS tco_5y_hkd
FROM models m
LEFT JOIN prices p ON p.model_id = m.id
LEFT JOIN tco_5y t ON t.model_id = m.id
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
  COALESCE(t.tco_hkd, min_price_hkd);

CREATE VIEW v_checkpoints AS
SELECT
  m.slug, m.brand, m.model, m.shortlist, m.under_2000,
  MIN(p.price_hkd) AS min_price_hkd,
  r.cp1, r.cp2, r.cp3, r.overall, r.summary
FROM models m
JOIN checkpoint_results r ON r.model_id = m.id
LEFT JOIN prices p ON p.model_id = m.id
GROUP BY m.id
ORDER BY
  CASE r.overall
    WHEN 'pass' THEN 1
    WHEN 'watch' THEN 2
    WHEN 'fail' THEN 3
    ELSE 9
  END,
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
        "toshiba-aw-q801aph", "Toshiba", "AW-Q801APH(WW)",
        7.0, 680, 515, 940, 525, 1, 15, 92, 0.00830, "high_low", None, 1,
        "complete", "primary", 1, "U3-W250106",
        "User ref PRIMARY: Toshiba pulsator MTBF/parts; CYE $1880",
        "models/toshiba-aw-q801aph.md",
    ),
    (
        "hitachi-ltl065sm00", "Hitachi", "LTL 065SM00",
        6.5, 830, 500, 850, 535, 1, 15, 85, 0.00890, "high_low", 1.5, 0,
        "complete", "alt", 1, "U3-W250072",
        "Spec strong; demoted from primary per user ref assumption-1 brand premium risk",
        "models/hitachi-ltl065sm00.md",
    ),
    (
        "whirlpool-vemc65811", "Whirlpool", "VEMC65811",
        6.5, 850, 500, 890, 530, 1, 13, 87, 0.00770, "high_low", None, 1,
        "complete", "alt", 1, "U3-W240039",
        "CYE $1880; demoted per user ref assumption-3 belt/humidity risk",
        "models/whirlpool-vemc65811.md",
    ),
    (
        "toshiba-aw-q751aph", "Toshiba", "AW-Q751APH(WW)",
        6.5, 680, 515, 940, 525, 1, 16, 98, 0.00920, "high_low", None, 1,
        "complete", "alt", 1, "U3-W250105",
        "CYE $1799 cheapest Toshiba Grade-1 band; weak spin",
        "models/toshiba-aw-q751aph.md",
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
        "complete", "demote", 1, "U3-W250157",
        "High drain risk + white-label parts risk per user ref assumption-2",
        "models/fortress-fjw75m25.md",
    ),
    (
        "sharp-es-hk750x-w", "Sharp", "ES-HK750X-W",
        7.5, 700, 530, 917, 550, 1, 18, 120, 0.00930, "high_low", None, 1,
        "complete", "alt", 1, "U3-W250082",
        "Suning $1980; 7.5kg glass lid; high water 120L — capacity alt only",
        "models/sharp-es-hk750x-w.md",
    ),
    (
        "midea-mj70n68p", "Midea", "MJ70N68P",
        7.0, 680, 515, 910, 525, 2, 23, 92, 0.01260, "high_low", None, 1,
        "complete", "alt", 1, "U3-W210074",
        "Electric Tung ~$1842–1899; Grade 2; loses to Q801 in same band",
        "models/midea-mj70n68p.md",
    ),
    (
        "toshiba-aw-m731aph", "Toshiba", "AW-M731APH(WW)",
        6.3, 700, 515, 920, 525, 4, 24, 93, 0.01460, "high_low", None, 1,
        "complete", "demote", 1, "U3-W220055",
        "Ecox $1780; EMSD Grade 4 — retailers often wrongly claim Grade 1",
        "models/toshiba-aw-m731aph.md",
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
    ("hitachi-ltl065sm00", "Suning", 1800, None, "2026-09-14",
     "https://product.hksuning.com/0000000000/12449132770.html", "Best seen street for 065"),
    ("whirlpool-vemc65811", "CYE", 1880, 2798, "2026-09-14", "https://www.cyeshop.com/540-Tub-Washers", None),
    ("whirlpool-vemc65811", "Suning", 1880, None, "2026-09-14",
     "https://product.hksuning.com/0000000000/12436797185.html", None),
    ("toshiba-aw-q751aph", "CYE", 1799, 2880, "2026-09-14", "https://www.cyeshop.com/540-Tub-Washers", None),
    ("toshiba-aw-q751aph", "Suning", 1930, None, "2026-09-14",
     "https://product.hksuning.com/0000000000/12449552608.html", "Listing wrongly says 6.3kg/715rpm"),
    ("toshiba-aw-q801aph", "CYE", 1880, 3380, "2026-09-14",
     "https://www.cyeshop.com/Tub-Washers/10760-12968-%E6%9D%B1%E8%8A%9D-toshiba-aw-q801aphww-7%E5%85%AC%E6%96%A4-%E6%97%A5%E5%BC%8F%E6%B4%97%E8%A1%A3%E6%A9%9F-%E7%B5%90%E5%90%88%E9%AB%98%E4%BD%8E%E6%B0%B4%E4%BD%8D.html",
     None),
    ("toshiba-aw-q801aph", "Suning", 1880, None, "2026-09-14",
     "https://product.hksuning.com/0000000000/12449552609.html", None),
    ("hitachi-ltl07sm00", "CYE", 1980, 2880, "2026-09-14", "https://www.cyeshop.com/540-Tub-Washers", None),
    ("hitachi-ltl07sm00", "EEH FPS", 1920, 2880, "2026-09-14", "https://www.eeh.hk/LTL07SM00WH", None),
    ("hitachi-ltl07sm00", "Fortress", 2180, 2880, "2026-09-14", None, "Often over $2k"),
    ("sharp-es-hk750x-w", "Suning", 1980, None, "2026-09-14",
     "https://product.hksuning.com/0000000000/12449238826.html", None),
    ("midea-mj70n68p", "Electric Tung FPS", 1842, 2789, "2026-09-14",
     "https://www.electrictung.com/tub-washers/mj70n68p", "Other pay ~$1899"),
    ("midea-mj70n68p", "The Club", 1798, 2789, "2026-09-14",
     "https://shop.theclub.com.hk/midea-7kg-automatic-tub-washer-combined-drain-pump-included-standard-installation-mj70n68p-cr-mj70n68p",
     "Points+cash listing"),
    ("toshiba-aw-m731aph", "Ecox", 1780, 2780, "2026-09-14",
     "https://ecox.com.hk/shop/hk/toshiba-aw-m731aph-ww-automatic-tub-washer-6-3kg-combined-drain-pump.html",
     "Suning/YOHO delisted"),
    ("toshiba-aw-m731aph", "Usave", 1950, None, "2026-09-14",
     "https://www.usave.com.hk/index.php?main_page=product_info&products_id=6618", None),
    ("fortress-fjw75m25", "Fortress in-store", 1780, 2890, "2026-09-12", None, "Photo price tag"),
    ("hitachi-ltl08sm00", "Fortress in-store", 2180, 3180, "2026-09-12", None, "Photo"),
    ("hitachi-ltl08sm00", "CYE", 2080, 3180, "2026-09-14", "https://www.cyeshop.com/540-Tub-Washers", None),
    ("hitachi-ltl08sm00", "Suning", 2380, None, "2026-09-14",
     "https://product.hksuning.com/0000000000/12446695975.html", "Over $2k"),
    ("fortress-fjw85m25", "Fortress web", 2200, 3099, "2026-09-14", None, "List price band"),
]

SOURCES = [
    (None, "official", "Hitachi single-tub lineup",
     "https://www.hitachi-homeappliances.com.hk/tc/products/single-tub.html", None),
    (None, "retailer", "CYE Tub Washers",
     "https://www.cyeshop.com/540-Tub-Washers", "Price-asc category URL blocked bots"),
    (None, "retailer", "Suning washers $1400-2800",
     "https://search.hksuning.com/search/list?ci=503369&cf=1400_2800", "2026-09-14 scrape"),
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
    ("sharp-es-hk750x-w", "emsd", "EMSD U3-W250082",
     "https://www.emsd.gov.hk/energylabel/en/households/wm/select_wm_detail.php?refid=U3-W250082", None),
    ("midea-mj70n68p", "emsd", "EMSD U3-W210074",
     "https://www.emsd.gov.hk/energylabel/en/households/wm/select_wm_detail.php?refid=U3-W210074", None),
    ("toshiba-aw-m731aph", "emsd", "EMSD U3-W220055",
     "https://www.emsd.gov.hk/energylabel/en/households/wm/select_wm_detail.php?refid=U3-W220055", None),
    (None, "retailer", "Midea/Toshiba ≤$2k scan notes",
     None, "2026-09-14-midea-toshiba-under-2000.md"),
    (None, "forum", "Consumer Council #513 washer reliability",
     "https://www.consumer.org.hk/tc/article/513-appliance-reliability-survey/513-survey-wm",
     "Panasonic 16% / Whirlpool 28%; avg repair $1083; type gap slight"),
]

# slug, price, tier, p, C, I, annual_kwh, note
# expected_repair = p*C; energy = annual_kwh*5*1.2; tco = P + pC + I + energy
TCO_ROWS = [
    ("toshiba-aw-q751aph", 1799, "A", 0.10, 900, 0, 16,
     "Cheapest Toshiba TCO band"),
    ("toshiba-aw-q801aph", 1880, "A", 0.10, 900, 0, 15,
     "PRIMARY; parts liquidity"),
    ("toshiba-aw-m731aph", 1780, "C", 0.12, 900, 0, 24,
     "Grade 4 energy penalty in E"),
    ("hitachi-ltl065sm00", 1800, "B", 0.11, 1200, 0, 15,
     "OEM board premium in C"),
    ("midea-mj70n68p", 1842, "E", 0.15, 900, 0, 23, None),
    ("whirlpool-vemc65811", 1880, "D", 0.16, 1080, 0, 13,
     "p=0.16 from CC #513 5y fail"),
    ("fortress-fjw75m25", 1780, "F", 0.22, 1000, 100, 16,
     "White-label + high-drain install risk"),
    ("hitachi-ltl07sm00", 1980, "B", 0.11, 1200, 0, 19, None),
    ("sharp-es-hk750x-w", 1980, "C", 0.12, 1000, 0, 18, None),
    ("hitachi-ltl08sm00", 2080, "B", 0.11, 1200, 0, 22, None),
    ("fortress-fjw85m25", 2200, "F", 0.22, 1000, 100, 18, None),
]


def emsd_url(ref: str | None) -> str | None:
    if not ref:
        return None
    return f"https://www.emsd.gov.hk/energylabel/en/households/wm/select_wm_detail.php?refid={ref}"


def _prices_by_slug() -> dict[str, list[float]]:
    grouped: dict[str, list[float]] = defaultdict(list)
    for slug, _channel, price, *_rest in PRICES:
        grouped[slug].append(price)
    return grouped


def library_checkpoint_record(row: tuple, prices_by_slug: dict[str, list[float]]) -> dict:
    slug = row[0]
    rec = {
        "slug": slug,
        "capacity_kg": row[3],
        "spin_rpm": row[4],
        "width_mm": row[5],
        "energy_grade": row[8],
        "annual_kwh": row[9],
        "water_l": row[10],
        "drain": row[12],
        "status": row[15],
        "emsd_ref": row[18],
        "min_price": min(prices_by_slug[slug]) if prices_by_slug.get(slug) else None,
    }
    return attach_meta(slug, rec)


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

    for slug, price, tier, p, c, install, kwh, note in TCO_ROWS:
        exp = round(p * c)
        energy = round(kwh * 5 * 1.2)
        tco = round(price + exp + install + energy)
        con.execute(
            """
            INSERT INTO tco_5y (
              model_id, slug, price_hkd, risk_tier, p_fail_5y, repair_cost_hkd,
              expected_repair, install_extra, energy_5y_hkd, tco_hkd, note
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """,
            (slug_ids[slug], slug, price, tier, p, c, exp, install, energy, tco, note),
        )

    prices_by_slug = _prices_by_slug()
    for row in MODELS:
        rec = library_checkpoint_record(row, prices_by_slug)
        check = evaluate_model(rec)
        mid = slug_ids[check.slug]
        con.execute(
            """
            INSERT INTO checkpoint_results (model_id, cp1, cp2, cp3, overall, summary)
            VALUES (?,?,?,?,?,?)
            """,
            (mid, check.cp1.status, check.cp2.status, check.cp3.status, check.overall, check.summary),
        )
        for gate in (check.cp1, check.cp2, check.cp3):
            for finding in gate.findings:
                con.execute(
                    """
                    INSERT INTO checkpoint_findings (
                      model_id, checkpoint, rule, status, message
                    ) VALUES (?,?,?,?,?)
                    """,
                    (mid, gate.checkpoint, finding.rule, finding.status, finding.message),
                )

    con.commit()

    n_models = con.execute("SELECT COUNT(*) FROM models").fetchone()[0]
    n_prices = con.execute("SELECT COUNT(*) FROM prices").fetchone()[0]
    n_tco = con.execute("SELECT COUNT(*) FROM tco_5y").fetchone()[0]
    print(f"Wrote {DB_PATH.name}: {n_models} models, {n_prices} prices, {n_tco} TCO rows")
    print("\nShortlist by TCO:")
    for r in con.execute(
        "SELECT slug, shortlist, min_price_hkd, tco_5y_hkd FROM v_shortlist ORDER BY tco_5y_hkd NULLS LAST"
    ):
        print(f"  {r[0]:28} {r[1]:8} P=${r[2] or '-':>6}  TCO₅=${r[3] or '-':>6}")

    print("\nCheckpoints (CP1 入場 / CP2 核實 / CP3 決策):")
    for r in con.execute(
        "SELECT slug, cp1, cp2, cp3, overall FROM v_checkpoints"
    ):
        print(f"  {r[0]:28} {r[1]:5} {r[2]:5} {r[3]:5}  → {r[4]}")
    con.close()


if __name__ == "__main__":
    main()
