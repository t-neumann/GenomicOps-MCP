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
@patch('server.tools.requests.get')
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
        # Ensure tool is registered
        tools = await client.list_tools()
        tool_names = [t.name for t in tools]
        assert "get_overlapping_features" in tool_names

        # Call the tool
        result = await client.call_tool(
            "get_overlapping_features",
            arguments={
                "region": "chr1:1000-2000",
                "assembly": "hg38",
                "track": "knownGene"
            },
        )

        # Validate result
        assert result is not None
        assert not result.is_error

        data = json.loads(result.output if hasattr(result, "output") else result.content[0].text)
        assert isinstance(data, dict)
        assert "knownGene" in data
        assert data["knownGene"][0]["chrom"] == "chr1"

@pytest.mark.asyncio
@patch('server.tools.requests.get')
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
@patch('server.tools.requests.get')
async def test_get_overlapping_features_tool_invalid_region(mock_get):
    """Unit test: invalid region should raise exception."""
    mock_get.side_effect = Exception("Invalid region")

    async with Client(mcp) as client:
        with pytest.raises(Exception):
            await client.call_tool(
                "get_overlapping_features",
                arguments={"region": "invalid", "assembly": "hg38"},
            )

# ============================================================
#  INTEGRATION TESTS (UCSC API calls)
# ============================================================

@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_overlapping_features_tool():
    """Test MCP server through the client"""
    
    # Use the FastMCP Client to test the tool
    async with Client(mcp) as client:
        # List tools to verify it's registered
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
        
        # The result should contain data
        assert result is not None
        assert not result.is_error

        data = json.loads(result.output if hasattr(result, "output") else result.content[0].text)

        #logger.info(f"Tool returned: {data}")

        assert isinstance(data, dict)
        assert "knownGene" in data
        assert data["knownGene"][0]["chrom"] == "chr8"

        genes = data.get("knownGene", [])
        assert any(g.get("geneName") == "MYC" for g in genes), "Expected at least one gene with geneName == 'MYC'"