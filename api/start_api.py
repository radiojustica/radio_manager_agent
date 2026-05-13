import uvicorn
from api.manager import app
import logging

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Starting API on port 8001...")
    uvicorn.run(app, host="0.0.0.0", port=8001)


