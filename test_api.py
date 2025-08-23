"""
Simple test API to verify the structure
"""
from fastapi import FastAPI

app = FastAPI(
    title="HCE Analyzer Pro Test API",
    description="Test API for the restructured application",
    version="2.0.0"
)

@app.get("/")
async def root():
    return {
        "message": "HCE Analyzer Pro API Test",
        "version": "2.0.0",
        "status": "operational"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "2.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
