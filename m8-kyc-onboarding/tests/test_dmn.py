"""Тесты таблицы решений «Уровень проверки» (bpmn/kyc-check-level.dmn).
Запуск из корня репозитория:  python tests/test_dmn.py   (или pytest tests/)
"""
import itertools
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from dmn_eval import evaluate  # noqa: E402

DMN = ROOT / "bpmn" / "kyc-check-level.dmn"
CLEAN = dict(inLists=False, passportValid=True, egripStatus="active", zskGroup="low", dataMismatch=False, okvedWatch=False)


def level(**changes):
    return evaluate(DMN, "checkLevel", {**CLEAN, **changes})


def test_examples_from_requirements():
    # те же примеры, что в docs/requirements.md, раздел «Правила»
    cases = [
        ({}, "AUTO", "KYC-06"),                                            # чистая заявка, зелёная группа
        (dict(inLists=True), "REFUSE", "KYC-01"),
        (dict(inLists=True, zskGroup="low"), "REFUSE", "KYC-01"),          # перечень важнее зелёной группы
        (dict(passportValid=False), "REFUSE", "KYC-02"),
        (dict(egripStatus="ceased"), "REFUSE", "KYC-03"),
        (dict(zskGroup="high"), "REFUSE", "KYC-04"),
        (dict(dataMismatch=True), "MANUAL", "KYC-05"),                     # расхождение — даже у зелёной группы
        (dict(okvedWatch=True), "AUTO", "KYC-06"),                         # зелёная группа + «внимательный» ОКВЭД
        (dict(zskGroup="medium"), "MANUAL", "KYC-07"),
        (dict(zskGroup="none", okvedWatch=True), "MANUAL", "KYC-08"),
        (dict(zskGroup="none"), "AUTO", "KYC-09"),
        (dict(zskGroup="unknown"), "MANUAL", "KYC-10"),                    # новое значение справочника
    ]
    for changes, exp_level, exp_rule in cases:
        res = level(**changes)
        assert (res["level"], res["rule"]) == (exp_level, exp_rule), (changes, res)
    assert level(zskGroup="none")["postControl"] is True
    assert level()["postControl"] is False


def test_all_combinations_are_safe():
    """Перебираем все 192 комбинации входов: стоп-факторы 115-ФЗ всегда дают отказ,
    а зелёная группа без стоп-факторов и расхождений никогда не получает отказ."""
    for lists, passport, egrip, zsk, mismatch, watch in itertools.product(
            [False, True], [True, False], ["active", "ceased"], ["low", "medium", "high", "none"], [False, True], [False, True]):
        ctx = dict(inLists=lists, passportValid=passport, egripStatus=egrip, zskGroup=zsk, dataMismatch=mismatch, okvedWatch=watch)
        res = evaluate(DMN, "checkLevel", ctx)
        stop = lists or not passport or egrip == "ceased" or zsk == "high"
        if stop:
            assert res["level"] == "REFUSE", ctx
        else:
            assert res["level"] != "REFUSE", ctx
        if res["level"] == "AUTO":
            assert not mismatch and zsk in ("low", "none"), ctx


if __name__ == "__main__":
    test_examples_from_requirements()
    test_all_combinations_are_safe()
    print("OK: 2 теста пройдены")
