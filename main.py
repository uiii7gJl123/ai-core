from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import os
from groq import Groq

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not set")

client = Groq(api_key=GROQ_API_KEY)

app = FastAPI(title="AI Core Diagnostic API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if not os.path.exists("frontend"):
    os.makedirs("frontend")

app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")

@app.get("/", response_class=FileResponse)
def root():
    path = "frontend/index.html"
    if os.path.isfile(path):
        return FileResponse(path)
    return JSONResponse({"error": "index.html not found"}, 404)

@app.post("/analyze")
async def analyze(request: Request):
    try:
        data = await request.json()
    except:
        return JSONResponse({"error": "Invalid JSON body"}, 400)

    frontend_url = data.get("frontend_url")
    backend_url = data.get("backend_url")
    frontend_type = data.get("frontend_type")
    backend_type = data.get("backend_type")
    error_message = data.get("error_message")

    missing = [k for k in ("frontend_url","backend_url","frontend_type","backend_type","error_message")
               if not data.get(k)]
    if missing:
        return JSONResponse({"status":"error","missing_fields": missing}, 400)

    prompt = f"""
أنت مساعد تقني لتصحيح الأخطاء بين الواجهة الأمامية والخلفية.
المستخدم أعطاك:
Frontend URL: {frontend_url}
Backend URL: {backend_url}
Frontend Type: {frontend_type}
Backend Type: {backend_type}
رسالة الخطأ: {error_message}

حدد مصدر الخطأ (Frontend / Backend / Unknown)، اشرح السبب، واقترح حل كود عملي.
أعد النتيجة JSON بهذا الشكل:
{{
  "source": "...",
  "reason": "...",
  "fix": "..."
}}
"""

    try:
        resp = client.chat.completions.create(
            messages=[
                {"role":"system","content":"You are a helpful assistant who diagnoses frontend/backend integration bugs."},
                {"role":"user","content": prompt}
            ],
            model="llama-3.3-70b-versatile"
        )
        ai_output = resp.choices[0].message.content
    except Exception as e:
        return JSONResponse({"error": f"AI call failed: {e}"}, 500)

    return JSONResponse({
        "status":"ok",
        "frontend_url": frontend_url,
        "backend_url": backend_url,
        "frontend_type": frontend_type,
        "backend_type": backend_type,
        "error_received": error_message,
        "ai_diagnostic": ai_output
    })

@app.get("/test")
def test():
    return {"status":"API Working Successfully"}
