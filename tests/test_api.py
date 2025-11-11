import pytest
from fastapi.testclient import TestClient
from server.mcp_server import app
from unittest.mock import patch, Mock
import logging
import json

logger = logging.getLogger(__name__)
client = TestClient(app)

# ============================================================
#  SMOKE TESTS (Real API calls)
# ============================================================

@pytest.mark.smoke
def test_overlaps_endpoint_success():
    """Test the /overlaps endpoint with valid input"""
    payload = {
        "region": "chr8:127738881-127738920",
        "genome": "hg38",
        "track": "knownGene"
    }
    response = client.post("/overlaps", json=payload)
    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, dict)
    assert "knownGene" in data
    assert data["knownGene"][0]["chrom"] == "chr8"

    genes = data.get("knownGene", [])
    assert any(g.get("geneName") == "MYC" for g in genes), "Expected at least one gene with geneName == 'MYC'"

@pytest.mark.smoke
def test_species_endpoint_real():
    """
    Smoke test that calls the real UCSC API via /species.
    Verifies that known organisms like 'Homo sapiens' are present.
    """
    response = client.get("/species")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0

    species_names = [s["scientificName"] for s in data if "scientificName" in s]
    assert any("Homo sapiens" in s for s in species_names), "Expected Homo sapiens in UCSC species list"

    # sanity check: structure
    first = data[0]
    assert "assemblies" in first
    assert isinstance(first["assemblies"], list)
    assert "scientificName" in first

@pytest.mark.smoke
def test_assemblies_endpoint_real_exact_match():
    """
    Smoke test that retrieves real assemblies for 'Homo sapiens'.
    Ensures that hg38 or GRCh38 is present among assemblies.
    """
    response = client.get("/assemblies/Homo%20sapiens")
    assert response.status_code == 200

    data = response.json()
    assert "matched_species" in data
    assert data["matched_species"] == "Homo sapiens"

    assemblies = data.get("assemblies", [])
    assert isinstance(assemblies, list)
    assert any("hg38" in a.get("assemblyName", "") or "GRCh38" in a.get("assemblyName", "") for a in assemblies), \
        "Expected hg38/GRCh38 in Homo sapiens assemblies"
    
@pytest.mark.smoke
def test_assemblies_endpoint_real_fuzzy_match():
    """
    Smoke test that retrieves assemblies using a fuzzy species name (case-insensitive, partial).
    For example, 'mouse' should resolve to 'Mus musculus'.
    """
    response = client.get("/assemblies/mouse")
    assert response.status_code == 200

    data = response.json()
    assert "matched_species" in data
    assert data["matched_species"] == "Mus musculus"

    assemblies = data.get("assemblies", [])
    assert isinstance(assemblies, list)
    assert len(assemblies) > 0
    
# ============================================================
#  MOCK TESTS (Mocked API calls)
# ============================================================


def test_overlaps_endpoint_missing_field():
    """Test /overlaps endpoint with missing required field"""
    payload = {
        "region": "chr1:1000-2000",
        # missing 'genome' field
    }
    response = client.post("/overlaps", json=payload)
    assert response.status_code == 422
    # Check that the error message mentions the missing field
    assert "genome" in str(response.json())

def test_assemblies_endpoint_not_implemented():
    """Optional: if you later add a /assemblies endpoint"""
    response = client.get("/assemblies")
    assert response.status_code == 404  # not implemented yet

@patch("server.ucsc_rest.fetch_ucsc_genomes")
def test_species_endpoint_returns_species(mock_fetch):
    """Test that /species returns a valid list of species"""
    mock_fetch.return_value = [
        {
            "speciesKey": "Homo sapiens",
            "scientificName": "Homo sapiens",
            "commonName": "Human",
            "count": 2,
            "assemblies": [
                {"genome": "hg19", "assemblyName": "Feb. 2009 (GRCh37/hg19)"},
                {"genome": "hg38", "assemblyName": "Dec. 2013 (GRCh38/hg38)"},
            ],
        },
        {
            "speciesKey": "Mus musculus",
            "scientificName": "Mus musculus",
            "commonName": "Mouse",
            "count": 1,
            "assemblies": [
                {"genome": "mm10", "assemblyName": "Dec. 2011 (GRCm38/mm10)"},
            ],
        },
    ]

    response = client.get("/species")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2

    human = next(s for s in data if s["scientificName"] == "Homo sapiens")
    assert human["commonName"] == "Human"
    assert len(human["assemblies"]) == 2

@patch("server.ucsc_rest.fetch_ucsc_genomes")
def test_assemblies_endpoint_exact_match(mock_fetch):
    """Test /assemblies/{species_name} returns correct assemblies for exact match"""
    mock_fetch.return_value = [
        {
            "speciesKey": "Homo sapiens",
            "scientificName": "Homo sapiens",
            "commonName": "Human",
            "assemblies": [{"genome": "hg38", "assemblyName": "Dec. 2013 (GRCh38/hg38)"}],
        }
    ]

    response = client.get("/assemblies/Homo%20sapiens")
    assert response.status_code == 200

    data = response.json()
    assert "matched_species" in data
    assert data["matched_species"] == "Homo sapiens"
    assert data["assemblies"][0]["genome"] == "hg38"

@patch("server.ucsc_rest.fetch_ucsc_genomes")
def test_assemblies_endpoint_fuzzy_match(mock_fetch):
    """Test /assemblies/{species_name} returns partial match results (case-insensitive)"""
    mock_fetch.return_value = [
        {
            "speciesKey": "Mus musculus",
            "scientificName": "Mus musculus",
            "commonName": "Mouse",
            "assemblies": [{"genome": "mm10", "assemblyName": "Dec. 2011 (GRCm38/mm10)"}],
        }
    ]

    # Fuzzy search for "musc" should match "Mus musculus"
    response = client.get("/assemblies/musc?exact=false")
    assert response.status_code == 200
    data = response.json()

    assert data["matched_species"] == "Mus musculus"
    assert data["assemblies"][0]["genome"] == "mm10"

@patch("server.ucsc_rest.fetch_ucsc_genomes")
def test_assemblies_endpoint_no_match(mock_fetch):
    """Test /assemblies/{species_name} returns error message when species not found"""
    mock_fetch.return_value = [
        {
            "speciesKey": "Homo sapiens",
            "scientificName": "Homo sapiens",
            "commonName": "Human",
            "assemblies": [{"genome": "hg38", "assemblyName": "GRCh38"}],
        }
    ]

    response = client.get("/assemblies/banana")
    assert response.status_code == 200

    data = response.json()
    assert "error" in data
    assert "No assemblies found" in data["error"]