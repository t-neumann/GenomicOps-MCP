# src/server/main.py
from fastapi import FastAPI
from .api import router

app = FastAPI(title="GenomicOps MCP Server")

# Register API routes
app.include_router(router)

def main():
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")

if __name__ == "__main__":
    main()