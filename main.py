import os
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from groq import Groq

app = FastAPI()

# قراءة مفتاح Groq من متغير البيئة في Render
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()


def build_client():
    if not GROQ_API_KEY:
        return None
    return Groq(api_key=GROQ_API_KEY)


def build_prompt(frontend_url, backend_url, frontend_type, backend_type, error_message):
    return f"""
أنت خبير في مشاكل الربط بين الواجهة الأمامية والخلفية (CORS, URLs, HTTP errors).

حلّل المشكلة بناءً على البيانات التالية:

- Frontend URL: {frontend_url}
- Backend URL: {backend_url}
- Frontend type: {frontend_type}
- Backend type: {backend_type}
- Error message: {error_message}

اكتب الإجابة بالعربية، وبالهيكل EXACT التالي (نفس العناوين):

[SUMMARY]
ملخص قصير جداً للمشكلة في سطر أو سطرين فقط.

[STEPS]
خطوات عملية واضحة لحل المشكلة، كل خطوة في سطر منفصل.

[BACKEND_CODE]
كود مقترح للباك إند (أو تعديل على الكود) يساعد في حل المشكلة.

[FRONTEND_CODE]
كود أو إعدادات مقترحة للفرونت إند (مثل إعداد proxy أو تعديل request).

استخدم نفس العناوين الموضحة بين الأقواس ولا تضف JSON.
"""


def parse_sections(text: str):
    sections = {
        "SUMMARY": "",
        "STEPS": "",
        "BACKEND_CODE": "",
        "FRONTEND_CODE": "",
    }
    current = None
    lines = text.splitlines()
    for line in lines:
        line_stripped = line.strip()
        if line_stripped == "[SUMMARY]":
            current = "SUMMARY"
            continue
        if line_stripped == "[STEPS]":
            current = "STEPS"
            continue
        if line_stripped == "[BACKEND_CODE]":
            current = "BACKEND_CODE"
            continue
        if line_stripped == "[FRONTEND_CODE]":
            current = "FRONTEND_CODE"
            continue
        if current:
            sections[current] += line + "\n"
    for k in sections:
        sections[k] = sections[k].strip()
    return sections


@app.get("/", response_class=HTMLResponse)
def read_root():
    return """
    <html dir="rtl">
      <head>
        <meta charset="utf-8" />
        <title>إصلاح مشاكل الربط بين الواجهة الأمامية والخلفية</title>
      </head>
      <body style="font-family: sans-serif; max-width: 800px; margin: 40px auto;">
        <h1>إصلاح مشاكل الربط بين الواجهة الأمامية والخلفية</h1>
        <p>ادخل بيانات مشكلتك، وسيتم تحليلها بواسطة الذكاء الاصطناعي.</p>
        <form method="post" action="/analyze">
          <label>رابط الواجهة الأمامية (Frontend URL)</label><br/>
          <input type="text" name="frontend_url" style="width:100%; padding:6px;" /><br/><br/>

          <label>رابط الواجهة الخلفية / API (Backend URL)</label><br/>
          <input type="text" name="backend_url" style="width:100%; padding:6px;" /><br/><br/>

          <label>نوع الواجهة الأمامية</label><br/>
          <select name="frontend_type" style="width:100%; padding:6px;">
            <option value="React + Vite">React + Vite</option>
            <option value="React">React</option>
            <option value="Vue">Vue</option>
            <option value="Next.js">Next.js</option>
            <option value="Angular">Angular</option>
            <option value="HTML/JS">HTML/JS</option>
            <option value="Other">غير ذلك</option>
          </select><br/><br/>

          <label>نوع الواجهة الخلفية</label><br/>
          <select name="backend_type" style="width:100%; padding:6px;">
            <option value="FastAPI">FastAPI</option>
            <option value="Express">Express</option>
            <option value="Laravel">Laravel</option>
            <option value="Django">Django</option>
            <option value="Node.js">Node.js (عام)</option>
            <option value="Other">غير ذلك</option>
          </select><br/><br/>

          <label>رسالة الخطأ (اختياري)</label><br/>
          <textarea name="error_message" rows="5" style="width:100%; padding:6px;"></textarea><br/><br/>

          <button type="submit" style="padding:8px 16px;">حلل المشكلة</button>
        </form>
      </body>
    </html>
    """


@app.post("/analyze", response_class=HTMLResponse)
def analyze(
    frontend_url: str = Form(""),
    backend_url: str = Form(""),
    frontend_type: str = Form(""),
    backend_type: str = Form(""),
    error_message: str = Form(""),
):
    client = build_client()
    if client is None:
        summary = "مفتاح GROQ_API_KEY غير مضبوط في الخادم."
        steps = "ادخل إلى إعدادات Render ثم أضف متغير البيئة GROQ_API_KEY بمفتاح Groq الصحيح."
        backend_code = ""
        frontend_code = ""
    else:
        prompt = build_prompt(
            frontend_url, backend_url, frontend_type, backend_type, error_message
        )
        try:
            completion = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {
                        "role": "system",
                        "content": "أنت مساعد خبير يساعد المبرمجين على حل مشاكل الربط بين الواجهة الأمامية والخلفية.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
            )
            content = completion.choices[0].message.content
            parts = parse_sections(content or "")
            summary = parts.get("SUMMARY") or "لم يرجع النموذج ملخصاً واضحاً."
            steps = parts.get("STEPS") or ""
            backend_code = parts.get("BACKEND_CODE") or ""
            frontend_code = parts.get("FRONTEND_CODE") or ""
        except Exception as e:
            summary = "حدث خطأ أثناء الاتصال بخدمة Groq."
            steps = f"نص الخطأ الخام:\n{repr(e)}"
            backend_code = ""
            frontend_code = ""

    steps_html = "<br/>".join(
        s for s in (steps.splitlines() if steps else []) if s.strip()
    )

    return f"""
    <html dir="rtl">
      <head>
        <meta charset="utf-8" />
        <title>نتيجة التحليل</title>
      </head>
      <body style="font-family: sans-serif; max-width: 900px; margin: 40px auto;">
        <h2>نتيجة التحليل</h2>

        <h3>تشخيص مختصر (مجاني)</h3>
        <p>{summary}</p>

        <hr/>

        <h3>المحتوى الكامل (تجريبي الآن، لاحقاً سيكون مدفوع)</h3>

        <h4>الخطوات المقترحة</h4>
        <p>{steps_html}</p>

        <h4>كود الباك إند المقترح</h4>
        <pre style="background:#272822; color:#f8f8f2; padding:10px; white-space:pre-wrap;">{backend_code}</pre>

        <h4>كود الواجهة الأمامية / إعدادات الفرونت</h4>
        <pre style="background:#272822; color:#f8f8f2; padding:10px; white-space:pre-wrap;">{frontend_code}</pre>

        <hr/>
        <h4>بيانات المشكلة التي أدخلتها</h4>
        <ul>
          <li>Frontend URL: {frontend_url}</li>
          <li>Backend URL: {backend_url}</li>
          <li>Frontend type: {frontend_type}</li>
          <li>Backend type: {backend_type}</li>
          <li>Error message: <pre>{error_message}</pre></li>
        </ul>

        <a href="/">رجوع</a>
      </body>
    </html>
    """