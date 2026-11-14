"""Тесты правил кэшбэка: таблица решений DMN даёт те же результаты, что и справочник MCC в базе.
Запуск из корня репозитория:  python tests/test_rules.py   (или pytest tests/)
"""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from dmn_eval import evaluate  # noqa: E402

DMN = ROOT / "bpmn" / "cashback-rate.dmn"


def rate(mcc, amount, chosen):
    return evaluate(DMN, "cashbackRate", {"mcc": mcc, "amount": amount, "isChosen": chosen})


def test_examples_from_requirements():
    # (MCC, сумма, выбрана ли категория, ожидаемая ставка, правило) — те же примеры, что в docs/rules.md
    cases = [
        (6011, 5000, False, 0, "CB-01"),     # снятие наличных
        (4829, 20000, True, 0, "CB-01"),     # перевод: исключён, даже если что-то выбрано
        (4900, 5200, False, 0, "CB-01"),     # ЖКУ
        (5812, 99, True, 0, "CB-02"),        # кофе за 99 ₽ в выбранной категории — всё равно 0
        (5812, 700, True, 0.05, "CB-03"),    # кафе, категория выбрана
        (5812, 700, False, 0.01, "CB-04"),   # кафе, категория не выбрана
        (5411, 1500, True, 0.03, "CB-03"),   # супермаркет — повышенная 3 %, а не 5 %
        (5732, 30000, True, 0.01, "CB-04"),  # электронику нельзя выбрать повышенной
        (7299, 1000, False, 0.01, "CB-04"),  # MCC не из справочника — базовый кэшбэк
    ]
    for mcc, amount, chosen, exp_rate, exp_rule in cases:
        res = rate(mcc, amount, chosen)
        assert (res["rate"], res["rule"]) == (exp_rate, exp_rule), (mcc, amount, chosen, res)


def test_dmn_matches_mcc_reference():
    """Каждый MCC из data/mcc_groups.csv: группа и ставка по DMN = по справочнику."""
    with open(ROOT / "data" / "mcc_groups.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            mcc = int(row["mcc"])
            assert evaluate(DMN, "mccGroup", {"mcc": mcc})["group"] == row["group_code"], mcc
            excluded = row["is_excluded"] == "True"
            elevated = float(row["elevated_rate"]) if row["elevated_rate"] else None
            for chosen in (True, False):
                expected = 0 if excluded else (elevated if chosen and elevated else 0.01)
                assert rate(mcc, 1000, chosen)["rate"] == expected, (mcc, chosen)


if __name__ == "__main__":
    test_examples_from_requirements()
    test_dmn_matches_mcc_reference()
    print("OK: 2 теста пройдены")
