import pytest
from fastapi.testclient import TestClient
from server.mcp_server import app
import logging
import json

logger = logging.getLogger(__name__)
client = TestClient(app)

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