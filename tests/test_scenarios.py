"""Scenarios as data (README roadmap item 47): TOML files, validated keys."""
import pytest

from ukabm import SCENARIOS, GBMarketModel, get_scenario
from ukabm.scenarios import BENCHMARKS, SCENARIO_KEYS, load_scenarios, validate


def test_builtin_scenarios_load_and_validate():
    assert set(SCENARIOS) == {"baseline", "high_carbon", "no_cfd", "heat_push", "no_capacity_market", "high_gas"}
    assert SCENARIOS["baseline"] == {}
    assert SCENARIOS["high_carbon"] == {"policy": {"carbon_price_2050": 300.0}}
    assert SCENARIOS["no_cfd"]["policy"]["cfd_enabled"] is False
    assert BENCHMARKS["competitive_benchmark"]["max_merchant_decisions"] == 40
    for sc in list(SCENARIOS.values()) + list(BENCHMARKS.values()):
        assert validate(sc) is sc


def test_get_scenario_returns_a_copy():
    a = get_scenario("high_gas")
    a["fuels"]["gas_adder"] = 99.0
    assert get_scenario("high_gas")["fuels"]["gas_adder"] == 15.0
    with pytest.raises(KeyError, match="unknown scenario"):
        get_scenario("no_such_scenario")


def test_unknown_keys_are_errors():
    with pytest.raises(ValueError, match="unknown scenario key"):
        GBMarketModel({"decison_logic": "expectations"}, end=2025, network_every=0)   # misspelt
    with pytest.raises(ValueError, match=r"scenario\['policy'\]"):
        validate({"policy": {"carbon_price_2051": 300.0}})
    with pytest.raises(ValueError, match=r"scenario\['fuels'\]"):
        validate({"fuels": {"gas_addr": 1.0}})
    with pytest.raises(ValueError, match=r"scenario\['reserve'\]"):
        validate({"reserve": {"scal": 0}})


def test_every_key_the_model_reads_is_declared():
    """Each scenario key read anywhere in the package is in SCENARIO_KEYS (and so documented)."""
    import pathlib
    import re
    src = "\n".join(p.read_text(encoding="utf-8") for p in pathlib.Path("ukabm").glob("*.py"))
    read = set(re.findall(r'scenario\.get\("([a-z_0-9]+)"', src)) | set(re.findall(r'scenario\["([a-z_0-9]+)"\]', src))
    assert read <= set(SCENARIO_KEYS), sorted(read - set(SCENARIO_KEYS))


def test_user_file_with_year_keys(tmp_path):
    f = tmp_path / "mine.toml"
    f.write_text('[scenarios.cheap_gas.fuels.gas_path]\n"2025" = 30.0\n"2050" = 20.0\n', encoding="utf-8")
    sc = get_scenario("cheap_gas", file=f)
    assert sc == {"fuels": {"gas_path": {2025: 30.0, 2050: 20.0}}}
    m = GBMarketModel(sc, end=2025, network_every=0)
    assert m.fuels.gas(2030) == pytest.approx(28.0)
    f.write_text("[scenarios.bad]\nnot_a_key = 1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="scenario 'bad'"):
        load_scenarios(f)
