from pathlib import Path

from qedra.adapters.ingest import load_architecture
from qedra.adapters.ingest.arm import load_arm_template

ARM = Path(__file__).parents[2] / "examples" / "contoso-arm" / "azuredeploy.json"


def test_arm_parses_vnet_and_subnets() -> None:
    arch = load_arm_template(ARM)
    subnets = {s.name: s for s in arch.network.subnets()}
    assert "snet-data" in subnets
    assert subnets["snet-data"].address_prefix == "10.0.3.0/24"


def test_arm_infers_data_tier() -> None:
    arch = load_arm_template(ARM)
    data = arch.network.subnets_in_tier("data")
    assert [s.name for s in data] == ["snet-data"]


def test_arm_resolves_nsg_and_rule() -> None:
    arch = load_arm_template(ARM)
    data = arch.network.subnets_in_tier("data")[0]
    assert data.nsg is not None
    names = {r.name for r in data.nsg.rules}
    assert "AllowSqlFromInternet" in names


def test_dispatch_detects_arm_by_schema() -> None:
    arch = load_architecture(ARM.parent)
    assert arch.network.subnets_in_tier("data")
