#!/usr/bin/env python3
"""Three data-filter checkpoints for the Hong Kong top-load washer shortlist.

CP1 入場關 — form / budget / one-person capacity / EMSD id
CP2 核實關 — EMSD is source of truth; retailer copy is untrusted
CP3 決策關 — MTBF / parts / the three failure-mode assumptions

Statuses: pass | watch | fail
Overall: fail if any gate fails; else watch if any gate is watch; else pass.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Literal

Status = Literal["pass", "watch", "fail"]

BUDGET_HARD_HKD = 2000
BUDGET_WATCH_HKD = 2200
CAP_PASS_MIN = 6.0
CAP_PASS_MAX = 7.5
CAP_WATCH_MAX = 8.0
WATER_WATCH_L = 110

# Per-model data-quality / architecture flags that specs tuples do not carry.
# conflicts: retailer claims already caught; emsd_wins True means the record
# stores EMSD numbers (dirty listing, clean row).
META: dict[str, dict[str, Any]] = {
    "toshiba-aw-q801aph": {
        "form": "top_pulsator",
        "white_label": False,
        "belt_risk": False,
        "brand_premium_risk": False,
        "stainless_drum": True,
        "damper_lid": True,
        "warranty_machine_yr": 2,
        "warranty_motor_yr": 5,
        "line": "toshiba_q",
        "conflicts": [],
    },
    "toshiba-aw-q751aph": {
        "form": "top_pulsator",
        "white_label": False,
        "belt_risk": False,
        "brand_premium_risk": False,
        "stainless_drum": True,
        "damper_lid": True,
        "warranty_machine_yr": 2,
        "warranty_motor_yr": 5,
        "line": "toshiba_q",
        "conflicts": [
            {
                "field": "capacity_kg/spin_rpm",
                "retailer": "Suning title 6.3kg / 715rpm",
                "official": "EMSD/official 6.5kg / 680rpm",
                "emsd_wins": True,
            }
        ],
    },
    "hitachi-ltl065sm00": {
        "form": "top_pulsator",
        "white_label": False,
        "belt_risk": False,
        "brand_premium_risk": True,
        "stainless_drum": True,
        "damper_lid": False,
        "warranty_machine_yr": None,
        "warranty_motor_yr": None,
        "line": "hitachi_ltl",
        "conflicts": [],
    },
    "whirlpool-vemc65811": {
        "form": "top_pulsator",
        "white_label": False,
        "belt_risk": True,
        "brand_premium_risk": False,
        "stainless_drum": True,
        "damper_lid": True,
        "warranty_machine_yr": None,
        "warranty_motor_yr": None,
        "line": "whirlpool",
        "conflicts": [],
    },
    "hitachi-ltl07sm00": {
        "form": "top_pulsator",
        "white_label": False,
        "belt_risk": False,
        "brand_premium_risk": True,
        "stainless_drum": True,
        "damper_lid": True,
        "warranty_machine_yr": None,
        "warranty_motor_yr": None,
        "line": "hitachi_ltl",
        "conflicts": [
            {
                "field": "energy_grade",
                "retailer": "部分零售誤標 1 級",
                "official": "EMSD 2 級",
                "emsd_wins": True,
            }
        ],
    },
    "fortress-fjw75m25": {
        "form": "top_pulsator",
        "white_label": True,
        "belt_risk": False,
        "brand_premium_risk": False,
        "stainless_drum": None,
        "damper_lid": False,
        "warranty_machine_yr": None,
        "warranty_motor_yr": None,
        "line": "fortress_oem",
        "conflicts": [],
    },
    "sharp-es-hk750x-w": {
        "form": "top_pulsator",
        "white_label": False,
        "belt_risk": False,
        "brand_premium_risk": False,
        "stainless_drum": True,
        "damper_lid": True,
        "warranty_machine_yr": None,
        "warranty_motor_yr": None,
        "line": "sharp",
        "conflicts": [],
    },
    "midea-mj70n68p": {
        "form": "top_pulsator",
        "white_label": False,
        "belt_risk": False,
        "brand_premium_risk": False,
        "stainless_drum": True,
        "damper_lid": True,
        "warranty_machine_yr": None,
        "warranty_motor_yr": None,
        "line": "midea",
        "conflicts": [
            {
                "field": "energy_grade",
                "retailer": "部分文案寫 1 級",
                "official": "EMSD 2 級",
                "emsd_wins": True,
            }
        ],
    },
    "toshiba-aw-m731aph": {
        "form": "top_pulsator",
        "white_label": False,
        "belt_risk": False,
        "brand_premium_risk": False,
        "stainless_drum": True,
        "damper_lid": True,
        "warranty_machine_yr": 2,
        "warranty_motor_yr": 5,
        "line": "toshiba_old",
        "conflicts": [
            {
                "field": "energy_grade",
                "retailer": "多店誤標 1 級",
                "official": "EMSD 4 級",
                "emsd_wins": True,
            }
        ],
    },
    "hitachi-ltl08sm00": {
        "form": "top_pulsator",
        "white_label": False,
        "belt_risk": False,
        "brand_premium_risk": True,
        "stainless_drum": True,
        "damper_lid": True,
        "warranty_machine_yr": None,
        "warranty_motor_yr": None,
        "line": "hitachi_ltl",
        "conflicts": [
            {
                "field": "energy_grade",
                "retailer": "零售有時誤標 1 級",
                "official": "EMSD 2 級",
                "emsd_wins": True,
            }
        ],
    },
    "fortress-fjw85m25": {
        "form": "top_pulsator",
        "white_label": True,
        "belt_risk": False,
        "brand_premium_risk": False,
        "stainless_drum": None,
        "damper_lid": False,
        "warranty_machine_yr": None,
        "warranty_motor_yr": None,
        "line": "fortress_oem",
        "conflicts": [],
    },
}


@dataclass(frozen=True)
class Finding:
    rule: str
    status: Status
    message: str


@dataclass(frozen=True)
class GateResult:
    checkpoint: str
    status: Status
    findings: tuple[Finding, ...]


@dataclass(frozen=True)
class ModelCheck:
    slug: str
    cp1: GateResult
    cp2: GateResult
    cp3: GateResult
    overall: Status
    summary: str

    def gate(self, name: str) -> GateResult:
        return {"cp1": self.cp1, "cp2": self.cp2, "cp3": self.cp3}[name]


def worst(statuses: Iterable[Status]) -> Status:
    values = list(statuses)
    if not values:
        return "fail"
    if any(s == "fail" for s in values):
        return "fail"
    if any(s == "watch" for s in values):
        return "watch"
    return "pass"


def _finding(rule: str, status: Status, message: str) -> Finding:
    return Finding(rule, status, message)


def eval_cp1(rec: dict[str, Any]) -> GateResult:
    """Hard intake: only HK top-load pulsators in the one-person ≤$2k band."""
    findings: list[Finding] = []

    form = rec.get("form") or "top_pulsator"
    if form == "top_pulsator":
        findings.append(_finding("cp1.form", "pass", "日式上置葉輪"))
    else:
        findings.append(_finding("cp1.form", "fail", f"類型 {form} 唔入短名單（只要日式上置葉輪）"))

    price = rec.get("min_price")
    if price is None:
        findings.append(_finding("cp1.price", "fail", "無香港街價，唔入庫"))
    elif price <= BUDGET_HARD_HKD:
        findings.append(_finding("cp1.price", "pass", f"${price:.0f} ≤ $2,000"))
    elif price <= BUDGET_WATCH_HKD:
        findings.append(
            _finding("cp1.price", "watch", f"${price:.0f} 貼／稍超 $2k（≤$2,200 列 watch）")
        )
    else:
        findings.append(_finding("cp1.price", "fail", f"${price:.0f} 超 $2,200 硬頂"))

    kg = rec.get("capacity_kg")
    if kg is None:
        findings.append(_finding("cp1.capacity", "fail", "缺容量"))
    elif CAP_PASS_MIN <= kg <= CAP_PASS_MAX:
        findings.append(_finding("cp1.capacity", "pass", f"{kg:g} kg 一人用合理"))
    elif CAP_PASS_MAX < kg <= CAP_WATCH_MAX:
        findings.append(_finding("cp1.capacity", "watch", f"{kg:g} kg 一人用過剩"))
    elif kg > CAP_WATCH_MAX:
        findings.append(_finding("cp1.capacity", "fail", f"{kg:g} kg 過殺（一人用唔收 >8kg）"))
    else:
        findings.append(_finding("cp1.capacity", "watch", f"{kg:g} kg 偏細"))

    if rec.get("emsd_ref"):
        findings.append(_finding("cp1.emsd", "pass", f"EMSD {rec['emsd_ref']}"))
    else:
        findings.append(_finding("cp1.emsd", "fail", "無 EMSD 編號 — 規格無可核對來源"))

    return GateResult("cp1", worst(f.status for f in findings), tuple(findings))


def eval_cp2(rec: dict[str, Any]) -> GateResult:
    """Source-of-truth: bind core specs to EMSD; flag retailer mismatches."""
    findings: list[Finding] = []

    core = (
        rec.get("energy_grade"),
        rec.get("annual_kwh"),
        rec.get("water_l"),
        rec.get("capacity_kg"),
        rec.get("emsd_ref"),
    )
    if all(v is not None for v in core):
        findings.append(
            _finding(
                "cp2.emsd_bound",
                "pass",
                f"能源 {rec['energy_grade']} 級 · {rec['annual_kwh']:g} kWh · {rec['water_l']:g} L 已綁 EMSD",
            )
        )
    else:
        findings.append(_finding("cp2.emsd_bound", "fail", "能源／年耗電／耗水／容量未綁 EMSD"))

    conflicts = rec.get("conflicts") or []
    if not conflicts:
        findings.append(_finding("cp2.conflict", "pass", "未見零售 vs EMSD 衝突"))
    else:
        unresolved = [c for c in conflicts if not c.get("emsd_wins")]
        bits = "; ".join(
            f"{c['field']}: {c['retailer']} → {c['official']}" for c in conflicts
        )
        if unresolved:
            findings.append(_finding("cp2.conflict", "fail", f"未解決衝突：{bits}"))
        else:
            findings.append(
                _finding("cp2.conflict", "watch", f"已用 EMSD 蓋過零售誤標：{bits}")
            )

    missing: list[str] = []
    if rec.get("width_mm") is None:
        missing.append("闊度")
    if rec.get("spin_rpm") is None:
        missing.append("轉速")
    drain = rec.get("drain")
    if drain in (None, "", "unknown"):
        missing.append("排水")
    status = rec.get("status") or ""
    if status != "complete":
        missing.append(f"狀態={status or 'empty'}")
    if missing:
        findings.append(
            _finding("cp2.complete", "fail", "資料未齊：" + "、".join(missing))
        )
    else:
        findings.append(_finding("cp2.complete", "pass", "闊／轉速／排水／狀態齊"))

    return GateResult("cp2", worst(f.status for f in findings), tuple(findings))


def eval_cp3(rec: dict[str, Any]) -> GateResult:
    """Lifecycle filter: three failure modes + energy + drain + hardware checklist."""
    findings: list[Finding] = []

    grade = rec.get("energy_grade")
    if grade is None:
        findings.append(_finding("cp3.energy", "fail", "缺能源級"))
    elif grade <= 1:
        findings.append(_finding("cp3.energy", "pass", "能源 1 級"))
    elif grade == 2:
        findings.append(_finding("cp3.energy", "watch", "能源 2 級 — 可留 ALT，唔做主鎖"))
    else:
        findings.append(_finding("cp3.energy", "fail", f"能源 {grade} 級 — 決策關淘汰"))

    if rec.get("white_label"):
        findings.append(
            _finding("cp3.white_label", "fail", "假設二：白牌／雜牌零件鏈弱，唔入主線")
        )
    else:
        findings.append(_finding("cp3.white_label", "pass", "非白牌主線風險"))

    if rec.get("belt_risk"):
        findings.append(
            _finding("cp3.belt", "watch", "假設三：平價皮帶／防潮未確認 — 最多 ALT")
        )
    else:
        findings.append(_finding("cp3.belt", "pass", "未標皮帶傳動風險"))

    if rec.get("brand_premium_risk"):
        findings.append(
            _finding("cp3.brand_premium", "watch", "假設一：日系溢價 ≠ 更耐 — 規格對照，唔自動勝")
        )
    else:
        findings.append(_finding("cp3.brand_premium", "pass", "無「貴 = 更耐」誤用"))

    water = rec.get("water_l")
    if water is None:
        findings.append(_finding("cp3.water", "watch", "缺耗水"))
    elif water > WATER_WATCH_L:
        findings.append(_finding("cp3.water", "watch", f"標準耗水 {water:g} L > {WATER_WATCH_L} L"))
    else:
        findings.append(_finding("cp3.water", "pass", f"耗水 {water:g} L"))

    drain = rec.get("drain")
    if drain == "high_low":
        findings.append(_finding("cp3.drain", "pass", "高低一機"))
    elif drain == "high":
        findings.append(_finding("cp3.drain", "watch", "高排水 — 要屋企喉位確認"))
    else:
        findings.append(_finding("cp3.drain", "fail", "排水不明，唔能下單"))

    ss, damper = rec.get("stainless_drum"), rec.get("damper_lid")
    w_m, w_t = rec.get("warranty_machine_yr"), rec.get("warranty_motor_yr")
    hardware_ok = ss is True and damper is True and w_m == 2 and w_t == 5
    if hardware_ok:
        findings.append(_finding("cp3.hardware", "pass", "不銹鋼膽＋阻尼門＋2年／摩打5年"))
    elif rec.get("line") == "toshiba_q":
        findings.append(_finding("cp3.hardware", "watch", "Q 系硬件清單未齊"))
    else:
        findings.append(_finding("cp3.hardware", "watch", "不銹鋼／阻尼門／保用未全鎖"))

    if rec.get("line") == "toshiba_q" and (grade or 99) <= 1 and not rec.get("white_label"):
        findings.append(_finding("cp3.architecture", "pass", "東芝 Q 系波輪 — 零件流通架構命中"))
    elif rec.get("line", "").startswith("toshiba"):
        findings.append(_finding("cp3.architecture", "watch", "東芝但非現役 Q 系"))
    else:
        findings.append(_finding("cp3.architecture", "watch", "非東芝 Q 系 — 可做對照，唔做主鎖"))

    return GateResult("cp3", worst(f.status for f in findings), tuple(findings))


def _summarize(slug: str, overall: Status, gates: Iterable[GateResult]) -> str:
    flags = []
    for gate in gates:
        for f in gate.findings:
            if f.status != "pass":
                flags.append(f.message)
    if overall == "pass" and not flags:
        return "三關全過 — 可入主鎖排序"
    if not flags:
        return overall
    return "；".join(flags[:3])


def evaluate_model(rec: dict[str, Any]) -> ModelCheck:
    slug = rec["slug"]
    cp1 = eval_cp1(rec)
    cp2 = eval_cp2(rec)
    cp3 = eval_cp3(rec)
    overall = worst((cp1.status, cp2.status, cp3.status))
    return ModelCheck(
        slug=slug,
        cp1=cp1,
        cp2=cp2,
        cp3=cp3,
        overall=overall,
        summary=_summarize(slug, overall, (cp1, cp2, cp3)),
    )


def attach_meta(slug: str, rec: dict[str, Any]) -> dict[str, Any]:
    meta = META.get(slug, {})
    merged = dict(rec)
    for key, value in meta.items():
        merged.setdefault(key, value)
    return merged


if __name__ == "__main__":
    import build_db

    prices = build_db._prices_by_slug()
    print(f"{'slug':28} {'CP1':5} {'CP2':5} {'CP3':5} overall")
    for row in build_db.MODELS:
        rec = build_db.library_checkpoint_record(row, prices)
        check = evaluate_model(rec)
        print(f"{check.slug:28} {check.cp1.status:5} {check.cp2.status:5} {check.cp3.status:5} {check.overall}")
