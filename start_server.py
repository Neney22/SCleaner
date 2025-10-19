import os
import sys
import uvicorn
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# --- Import your watermark removal logic ---
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    from sorawm.core import remove_watermark_task  # adjust if path differs
except Exception as e:
    print("⚠️ Failed to import sorawm.core:", e)
    remove_watermark_task = None

# --- FastAPI app setup ---
app = FastAPI(title="SoraWM - Watermark Remover Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "✅ SoraWM API is running on Render!"}

@app.post("/submit_remove_task")
async def submit_remove_task(file: UploadFile = File(...)):
    if not remove_watermark_task:
        return JSONResponse({"error": "Server misconfigured. Model not loaded."}, status_code=500)
    try:
        task_id = remove_watermark_task(file)
        return JSONResponse({"status": "processing", "task_id": task_id})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# --- Run Server ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5344"))
    print(f"🚀 Launching FastAPI on port {port}")
    uvicorn.run("start_server:app", host="0.0.0.0", port=port, reload=False)
