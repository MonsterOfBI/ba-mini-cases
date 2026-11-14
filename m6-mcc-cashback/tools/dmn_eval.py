"""Мини-исполнитель таблиц решений DMN 1.3 для учебных проектов (без внешних библиотек).
Поддерживает: hit policy FIRST и UNIQUE, несколько решений в одном файле (вход одного = выход другого),
унарные тесты FEEL в простом виде: "-", 5, "текст", true/false, < 100, >= 0.5, [1..10], списки через запятую, not(...).
Для настоящих проектов есть полноценные движки (Camunda, Drools); здесь важно, чтобы таблицу можно было проверить тестом.

Пример:  from dmn_eval import evaluate
         evaluate("bpmn/cashback-rate.dmn", "cashbackRate", {"mcc": 5812, "amount": 700, "isChosen": True})
"""
import re
import xml.etree.ElementTree as ET

NS = {"d": "https://www.omg.org/spec/DMN/20191111/MODEL/"}


def _literal(tok):
    tok = tok.strip()
    if tok in ("true", "false"):
        return tok == "true"
    if tok.startswith('"') and tok.endswith('"'):
        return tok[1:-1]
    return float(tok)


def _split(expr):
    """Делит «5411, 5499» или «"a", "b"» по запятым вне кавычек и скобок."""
    parts, buf, depth, quote = [], "", 0, False
    for ch in expr:
        if ch == '"':
            quote = not quote
        if not quote and ch in "[(":
            depth += 1
        if not quote and ch in "])":
            depth -= 1
        if ch == "," and not quote and depth == 0:
            parts.append(buf); buf = ""
        else:
            buf += ch
    parts.append(buf)
    return [p.strip() for p in parts if p.strip()]


def _test(expr, value):
    expr = expr.strip()
    if expr in ("-", ""):
        return True
    if expr.startswith("not(") and expr.endswith(")"):
        return not _test(expr[4:-1], value)
    for part in _split(expr):
        m = re.fullmatch(r"(<=|>=|<|>)\s*(.+)", part)
        r = re.fullmatch(r"([\[\]])\s*(.+?)\s*\.\.\s*(.+?)\s*([\[\]])", part)
        if m:
            op, lit = m.group(1), _literal(m.group(2))
            if value is None:
                continue
            if {"<": value < lit, "<=": value <= lit, ">": value > lit, ">=": value >= lit}[op]:
                return True
        elif r:
            lo, hi = _literal(r.group(2)), _literal(r.group(3))
            lo_ok = value >= lo if r.group(1) == "[" else value > lo
            hi_ok = value <= hi if r.group(4) == "]" else value < hi
            if lo_ok and hi_ok:
                return True
        elif _literal(part) == value:
            return True
    return False


def evaluate(path, decision_id, context):
    """Возвращает словарь выходов решения decision_id. Зависимые решения считаются рекурсивно."""
    root = ET.parse(path).getroot()
    decisions = {d.get("id"): d for d in root.findall("d:decision", NS)}
    ctx = dict(context)
    dec = decisions[decision_id]
    for req in dec.findall("d:informationRequirement/d:requiredDecision", NS):
        dep = req.get("href").lstrip("#")
        ctx.update(evaluate(path, dep, ctx))
    table = dec.find("d:decisionTable", NS)
    policy = table.get("hitPolicy", "UNIQUE")
    inputs = [i.find("d:inputExpression/d:text", NS).text.strip() for i in table.findall("d:input", NS)]
    outputs = [o.get("name") for o in table.findall("d:output", NS)]
    hits = []
    for rule in table.findall("d:rule", NS):
        entries = [e.find("d:text", NS).text or "" for e in rule.findall("d:inputEntry", NS)]
        if all(_test(e, ctx.get(name)) for e, name in zip(entries, inputs)):
            outs = [_literal(o.find("d:text", NS).text) for o in rule.findall("d:outputEntry", NS)]
            hits.append(dict(zip(outputs, outs), _rule=rule.get("id")))
            if policy == "FIRST":
                break
    if not hits:
        raise ValueError(f"{decision_id}: ни одно правило не подошло для {ctx}")
    if policy == "UNIQUE" and len(hits) > 1:
        raise ValueError(f"{decision_id}: hit policy UNIQUE, но подошли правила {[h['_rule'] for h in hits]}")
    return hits[0]
