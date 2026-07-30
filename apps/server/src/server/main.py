"""The only module allowed to import both apps.

One process serves the chatbot at / and the console at /console (TO-21). That is
not just deployment convenience: config_client's 5-second cache lives in process
memory, so an Activate in the console invalidates the exact cache the chatbot
reads, and the next request to /chat picks up the new version immediately. Split
across two processes it still works, just with up to 5 seconds of lag.

    uv run uvicorn server.main:app --reload --port 8000
"""

from ask_luma.main import app
from driftline.main import attach

attach(app)
