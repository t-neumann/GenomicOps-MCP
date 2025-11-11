# tests/test_mcp.py
import pytest
from unittest.mock import patch, Mock
from fastmcp.client import Client
from server.mcp_server import mcp
import json
import logging

logger = logging.getLogger(__name__)

# ============================================================
#  UNIT TESTS (Mocked UCSC API)
# ============================================================

@pytest.mark.asyncio
@patch('server.ucsc_rest.requests.get')
async def test_get_overlapping_features_tool_basic(mock_get):
    """Unit test: verify MCP server works with mocked UCSC response."""
    # Mock UCSC API response
    mock_response = Mock()
    mock_response.json.return_value = {
        "knownGene": [
            {"chrom": "chr1", "txStart": 1000, "txEnd": 2000, "name": "TEST_GENE"}
        ]
    }
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    async with Client(mcp) as client:

        tools = await client.list_tools()
        tool_names = [t.name for t in tools]
        assert "get_overlapping_features" in tool_names

        # Call get_overlapping_features
        result = await client.call_tool(
            "get_overlapping_features",
            arguments={
                "region": "chr1:1000-2000",
                "assembly": "hg38",
                "track": "knownGene"
            },
        )

        assert result is not None
        assert not result.is_error

        data = json.loads(result.output if hasattr(result, "output") else result.content[0].text)
        assert isinstance(data, dict)
        assert "knownGene" in data
        assert data["knownGene"][0]["chrom"] == "chr1"

@pytest.mark.asyncio
@patch('server.ucsc_rest.requests.get')
async def test_get_overlapping_features_tool_edge_case(mock_get):
    """Unit test: handle empty UCSC result gracefully."""
    mock_response = Mock()
    mock_response.json.return_value = {"knownGene": []}
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    async with Client(mcp) as client:
        result = await client.call_tool(
            "get_overlapping_features",
            arguments={"region": "chr1:0-1", "assembly": "hg38"},
        )

        assert result is not None
        assert not result.is_error

        data = json.loads(result.output if hasattr(result, "output") else result.content[0].text)
        assert "knownGene" in data

@pytest.mark.asyncio
@patch('server.ucsc_rest.requests.get')
async def test_get_overlapping_features_tool_invalid_region(mock_get):
    """Unit test: invalid region should raise exception."""
    mock_get.side_effect = Exception("Invalid region")

    async with Client(mcp) as client:
        with pytest.raises(Exception):
            await client.call_tool(
                "get_overlapping_features",
                arguments={"region": "invalid", "assembly": "hg38"},
            )

@pytest.mark.asyncio
@patch("server.ucsc_rest.requests.get")
async def test_list_ucsc_species_mocked(mock_get):
    """Unit test: verify MCP list_species returns species from mocked UCSC."""
    mock_response = Mock()
    mock_response.json.return_value = [
        {
            "speciesKey": "Homo sapiens",
            "scientificName": "Homo sapiens",
            "commonName": "Human",
            "assemblies": [{"genome": "hg38"}],
        },
        {
            "speciesKey": "Mus musculus",
            "scientificName": "Mus musculus",
            "commonName": "Mouse",
            "assemblies": [{"genome": "mm10"}],
        },
    ]
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    async with Client(mcp) as client:
        tools = await client.list_tools()
        tool_names = [t.name for t in tools]
        assert "list_species" in tool_names

        result = await client.call_tool("list_species", arguments={})
        assert result is not None
        assert not result.is_error

        data = json.loads(result.output if hasattr(result, "output") else result.content[0].text)
        assert isinstance(data, list)
        assert any(s["scientificName"] == "Homo sapiens" for s in data)
        assert any("assemblies" in s for s in data)

@pytest.mark.asyncio
@patch("server.ucsc_rest.fetch_ucsc_genomes")
async def test_get_ucsc_assemblies_mocked(mock_fetch):
    """Unit test: verify list_assemblies returns proper match."""
    mock_fetch.return_value = [
        {
            "speciesKey": "Homo sapiens",
            "scientificName": "Homo sapiens",
            "commonName": "Human",
            "assemblies": [{"genome": "hg38", "assemblyName": "Dec. 2013 (GRCh38/hg38)"}],
        }
    ]

    async with Client(mcp) as client:
        tools = await client.list_tools()
        assert "list_assemblies" in [t.name for t in tools]

        result = await client.call_tool("list_assemblies", arguments={"species_name": "Homo sapiens"})
        assert result is not None
        assert not result.is_error

        data = json.loads(result.output if hasattr(result, "output") else result.content[0].text)
        assert data["matched_species"] == "Homo sapiens"
        assert data["assemblies"][0]["genome"] == "hg38"

# ============================================================
#  SMOKE TESTS (MCP client calls)
# ============================================================

@pytest.mark.smoke
@pytest.mark.asyncio
async def test_list_tools_basic():
    """Smoke test: MCP should expose all main tools."""
    async with Client(mcp) as client:
        tools = await client.list_tools()
        names = [t.name for t in tools]

        assert "get_overlapping_features" in names
        assert "list_assemblies" in names
        assert "list_species" in names

# ============================================================
#  INTEGRATION TESTS (UCSC API calls)
# ============================================================

@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_overlapping_features_tool():
    """Test MCP server through the client"""
    
    # Use the FastMCP Client to test MCP
    async with Client(mcp) as client:
        tools = await client.list_tools()
        tool_names = [t.name for t in tools]
        assert "get_overlapping_features" in tool_names
        
        # Call the tool
        result = await client.call_tool(
            "get_overlapping_features",
            arguments={
                "region": "chr8:127738881-127738920",
                "assembly": "hg38",
                "track": "knownGene"
            }
        )
        
        assert result is not None
        assert not result.is_error

        data = json.loads(result.output if hasattr(result, "output") else result.content[0].text)

        #logger.info(f"Tool returned: {data}")

        assert isinstance(data, dict)
        assert "knownGene" in data
        assert data["knownGene"][0]["chrom"] == "chr8"

        genes = data.get("knownGene", [])
        assert any(g.get("geneName") == "MYC" for g in genes), "Expected at least one gene with geneName == 'MYC'"

@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_species_real():
    """Integration test: list_species via live UCSC API."""
    async with Client(mcp) as client:
        result = await client.call_tool("list_species", arguments={})
        assert result is not None
        assert not result.is_error

        data = json.loads(result.output if hasattr(result, "output") else result.content[0].text)
        assert isinstance(data, list)
        assert any("Homo sapiens" in s.get("scientificName", "") for s in data)
        assert any("Mus musculus" in s.get("scientificName", "") for s in data)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_assemblies_real_exact_match():
    """Integration test: list_assemblies for Homo sapiens (real UCSC call)."""
    async with Client(mcp) as client:
        result = await client.call_tool("list_assemblies", arguments={"species_name": "Homo sapiens"})
        assert result is not None
        assert not result.is_error

        data = json.loads(result.output if hasattr(result, "output") else result.content[0].text)
        assert data["matched_species"] == "Homo sapiens"
        assemblies = data.get("assemblies", [])
        assert any("hg38" in a.get("assemblyName", "") for a in assemblies)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_assemblies_real_fuzzy_match():
    """Integration test: get_ucsc_assemblies using fuzzy name 'mouse'."""
    async with Client(mcp) as client:
        result = await client.call_tool("list_assemblies", arguments={"species_name": "mouse"})
        assert result is not None
        assert not result.is_error

        data = json.loads(result.output if hasattr(result, "output") else result.content[0].text)
        assert data["matched_species"] == "Mus musculus"
        assemblies = data.get("assemblies", [])
        assert len(assemblies) > 0
