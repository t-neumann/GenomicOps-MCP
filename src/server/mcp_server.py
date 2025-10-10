# src/server/mcp_server.py
from fastmcp import FastMCP
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
import tools

mcp = FastMCP("ucsc-mcp")

@mcp.tool()
def get_overlapping_features(region: str, assembly: str, track: str = "knownGene") -> dict:
    return tools.overlaps(region, assembly, track)

# FastAPI for human testing
app = FastAPI(title="UCSC MCP Server", version="0.1.0")

class OverlapRequest(BaseModel):
    region: str
    assembly: str
    track: Optional[str] = "knownGene"

@app.post("/overlaps")
def overlaps_api(req: OverlapRequest):
    return tools.overlaps(req.region, req.assembly, req.track)

@app.get("/assemblies")
def assemblies_api():
    return tools.assemblies()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "api":
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8000)
    else:
        mcp.run()
