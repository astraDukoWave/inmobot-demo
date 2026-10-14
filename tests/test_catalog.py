import pytest

from app.catalog import AmbiguousAmountError


def test_demo_query_returns_only_cholula_houses_within_budget(catalog):
    result = catalog.search(zone="Cholula", max_price=2_500_000, min_bedrooms=3, property_type="casa")
    assert [p.id for p in result.matches] == [4, 5]
    assert all(p.price_mxn <= 2_500_000 and p.bedrooms >= 3 for p in result.matches)


def test_zone_aliases_and_accents(catalog):
    assert catalog.normalize_zone("angelopolis") == "Angelópolis"
    assert catalog.normalize_zone("San Andrés Cholula") == "Cholula"
    assert catalog.normalize_zone("Atlixco") is None


@pytest.mark.parametrize("amount", [3, 2.5, 99_999])
def test_ambiguous_amounts_are_rejected(catalog, amount):
    with pytest.raises(AmbiguousAmountError):
        catalog.search(zone="Cholula", max_price=int(amount))


def test_no_exact_match_returns_declared_alternatives(catalog):
    result = catalog.search(zone="Centro", max_price=3_000_000, min_bedrooms=4)
    assert result.matches == []
    assert result.alternatives and result.relaxed[0] == "recámaras"
    assert all(p.zone == "Centro" for p in result.alternatives)
