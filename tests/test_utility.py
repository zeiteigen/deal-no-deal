import pytest

from dond_analysis.utility import UtilityModel


def model(points):
    return UtilityModel(
        {
            "schema_version": 1,
            "name": "test",
            "points": [{"cash_cents": x, "utility": y} for x, y in points],
        }
    )


def test_interpolation_and_leftmost_plateau():
    m = model([(0, 0), (10, 0.5), (20, 0.5), (30, 1)])
    assert m.evaluate(5) == 0.25
    assert m.evaluate(20) == 0.5
    assert m.certainty_equivalent(0.5) == 10
    assert m.certainty_equivalent(0.75) == 25
    assert m.certainty_equivalent(0) == 0


@pytest.mark.parametrize(
    "points", [[(0, 0), (0, 1)], [(0, 1), (1, 0)], [(0, 0), (1, float("nan"))]]
)
def test_invalid_models(points):
    with pytest.raises(ValueError):
        model(points)


def test_domain_errors():
    m = model([(0, 0), (10, 1)])
    with pytest.raises(ValueError):
        m.evaluate(-1)
    with pytest.raises(ValueError):
        m.certainty_equivalent(2)


def test_survey_and_seeded_verification(tmp_path, monkeypatch):
    import json

    from dond_analysis.calibration.survey import run_survey
    from dond_analysis.calibration.verify import run_verification

    path = tmp_path / "utility.json"
    monkeypatch.setattr("builtins.input", lambda _: "500000")
    document = run_survey(path, layers=1, seed=7)
    assert json.loads(path.read_text()) == document
    assert document["points"][1] == {"cash_cents": 50_000_000, "utility": 0.5}
    first = run_verification(path, seed=8)
    assert first == run_verification(path, seed=8)
    assert all(
        r["predicted_take"] == (r["comparison_utility"] >= r["expected_utility"]) for r in first
    )
    assert all(r["did_take"] is None for r in first)
    assert {r["predicted_take"] for r in first} == {True, False}
    with pytest.raises(FileExistsError):
        run_survey(path, layers=1, seed=7)


@pytest.mark.parametrize("answer", ["nan", "inf", "1000000000000000000000", "0", "abc"])
def test_survey_reprompts_after_invalid_answer(tmp_path, monkeypatch, answer):
    from dond_analysis.calibration.survey import run_survey

    answers = iter([answer, "$250,000.50"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    document = run_survey(tmp_path / "utility.json", layers=1, seed=7)
    assert document["points"][1] == {"cash_cents": 25_000_050, "utility": 0.5}


def test_survey_cancelled_without_output(tmp_path, monkeypatch):
    from dond_analysis.calibration.survey import run_survey

    def cancel(_):
        raise EOFError

    monkeypatch.setattr("builtins.input", cancel)
    path = tmp_path / "utility.json"
    with pytest.raises(EOFError):
        run_survey(path, layers=1, seed=7)
    assert not path.exists()


@pytest.mark.parametrize("cash", [-1, 4294967296])
def test_uint32_cash_domain(cash):
    with pytest.raises(ValueError, match="uint32"):
        model([(0, 0), (cash, 1)])


def test_verification_collects_decisions(tmp_path, monkeypatch):
    import json

    from dond_analysis.calibration.verify import run_verification

    path = tmp_path / "model.json"
    path.write_text(json.dumps(model([(0, 0), (1000, 1)]).document))
    answers = iter(["invalid", "yes", "no", "yes", "no", "yes"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    reports = run_verification(path, 1, interactive=True)
    assert [r["did_take"] for r in reports] == [True, False, True, False, True]
