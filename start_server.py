
from fastapi import FastAPI, Request, UploadFile, HTTPException
import datetime

app = FastAPI()

user_limits = {}

@app.middleware("http")
async def limit_ip_usage(request: Request, call_next):
    client_ip = request.client.host
    today = datetime.date.today().isoformat()
    user_limits.setdefault(client_ip, {}).setdefault(today, 0)

    if request.url.path == "/submit_remove_task" and request.method == "POST":
        if user_limits[client_ip][today] >= 10:
            raise HTTPException(status_code=429, detail="Daily limit reached (10 videos/day)")
        user_limits[client_ip][today] += 1

    return await call_next(request)


import argparse

import fire
import uvicorn
from loguru import logger

from sorawm.configs import LOGS_PATH
from sorawm.server.app import init_app

parser = argparse.ArgumentParser()
parser.add_argument("--host", default="0.0.0.0", help="host")
parser.add_argument("--port", default=5344, help="port")
parser.add_argument("--workers", default=1, type=int, help="workers")
args = parser.parse_args()
logger.add(LOGS_PATH / "log_file.log", rotation="1 week")


def start_server(port=args.port, host=args.host):
    logger.info(f"Starting server at {host}:{port}")
    app = init_app()
    config = uvicorn.Config(app, host=host, port=port, workers=args.workers)
    server = uvicorn.Server(config=config)
    try:
        server.run()
    finally:
        logger.info("Server shutdown.")


if __name__ == "__main__":
    fire.Fire(start_server)
