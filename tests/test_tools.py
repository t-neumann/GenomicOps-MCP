import pytest
from unittest.mock import patch, Mock, mock_open
from server import tools
import os, json, time

def test_parse_region_valid():
    chrom, start, end = tools.parse_region("chr1:1000-2000")
    assert chrom == "chr1"
    assert start == 1000
    assert end == 2000

def test_parse_region_invalid():
    with pytest.raises(ValueError):
        tools.parse_region("invalid_region")

@patch("server.tools.requests.get")
def test_get_annotations_basic(mock_get):
    # Mock the HTTP response
    mock_response = Mock()
    mock_response.json.return_value = {"knownGene": [{"chrom": "chr1"}]}
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    result = tools.get_annotations("chr1:1000-2000", genome="hg38", track="knownGene")
    assert isinstance(result, dict)
    assert "knownGene" in result
    assert result["knownGene"][0]["chrom"] == "chr1"

@patch("server.tools.requests.get")
def test_get_annotations_invalid_region(mock_get):
    # Should raise ValueError because parse_region fails
    with pytest.raises(ValueError):
        tools.get_annotations("chr1:abc-def", genome="hg38", track="knownGene")

@patch("server.tools.requests.get")
def test_get_annotations_api_returns_invalid_json(mock_get):
    # Simulate invalid JSON from server
    mock_response = Mock()
    mock_response.json.side_effect = ValueError("Invalid JSON")
    mock_response.text = "Invalid text"
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    result = tools.get_annotations("chr1:1000-2000", genome="hg38", track="knownGene")
    assert isinstance(result, dict)
    assert "error" in result
    assert "No valid JSON returned" in result["error"]

SAMPLE_API_RESPONSE = {
    "ucscGenomes": {
        "hg38": {"scientificName": "Homo sapiens", "organism": "Human", "description": "GRCh38/hg38"},
        "mm10": {"scientificName": "Mus musculus", "organism": "Mouse", "description": "GRCm38/mm10"}
    }
}

def test_extract_ucsc_genomes():
    genomes = tools.extract_ucsc_genomes(SAMPLE_API_RESPONSE)
    assert isinstance(genomes, list)
    assert len(genomes) == 2
    human = next(g for g in genomes if g["scientificName"] == "Homo sapiens")
    assert human["commonName"] == "Human"
    assert human["assemblies"][0]["genome"] == "hg38"
    assert human["assemblies"][0]["assemblyName"] == "GRCh38/hg38"

@patch("server.tools.requests.get")
def test_fetch_ucsc_genomes_with_corrupted_cache(mock_get, tmp_path):
    cache_file = tmp_path / "cache.json"
    cache_file.write_text("{ this is not valid JSON ")

    # Mock API response
    mock_resp = Mock()
    mock_resp.json.return_value = SAMPLE_API_RESPONSE
    mock_resp.raise_for_status = Mock()
    mock_get.return_value = mock_resp

    # Override CACHE_FILE
    tools.CACHE_FILE = cache_file

    # Fetch with use_cache=True should ignore corrupted cache and get fresh data
    genomes = tools.fetch_ucsc_genomes(timeout=1, use_cache=True)

    assert isinstance(genomes, list)
    assert any(g["scientificName"] == "Homo sapiens" for g in genomes)
    # Cache should be overwritten with valid JSON
    with open(cache_file) as f:
        cached_data = json.load(f)
    assert cached_data == genomes

@patch("server.tools.requests.get")
def test_fetch_ucsc_genomes_without_cache(mock_get, tmp_path):
    # Prepare mock API response
    mock_resp = Mock()
    mock_resp.json.return_value = SAMPLE_API_RESPONSE
    mock_resp.raise_for_status = Mock()
    mock_get.return_value = mock_resp

    tools.CACHE_FILE = tmp_path / "cache.json"

    genomes = tools.fetch_ucsc_genomes(timeout=1, use_cache=True)
    assert isinstance(genomes, list)
    assert (tmp_path / "cache.json").exists()

    mock_get.reset_mock()
    genomes2 = tools.fetch_ucsc_genomes(timeout=1, use_cache=True)
    assert genomes2 == genomes
    mock_get.assert_not_called()

def test_get_species():
    genomes = tools.extract_ucsc_genomes(SAMPLE_API_RESPONSE)
    species = tools.get_species(genomes)
    assert isinstance(species, list)
    human = next(s for s in species if s["scientificName"] == "Homo sapiens")
    assert human["commonName"] == "Human"
    assert len(human["assemblies"]) == 1

def test_get_assemblies_exact_and_fuzzy():
    genomes = tools.extract_ucsc_genomes(SAMPLE_API_RESPONSE)

    # Exact match scientificName
    res = tools.get_assemblies("Homo sapiens", genomes, exact=True)
    assert res["matched_species"] == "Homo sapiens"
    assert len(res["assemblies"]) == 1

    # Exact match commonName
    res = tools.get_assemblies("Mouse", genomes, exact=True)
    assert res["matched_species"] == "Mus musculus"

    # Fuzzy match
    res = tools.get_assemblies("homo", genomes, exact=False)
    assert res["matched_species"] == "Homo sapiens"

    # Not found
    res = tools.get_assemblies("unknown", genomes)
    assert "error" in res

# ============================================================
#  SMOKE TESTS (API calls)
# ============================================================

@pytest.mark.smoke
def test_get_annotations_real():
    """
    Smoke test that calls the real UCSC API.
    Verifies that we can get annotations for a known region.
    """
    region = "chr8:127735433-127740477"
    genome = "hg38"
    track = "knownGene"

    result = tools.get_annotations(region, genome, track)
    
    assert isinstance(result, dict)
    assert "knownGene" in result

    myc_genes = [g for g in result["knownGene"] if g.get("geneName") == "MYC"]
    assert len(myc_genes) > 0, "No gene named 'MYC' found in the region"

@pytest.mark.smoke
def test_fetch_ucsc_genomes_real():
    genomes = tools.fetch_ucsc_genomes(timeout=10, use_cache=False)
    assert isinstance(genomes, list)
    assert all("scientificName" in g for g in genomes)