from pathlib import Path

import pytest
from solcx import compile_standard, install_solc

CONTRACT_PATH = Path(__file__).resolve().parent.parent / "contracts" / "KPIFactory.sol"
SOLC_VERSION = "0.8.20"

EXPECTED_TICKERS = {
    "PYLD",
    "EPDX",
    "DRAX",
    "LLOX",
    "CDLX",
    "ALIX",
    "SPVX",
    "DTPX",
    "SCEX",
    "CJEX",
    "RRYX",
    "LEVX",
    "OEVX",
    "PDMX",
    "IDRX",
    "SSPX",
    "TRUX",
    "QLTX",
    "CVRX",
    "STBX",
    "SAFE",
    "COST",
    "RETX",
    "ERRX",
    "UPTX",
    "PRFX",
    "VLTX",
    "AUCX",
    "HUMX",
    "EVDX",
}


@pytest.fixture(scope="module")
def contract_source() -> str:
    return CONTRACT_PATH.read_text()


@pytest.fixture(scope="module")
def compiled_contracts(contract_source):
    install_solc(SOLC_VERSION)
    compiled = compile_standard(
        {
            "language": "Solidity",
            "sources": {"KPIFactory.sol": {"content": contract_source}},
            "settings": {
                "outputSelection": {
                    "*": {"*": ["abi", "evm.bytecode", "metadata"]}
                }
            },
        },
        solc_version=SOLC_VERSION,
    )
    return compiled["contracts"]["KPIFactory.sol"]


def test_seeded_kpis_match_expected(contract_source):
    invocations = [line for line in contract_source.splitlines() if "_registerKPI(" in line]
    tickers = {
        line.split('"')[3]
        for line in invocations
        if line.count('"') >= 4
    }
    assert tickers == EXPECTED_TICKERS


def test_registry_interface(compiled_contracts):
    abi = compiled_contracts["KPIRegistry"]["abi"]
    functions = {entry["name"] for entry in abi if entry.get("type") == "function"}
    expected = {
        "totalKPIs",
        "listKPIIds",
        "getKPIMetadata",
        "getKPIValue",
        "setAuthorizedMinter",
        "setEmissionsCollector",
        "updateEmissionMultiplier",
        "updateKPI",
        "mintForAppraisal",
        "deactivateKPI",
        "reactivateKPI",
        "isRegistered",
    }
    assert expected <= functions


def test_router_and_index_interfaces(compiled_contracts):
    router_functions = {
        entry["name"]
        for entry in compiled_contracts["AppraisalRouter"]["abi"]
        if entry.get("type") == "function"
    }
    assert {"setAppraiser", "appraise", "registry", "promptNFT", "baseUnit"} <= router_functions

    index_functions = {
        entry["name"]
        for entry in compiled_contracts["CompositeIndex"]["abi"]
        if entry.get("type") == "function"
    }
    assert {"setWeights", "indexValue", "components", "registry"} <= index_functions


def test_prompt_nft_has_mint_and_burn(compiled_contracts):
    abi = compiled_contracts["PromptNFT"]["abi"]
    functions = {entry["name"] for entry in abi if entry.get("type") == "function"}
    assert {"mint", "burn", "ownerOf", "exists", "transferFrom"} <= functions
