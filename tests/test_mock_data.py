from src.mock_data import generate_prices, MARKETS

def test_generates_correct_hours():
    data = generate_prices(24)
    assert len(data) == 24

def test_all_markets_present():
    data = generate_prices(1)
    prices = data[0]["prices"]
    for market in MARKETS.keys():
        assert market in prices

def test_de_nl_correlation():
    data = generate_prices(50)

    de_changes = []
    nl_changes = []

    for i in range(1, len(data)):
        de_diff = data[i]["prices"]["DE"] - data[i-1]["prices"]["DE"]
        nl_diff = data[i]["prices"]["NL"] - data[i-1]["prices"]["NL"]
        de_changes.append(de_diff)
        nl_changes.append(nl_diff)

    same_direction = sum(1 for de, nl in zip(de_changes, nl_changes) if de * nl > 0)
    correlation_rate = same_direction / len(de_changes)

    assert correlation_rate > 0.6

def test_peak_higher_than_offpeak():
    data = generate_prices(24)

    offpeak = [data[h]["prices"]["DE"] for h in [2, 3, 4]]
    peak = [data[h]["prices"]["DE"] for h in [10, 11, 12]]

    avg_offpeak = sum(offpeak) / len(offpeak)
    avg_peak = sum(peak) / len(peak)

    assert avg_peak > avg_offpeak

def test_mean_reversion():
    data = generate_prices(100)

    de_prices = [entry["prices"]["DE"] for entry in data]
    avg_price = sum(de_prices) / len(de_prices)

    assert 60 < avg_price < 110

if __name__ == "__main__":
    test_generates_correct_hours()
    print("✓ Generates correct hours")

    test_all_markets_present()
    print("✓ All markets present")

    test_de_nl_correlation()
    print("✓ DE-NL correlation works")

    test_peak_higher_than_offpeak()
    print("✓ Peak hours higher than off-peak")

    test_mean_reversion()
    print("✓ Mean reversion keeps prices realistic")

    print("\nAll tests passed!")
