import datetime
import os
import uuid
import shutil
import asyncio
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sorawm.core import SoraWM

# ==========================
# BASIC APP CONFIG
# ==========================
app = FastAPI(title="Sora Watermark Cleaner API")
UPLOAD_DIR = Path("uploads")
PROCESSED_DIR = Path("processed")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

# Allow access from your frontend domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You can restrict to your domain later: ["https://trendsturds.com"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================
# RATE LIMITER (by IP)
# ==========================
user_limits = {}

@app.middleware("http")
async def limit_ip_usage(request: Request, call_next):
    """Limit each IP to 10 uploads per day."""
    client_ip = request.client.host
    today = datetime.date.today().isoformat()
    user_limits.setdefault(client_ip, {}).setdefault(today, 0)

    if request.url.path == "/submit_remove_task" and request.method == "POST":
        if user_limits[client_ip][today] >= 10:
            return JSONResponse(status_code=429, content={"detail": "Daily limit reached (10 videos/day)."})
        user_limits[client_ip][today] += 1

    return await call_next(request)

# ==========================
# TASK STORAGE (in-memory)
# ==========================
tasks = {}

# ==========================
# BACKGROUND CLEANING JOB
# ==========================
async def process_video(task_id: str, input_path: Path, output_path: Path):
    try:
        print(f"[Task {task_id}] Starting watermark removal: {input_path}")
        sora = SoraWM()
        sora.run(input_path, output_path)
        tasks[task_id]["status"] = "completed"
        tasks[task_id]["download_url"] = f"/download/{task_id}"
        print(f"[Task {task_id}] Completed successfully.")
    except Exception as e:
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["error"] = str(e)
        print(f"[Task {task_id}] Failed: {e}")

# ==========================
# ROUTES
# ==========================

@app.post("/submit_remove_task")
async def submit_remove_task(file: UploadFile = File(...), request: Request = None):
    """Receive video, start background task, and return task ID."""
    task_id = str(uuid.uuid4())
    input_path = UPLOAD_DIR / f"{task_id}_{file.filename}"
    output_path = PROCESSED_DIR / f"{task_id}_cleaned.mp4"

    with open(input_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    tasks[task_id] = {
        "status": "processing",
        "input": str(input_path),
        "output": str(output_path),
        "download_url": None,
        "created_at": datetime.datetime.utcnow().isoformat()
    }

    asyncio.create_task(process_video(task_id, input_path, output_path))

    return {"task_id": task_id, "message": "Processing started"}

@app.get("/get_results")
async def get_results(task_id: str):
    """Check progress or get download link."""
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@app.get("/download/{task_id}")
async def download(task_id: str):
    """Download the processed video."""
    task = tasks.get(task_id)
    if not task or task.get("status") != "completed":
        raise HTTPException(status_code=404, detail="Task not ready or not found")
    return FileResponse(task["output"], filename="sora_cleaned.mp4")

@app.get("/")
def home():
    return {"message": "Sora Watermark Cleaner API is running."}

# ==========================
# ENTRY POINT
# ==========================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5344)
