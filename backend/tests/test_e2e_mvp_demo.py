import pytest

from tools.e2e_mvp_demo import parse_scenarios, render_output


def test_parse_scenarios_parses_pairs():
    scenarios = parse_scenarios(["emp-1|منو", "sup-1|مشاهده افراد یک روز"])

    assert scenarios == [("emp-1", "منو"), ("sup-1", "مشاهده افراد یک روز")]


def test_parse_scenarios_rejects_invalid_format():
    with pytest.raises(ValueError):
        parse_scenarios(["invalid-scenario"])


def test_render_output_serializes_json():
    output = render_output([{"status": 200}], [{"path": "/send"}])

    assert '"status": 200' in output
    assert '"/send"' in output
