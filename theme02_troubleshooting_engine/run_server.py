"""Server launcher for the Smart Guided Troubleshooting Engine."""
import uvicorn
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting Smart Guided Troubleshooting Engine on port {port}...")
    uvicorn.run(
        "theme02_troubleshooting_engine.api.app:app",
        host="0.0.0.0",
        port=port,
        reload=False
    )
