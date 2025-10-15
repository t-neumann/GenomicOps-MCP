# src/server/mcp_server.py
from fastmcp import FastMCP
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
from server import tools

# === MCP ===

mcp = FastMCP("ucsc-mcp")

@mcp.tool()
def get_overlapping_features(region: str, assembly: str, track: str = "knownGene") -> dict:
    return tools.get_annotations(region, assembly, track)

@mcp.tool()
def list_species() -> list:
    """List all available species from UCSC."""
    genomes = tools.fetch_ucsc_genomes()
    return tools.get_species(genomes)


@mcp.tool(
    name="list_assemblies",
    description="Get assemblies for a given species (exact or fuzzy match)",
    output_schema={
        "type": "object",
        "properties": {
            "matched_species": {"type": "string"},
            "assemblies": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "genome": {"type": "string"},
                        "assemblyName": {"type": "string"},
                    },
                    "required": ["genome", "assemblyName"]
                }
            },
        },
        "required": ["matched_species", "assemblies"]
    }
)
def list_assemblies(species_name: str) -> list:
    """List all assemblies for a given species."""
    genomes = tools.fetch_ucsc_genomes()
    return tools.get_assemblies(species_name, genomes)

# === FastAPI ===

# FastAPI for human testing
app = FastAPI(title="UCSC MCP Server", version="0.1.0")

class OverlapRequest(BaseModel):
    region: str
    assembly: str = Field(alias="genome")
    track: Optional[str] = "knownGene"

@app.post("/overlaps")
def overlaps_api(req: OverlapRequest):
    return tools.get_annotations(req.region, req.assembly, req.track)

@app.get("/species")
def list_species_api():
    """HTTP endpoint to list all UCSC species."""
    genomes = tools.fetch_ucsc_genomes()
    return tools.get_species(genomes)


@app.get("/assemblies/{species_name}")
def list_assemblies_api(species_name: str, exact: bool = Query(True, description="Set to false for partial name matches")):
    """
    HTTP endpoint to list all assemblies for a given species.
    Accepts scientific name, species key, or common name (case-insensitive).
    Supports partial matches if ?exact=false.
    """
    genomes = tools.fetch_ucsc_genomes()
    return tools.get_assemblies(species_name, genomes, exact)

@app.post("/refresh-cache")
def refresh_ucsc_cache():
    """Force-refresh UCSC genome cache."""
    data = tools.fetch_ucsc_genomes(use_cache=False)
    return {"status": "refreshed", "entries": len(data)}

# === MAIN ===

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "api":
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8000)
    else:
        mcp.run()
