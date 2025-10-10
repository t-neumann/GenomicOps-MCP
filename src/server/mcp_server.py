# src/server/mcp_server.py
from fastmcp import FastMCP
from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import Optional
from . import tools

mcp = FastMCP("ucsc-mcp")

@mcp.tool()
def get_overlapping_features(region: str, assembly: str, track: str = "knownGene") -> dict:
    return tools.get_annotations(region, assembly, track)

# FastAPI for human testing
app = FastAPI(title="UCSC MCP Server", version="0.1.0")

class OverlapRequest(BaseModel):
    region: str
    assembly: str = Field(alias="genome")
    track: Optional[str] = "knownGene"

@app.post("/overlaps")
def overlaps_api(req: OverlapRequest):
    return tools.get_annotations(req.region, req.assembly, req.track)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "api":
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8000)
    else:
        mcp.run()
