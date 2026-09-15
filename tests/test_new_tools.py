"""Tests des nouveaux outils Ei : calculer, rappeler, ha_get_state, trio PDF."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_calculer_basic():
    from tools.calculator import calculer
    r = calculer("2*(3+4)")
    assert r["data"]["result"] == 14, r
    assert "speech" in r
    r2 = calculer("10 / 4 + 2 ** 3 - abs(-5)")
    assert r2["data"]["result"] == 10 / 4 + 2 ** 3 - abs(-5), r2
    r3 = calculer("min(3, 1, 2) + max(1, 9) + round(2.5)")
    assert r3["data"]["result"] == min(3, 1, 2) + max(1, 9) + round(2.5), r3


def test_calculer_injection_refused():
    from tools.calculator import calculer
    for expr in [
        "__import__('os').system('echo hacked')",
        "open('/etc/passwd').read()",
        "[x for x in range(3)]",
        "(lambda: 1)()",
        "{'a': 1}",
        "__class__",
    ]:
        r = calculer(expr)
        assert "error" in r["data"], f"injection acceptée : {expr} -> {r}"


def test_parse_delai():
    from tools.reminders import parse_delai
    assert parse_delai("10s") == 10
    assert parse_delai("5m") == 300
    assert parse_delai("2h") == 7200
    for bad in ["abc", "10", "5d", "", "1.5h", "-3s", "m10"]:
        try:
            parse_delai(bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"délai invalide accepté : {bad!r}")


def test_rappeler_invalid_delai():
    from tools.reminders import rappeler
    r = rappeler("test", "demain")
    assert "error" in r["data"], r


def test_rappeler_ok_with_fake_scheduler():
    import core.scheduler as sched_mod
    from tools.reminders import rappeler

    calls = {}

    class FakeScheduler:
        def add_reminder(self, message, delay_seconds, label="Rappel"):
            calls["message"] = message
            calls["delay_seconds"] = delay_seconds
            calls["label"] = label
            return "rem_fake_123"

    real = sched_mod.Scheduler
    sched_mod.Scheduler = FakeScheduler
    try:
        r = rappeler("prendre le pain", "5m")
    finally:
        sched_mod.Scheduler = real
    assert r["data"]["id"] == "rem_fake_123", r
    assert calls == {"message": "prendre le pain", "delay_seconds": 300, "label": "Rappel"}, calls


def test_ha_get_state_not_configured():
    import tools.home_assistant as ha
    old_url, old_tok = ha.HA_URL, ha.HA_TOKEN
    ha.HA_URL, ha.HA_TOKEN = "", ""
    try:
        r = ha.ha_get_state("light.salon")
    finally:
        ha.HA_URL, ha.HA_TOKEN = old_url, old_tok
    assert r["data"] == {"configured": False}, r
    assert r["speech"] == "Home Assistant n'est pas configuré dans le fichier d'environnement.", r


def _make_pdf(path, n):
    from pypdf import PdfWriter
    w = PdfWriter()
    for _ in range(n):
        w.add_blank_page(width=200, height=200)
    with open(path, "wb") as f:
        w.write(f)


def test_pdf_trio():
    from pypdf import PdfReader
    from tools.documents import lire_pdf, fusionner_pdfs, diviser_pdf, _parse_page_spec
    tmp = tempfile.mkdtemp()
    src = os.path.join(tmp, "src.pdf")
    _make_pdf(src, 3)

    r = lire_pdf(src)
    assert r["data"]["pages_total"] == 3, r
    assert r["data"]["pages_lues"] == 3, r

    assert _parse_page_spec("1-3,7", 10) == [0, 1, 2, 6]
    try:
        _parse_page_spec("9", 3)
    except ValueError:
        pass
    else:
        raise AssertionError("page hors limites acceptée")

    src2 = os.path.join(tmp, "src2.pdf")
    _make_pdf(src2, 2)
    merged = os.path.join(tmp, "merged.pdf")
    m = fusionner_pdfs([src, src2], merged)
    assert "sortie" in m["data"], m
    assert len(PdfReader(merged).pages) == 5, m

    part = os.path.join(tmp, "part.pdf")
    d = diviser_pdf(src, "1-2", part)
    assert d["data"]["pages_extraites"] == 2, d
    assert len(PdfReader(part).pages) == 2

    bad = diviser_pdf(src, "9", os.path.join(tmp, "bad.pdf"))
    assert "error" in bad["data"], bad


if __name__ == "__main__":
    test_calculer_basic()
    print("calculer basic OK")
    test_calculer_injection_refused()
    print("calculer injection OK")
    test_parse_delai()
    print("delai parser OK")
    test_rappeler_invalid_delai()
    print("rappeler invalid OK")
    test_rappeler_ok_with_fake_scheduler()
    print("rappeler ok OK")
    test_ha_get_state_not_configured()
    print("ha_get_state OK")
    test_pdf_trio()
    print("pdf trio OK")
    print("ALL NEW TOOLS TESTS PASSED")
