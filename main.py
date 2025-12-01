from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import os
import os
import groq  # مكتبة Groq للذكاء الاصطناعي

# قراءة مفتاح Groq من المتغيرات البيئية
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY غير موجود في البيئة")

client = groq.Client(api_key=GROQ_API_KEY, model="llama-3.1-70b-versatile")

app = FastAPI(title="AI Core Diagnostic API")

# -------------------------------
# 1) تفعيل CORS
# -------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------
# 2) ربط مجلد الواجهة الأمامية
# -------------------------------
if not os.path.exists("frontend"):
    os.makedirs("frontend")

app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")

# -------------------------------
# 3) صفحة البداية
# -------------------------------
@app.get("/", response_class=FileResponse)
def root():
    path = "frontend/index.html"
    if os.path.isfile(path):
        return FileResponse(path)
    return JSONResponse({"error": "index.html not found"}, 404)

# -------------------------------
# 4) تحليل الخطأ باستخدام الذكاء
# -------------------------------
@app.post("/analyze")
async def analyze(request: Request):
    try:
        data = await request.json()
    except:
        return JSONResponse({"error": "Invalid JSON body"}, 400)

    # استخراج المدخلات
    frontend_url = data.get("frontend_url")
    backend_url = data.get("backend_url")
    frontend_type = data.get("frontend_type")
    backend_type = data.get("backend_type")
    error_message = data.get("error_message")

    # التحقق من المدخلات
    missing = []
    if not frontend_url: missing.append("frontend_url")
    if not backend_url: missing.append("backend_url")
    if not frontend_type: missing.append("frontend_type")
    if not backend_type: missing.append("backend_type")
    if not error_message: missing.append("error_message")

    if missing:
        return JSONResponse({
            "status": "error",
            "missing_fields": missing
        }, 400)

    # -------------------------------
    #  إنشاء prompt للذكاء
    # -------------------------------
    prompt = f"""
    أنت مساعد تقني لتصحيح الأخطاء بين الواجهة الأمامية والخلفية.
    المستخدم أعطاك البيانات التالية:
    Frontend URL: {frontend_url}
    Backend URL: {backend_url}
    Frontend Type: {frontend_type}
    Backend Type: {backend_type}
    رسالة الخطأ: {error_message}

    حدد مصدر الخطأ (فرونت اند أو باك اند) وفسر سبب الخطأ واقترح حل كود عملي.
    أعد النتيجة في JSON يحتوي على:
    {{
        "source": "Frontend/Backend/Unknown",
        "reason": "شرح السبب",
        "fix": "خطوات وحل كود جاهز"
    }}
    """

    try:
        response = client.generate(prompt)
        ai_result = response.output_text
    except Exception as e:
        return JSONResponse({"error": f"AI call failed: {e}"}, 500)

    return {
        "status": "ok",
        "frontend_url": frontend_url,
        "backend_url": backend_url,
        "frontend_type": frontend_type,
        "backend_type": backend_type,
        "error_received": error_message,
        "ai_diagnostic": ai_result
    }

# -------------------------------
# 5) صفحة اختبار
# -------------------------------
@app.get("/test")
def test():
    return {"status": "API Working Successfully"}

# -------------------------------
# 6) تشغيل محلي
# -------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

# -------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
