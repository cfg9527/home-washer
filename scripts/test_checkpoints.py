#!/usr/bin/env python3
"""Unit tests for washer data-filter checkpoints."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_db
import checkpoints as cp


def _base(**overrides):
    rec = {
        "slug": "test-model",
        "form": "top_pulsator",
        "min_price": 1880,
        "capacity_kg": 7.0,
        "emsd_ref": "U3-TEST",
        "energy_grade": 1,
        "annual_kwh": 15,
        "water_l": 90,
        "width_mm": 515,
        "spin_rpm": 680,
        "drain": "high_low",
        "status": "complete",
        "conflicts": [],
        "white_label": False,
        "belt_risk": False,
        "brand_premium_risk": False,
        "stainless_drum": True,
        "damper_lid": True,
        "warranty_machine_yr": 2,
        "warranty_motor_yr": 5,
        "line": "toshiba_q",
    }
    rec.update(overrides)
    return rec


def library_record(slug: str) -> dict:
    model = next(row for row in build_db.MODELS if row[0] == slug)
    (
        slug, _brand, _name, cap, rpm, w, _h, _d, grade, kwh, water, _esp,
        drain, _air, _glass, status, _short, _u2k, emsd, _notes, _md,
    ) = model
    prices = [p[2] for p in build_db.PRICES if p[0] == slug]
    rec = {
        "slug": slug,
        "min_price": min(prices) if prices else None,
        "capacity_kg": cap,
        "spin_rpm": rpm,
        "width_mm": w,
        "energy_grade": grade,
        "annual_kwh": kwh,
        "water_l": water,
        "drain": drain,
        "status": status,
        "emsd_ref": emsd,
    }
    return cp.attach_meta(slug, rec)


class RuleTests(unittest.TestCase):
    def test_cp1_rejects_front_loader(self):
        g = cp.eval_cp1(_base(form="front_loader"))
        self.assertEqual(g.status, "fail")
        self.assertTrue(any(f.rule == "cp1.form" and f.status == "fail" for f in g.findings))

    def test_cp1_price_bands(self):
        self.assertEqual(cp.eval_cp1(_base(min_price=2000)).status, "pass")
        self.assertEqual(cp.eval_cp1(_base(min_price=2080)).status, "watch")
        self.assertEqual(cp.eval_cp1(_base(min_price=2200)).status, "watch")
        self.assertEqual(cp.eval_cp1(_base(min_price=2201)).status, "fail")
        self.assertEqual(cp.eval_cp1(_base(min_price=None)).status, "fail")

    def test_cp1_capacity_bands(self):
        self.assertEqual(cp.eval_cp1(_base(capacity_kg=6.0)).status, "pass")
        self.assertEqual(cp.eval_cp1(_base(capacity_kg=7.5)).status, "pass")
        self.assertEqual(cp.eval_cp1(_base(capacity_kg=8.0)).status, "watch")
        self.assertEqual(cp.eval_cp1(_base(capacity_kg=8.5)).status, "fail")

    def test_cp1_requires_emsd(self):
        self.assertEqual(cp.eval_cp1(_base(emsd_ref=None)).status, "fail")

    def test_cp2_resolved_conflict_is_watch(self):
        rec = _base(
            conflicts=[
                {
                    "field": "energy_grade",
                    "retailer": "店寫 1 級",
                    "official": "EMSD 4 級",
                    "emsd_wins": True,
                }
            ]
        )
        g = cp.eval_cp2(rec)
        self.assertEqual(g.status, "watch")

    def test_cp2_unresolved_conflict_fails(self):
        rec = _base(
            conflicts=[
                {
                    "field": "energy_grade",
                    "retailer": "1",
                    "official": "4",
                    "emsd_wins": False,
                }
            ]
        )
        self.assertEqual(cp.eval_cp2(rec).status, "fail")

    def test_cp2_incomplete_dims_fail(self):
        self.assertEqual(cp.eval_cp2(_base(width_mm=None)).status, "fail")
        self.assertEqual(cp.eval_cp2(_base(drain="unknown")).status, "fail")
        self.assertEqual(cp.eval_cp2(_base(status="identified")).status, "fail")

    def test_cp3_energy_and_assumptions(self):
        self.assertEqual(cp.eval_cp3(_base(energy_grade=4)).status, "fail")
        self.assertEqual(cp.eval_cp3(_base(white_label=True)).status, "fail")
        self.assertEqual(cp.eval_cp3(_base(belt_risk=True)).status, "watch")
        self.assertEqual(cp.eval_cp3(_base(brand_premium_risk=True)).status, "watch")
        self.assertEqual(cp.eval_cp3(_base(drain="high")).status, "watch")
        self.assertEqual(cp.eval_cp3(_base(drain="unknown")).status, "fail")
        self.assertEqual(cp.eval_cp3(_base(water_l=120)).status, "watch")

    def test_clean_toshiba_q_passes_all(self):
        check = cp.evaluate_model(_base(slug="clean-q"))
        self.assertEqual(check.cp1.status, "pass")
        self.assertEqual(check.cp2.status, "pass")
        self.assertEqual(check.cp3.status, "pass")
        self.assertEqual(check.overall, "pass")


class LibrarySnapshotTests(unittest.TestCase):
    """Lock the three-gate outcomes for the current curated catalogue."""

    EXPECTED = {
        "toshiba-aw-q801aph": ("pass", "pass", "pass", "pass"),
        "toshiba-aw-q751aph": ("pass", "watch", "pass", "watch"),
        "hitachi-ltl065sm00": ("pass", "pass", "watch", "watch"),
        "whirlpool-vemc65811": ("pass", "pass", "watch", "watch"),
        "sharp-es-hk750x-w": ("pass", "pass", "watch", "watch"),
        "midea-mj70n68p": ("pass", "watch", "watch", "watch"),
        "hitachi-ltl07sm00": ("pass", "watch", "watch", "watch"),
        "toshiba-aw-m731aph": ("pass", "watch", "fail", "fail"),
        "fortress-fjw75m25": ("pass", "pass", "fail", "fail"),
        "hitachi-ltl08sm00": ("watch", "watch", "watch", "watch"),
        "fortress-fjw85m25": ("fail", "fail", "fail", "fail"),
    }

    def test_every_seeded_model_has_meta(self):
        slugs = {row[0] for row in build_db.MODELS}
        self.assertEqual(slugs, set(cp.META))
        self.assertEqual(slugs, set(self.EXPECTED))

    def test_library_gate_outcomes(self):
        for slug, expected in self.EXPECTED.items():
            with self.subTest(slug=slug):
                check = cp.evaluate_model(library_record(slug))
                got = (check.cp1.status, check.cp2.status, check.cp3.status, check.overall)
                self.assertEqual(got, expected)

    def test_only_q801_is_all_green(self):
        all_green = [
            slug
            for slug in self.EXPECTED
            if cp.evaluate_model(library_record(slug)).overall == "pass"
        ]
        self.assertEqual(all_green, ["toshiba-aw-q801aph"])

    def test_index_html_board_matches_engine(self):
        html = Path(__file__).resolve().parents[1].joinpath("index.html").read_text(encoding="utf-8")
        for slug, (c1, c2, c3, overall) in self.EXPECTED.items():
            needle = (
                f'data-slug="{slug}" data-cp1="{c1}" data-cp2="{c2}" '
                f'data-cp3="{c3}" data-overall="{overall}"'
            )
            self.assertIn(needle, html, msg=slug)


if __name__ == "__main__":
    unittest.main()
