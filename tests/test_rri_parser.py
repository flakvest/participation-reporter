from app.rri_parser import parse_strip, parse_text


def test_parse_valid_1plt():
    strip = "1PLTPARTRPT/AAR4LJ/JAN/YES/YES/12/5/3/2/22/Additional training needed"
    values, errors = parse_strip(strip)
    assert errors == []
    assert values is not None
    assert values[0] == "AAR4LJ"
    assert values[1] == "JAN"
    assert values[2] == "YES"
    assert values[3] == "YES"
    assert values[4] == "12"
    assert values[5] == "5"
    assert values[6] == "3"
    assert values[7] == "2"
    assert values[8] == "22"
    assert values[9] == "Additional training needed"


def test_parse_valid_2plt():
    strip = "2PLTPARTRPT/AAR4XX/DEC/YES/NO/8/2/1/1/12/None"
    values, errors = parse_strip(strip)
    assert errors == []
    assert values is not None
    assert values[0] == "AAR4XX"
    assert values[1] == "DEC"
    assert values[2] == "YES"
    assert values[3] == "NO"


def test_parse_invalid_set_id():
    strip = "UNKNOWN/AAR4LJ/JAN/YES/YES/12/5/3/2/22/Notes"
    values, errors = parse_strip(strip)
    assert values is None
    assert any("Unknown set identifier" in e for e in errors)


def test_parse_wrong_field_count():
    strip = "1PLTPARTRPT/AAR4LJ/JAN/YES/YES/12"
    values, errors = parse_strip(strip)
    assert values is None
    assert any("Expected 10 fields" in e for e in errors)


def test_parse_invalid_month():
    strip = "1PLTPARTRPT/AAR4LJ/XYZ/YES/YES/12/5/3/2/22/Notes"
    values, errors = parse_strip(strip)
    assert values is None
    assert any("Month" in e for e in errors)


def test_parse_invalid_yes_no():
    strip = "1PLTPARTRPT/AAR4LJ/JAN/MAYBE/YES/12/5/3/2/22/Notes"
    values, errors = parse_strip(strip)
    assert values is None
    assert any("Equipment" in e for e in errors)


def test_parse_numeric_field():
    strip = "1PLTPARTRPT/AAR4LJ/JAN/YES/YES/abc/5/3/2/22/Notes"
    values, errors = parse_strip(strip)
    assert values is None
    assert any("numeric" in e.lower() for e in errors)


def test_parse_multiple_strips():
    text = "1PLTPARTRPT/AAR4LJ/JAN/YES/YES/12/5/3/2/22/Notes//2PLTPARTRPT/AAR4XX/FEB/YES/NO/8/4/2/1/15/More notes//"
    results = parse_text(text)
    assert len(results) == 2
    r1, e1 = results[0]
    r2, e2 = results[1]
    assert r1 is not None and r1.callsign == "AAR4LJ" and r1.month == "JAN"
    assert r2 is not None and r2.callsign == "AAR4XX" and r2.month == "FEB"


def test_parse_mixed_valid_and_invalid():
    text = "1PLTPARTRPT/AAR4LJ/JAN/YES/YES/12/5/3/2/22/Notes//BADSTUFF/AAA//"
    results = parse_text(text)
    assert len(results) == 2
    r1, e1 = results[0]
    r2, e2 = results[1]
    assert r1 is not None
    assert r2 is None
    assert any("Unknown set identifier" in e for e in e2)


def test_parse_empty():
    results = parse_text("")
    assert len(results) == 1
    r, e = results[0]
    assert r is None
