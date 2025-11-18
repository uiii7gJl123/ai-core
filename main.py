from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import json
from groq import Groq

app = FastAPI()

# السماح لجميع الدومينات
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

client = Groq(api_key="ضع_مفتاحك_هنا")

def clean_text(txt: str):
    # إزالة الأقواس والأحرف اللي تكسر JSON
    txt = txt.replace("\n", " ")
    txt = txt.replace("\r", "")
    txt = txt.replace('"', "'")
    return txt

@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <h2>API Working Successfully ✔</h2>
    """

@app.post("/analyze", response_class=HTMLResponse)
async def analyze(
    frontend_url: str = Form(...),
    backend_url: str = Form(...),
    frontend_type: str = Form(...),
    backend_type: str = Form(...),
    error_message: str = Form(...)
):
    # تنظيف الرسالة
    cleaned_error = clean_text(error_message)

    # تجهيز البايلود
    payload = {
        "frontend_url": frontend_url,
        "backend_url": backend_url,
        "frontend_type": frontend_type,
        "backend_type": backend_type,
        "error_message": cleaned_error
    }

    # تحويل JSON آمن
    safe_json = json.dumps(payload)

    prompt = f"""
    You will analyze this JSON data containing a frontend-backend integration issue.
    Return diagnosis in Arabic.

    DATA:
    {safe_json}
    """

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are an error diagnosis assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )

        ai_text = response.choices[0].message["content"]

        return f"<h2>نتيجة التحليل</h2><p>{ai_text}</p>"

    except Exception as e:
        return f"<h2>خطأ من الخادم</h2><pre>{str(e)}</pre>"