from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import os

app = FastAPI(title="AI Core Diagnostic API")

# -------------------------------
# 1) تفعيل CORS
# -------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # السماح لكل المواقع
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------
# 2) ربط مجلد الواجهة الأمامية frontend/
# -------------------------------
if not os.path.exists("frontend"):
    os.makedirs("frontend")   # لو مجلد الواجهة غير موجود

app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")

# -------------------------------
# 3) صفحة البداية — index.html
# -------------------------------
@app.get("/", response_class=FileResponse)
def serve_frontend():
    path = "frontend/index.html"
    if os.path.isfile(path):
        return FileResponse(path)
    return JSONResponse({"error": "index.html not found inside /frontend"}, status_code=404)

# -------------------------------
# 4) مسار التحليل /analyze
# -------------------------------
@app.post("/analyze")
async def analyze(request: Request):

    data = await request.json()

    frontend_url = data.get("frontend_url", "")
    backend_url = data.get("backend_url", "")
    frontend_type = data.get("frontend_type", "")
    backend_type = data.get("backend_type", "")
    error_message = data.get("error_message", "")

    # ---------------------------
    # تشخيص مبدأي بسيط (placeholder)
    # ---------------------------
    result = {
        "short_summary": "تم استلام البيانات وسيتم تحليلها.",
        "full_fix": "سيتم إضافة الذكاء لاحقًا.",
        "code_example": None
    }

    return JSONResponse(result)


# -------------------------------
# 5) صفحة اختبار
# -------------------------------
@app.get("/test")
def test():
    return {"status": "API Working Successfully ✔"}


# -------------------------------
# 6) تشغيل محلي
# -------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)