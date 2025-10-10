import pytest
from unittest.mock import patch, Mock
from server import tools

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