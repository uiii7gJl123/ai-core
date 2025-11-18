from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from groq import Groq
import os

app = FastAPI()

def call_groq_analysis(prompt: str):
    try:
        client = Groq(api_key=os.environ["GROQ_API_KEY"])

        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "أنت مساعد خبير يحلل مشاكل الربط بين الواجهة الأمامية والخلفية، ويقترح حلولاً دقيقة مع كود جاهز."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            response_format={"type": "json_object"}
        )

        ai_response = completion.choices[0].message.content
        return ai_response

    except Exception as e:
        return f"خطأ في الاتصال مع Groq\nRaw error: {str(e)}"


@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <html dir='rtl'>
    <body>
        <h2>إصلاح مشاكل الربط بين الواجهة الأمامية والخلفية</h2>
        <form action="/analyze" method="post">
            <input name="frontend_url" placeholder="رابط الواجهة الأمامية"><br><br>
            <input name="backend_url" placeholder="رابط الواجهة الخلفية"><br><br>

            <select name="frontend_type">
                <option value="React">React</option>
                <option value="Vue">Vue</option>
                <option value="Next.js">Next.js</option>
                <option value="HTML">HTML</option>
            </select><br><br>

            <select name="backend_type">
                <option value="Node">Node</option>
                <option value="FastAPI">FastAPI</option>
                <option value="Laravel">Laravel</option>
                <option value="Django">Django</option>
            </select><br><br>

            <textarea name="error_message" placeholder="رسالة الخطأ إن وجدت"></textarea><br><br>
            <button type="submit">حلل المشكلة</button>
        </form>
    </body>
    </html>
    """


@app.post("/analyze", response_class=HTMLResponse)
async def analyze(
    frontend_url: str = Form(""),
    backend_url: str = Form(""),
    frontend_type: str = Form(""),
    backend_type: str = Form(""),
    error_message: str = Form("")
):

    prompt = f"""
    حلل مشكلة الربط بين الواجهة الأمامية والخلفية.

    Frontend URL: {frontend_url}
    Backend URL: {backend_url}

    Frontend Type: {frontend_type}
    Backend Type: {backend_type}

    Error message: {error_message}

    المطلوب:
    1. اكتشاف المشكلة الأساسية بدقة.
    2. شرح مبسط جداً (مجاني).
    3. شرح تقني عميق + خطوات الإصلاح + كود جاهز (مدفوع).

    أعد النتيجة بصيغة JSON:
    {{
        "short_summary": "...",
        "full_fix": "...",
        "code_example": "..."
    }}
    """

    ai_result = call_groq_analysis(prompt)

    return f"""
    <html dir='rtl'>
    <body>
        <h2>نتيجة التحليل</h2>

        <h3>تشخيص مختصر (مجاني)</h3>
        <div>{ai_result}</div>

        <hr>

        <h3>المحتوى الكامل (مدفوع)</h3>
        <p>ادفع ليتم عرض الشرح الكامل + الأكواد الجاهزة.</p>

    </body>
    </html>
    """