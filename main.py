import os
import json
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from groq import Groq

app = FastAPI()

# مفتاح Groq من متغيرات البيئة في Render
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = "llama-3.1-8b-instant"  # عدّله إذا تغيّر اسم الموديل لاحقاً


def build_client():
    if not GROQ_API_KEY:
        return None
    return Groq(api_key=GROQ_API_KEY)


def call_groq(frontend_url, backend_url, frontend_type, backend_type, error_message):
    """
    يستدعي Groq ويرجع نتيجة منظمة:
    {
      "side": "backend" | "frontend" | "both",
      "issue_title_ar": "...",
      "summary_ar": "...",
      "steps_ar": ["...", "..."],
      "backend_code": "...",
      "frontend_code": "..."
    }
    """

    client = build_client()
    if client is None:
        return {
            "side": "backend",
            "issue_title_ar": "إعداد خدمة الذكاء الاصطناعي غير مكتمل.",
            "summary_ar": "لم يتم إعداد متغير البيئة GROQ_API_KEY في الخادم.",
            "steps_ar": [
                "ادخل إلى إعدادات Render الخاصة بالخدمة.",
                "أضف متغير بيئة باسم GROQ_API_KEY وضع فيه مفتاح Groq الصحيح.",
                "أعد نشر الخدمة بعد حفظ المتغيرات."
            ],
            "backend_code": "",
            "frontend_code": ""
        }

    # نجمع البيانات في JSON واحد آمن
    payload = {
        "frontend_url": frontend_url,
        "backend_url": backend_url,
        "frontend_type": frontend_type,
        "backend_type": backend_type,
        "error_message": error_message,
    }
    payload_json = json.dumps(payload, ensure_ascii=False)

    prompt = f"""
أنت خبير في مشاكل الربط بين الواجهة الأمامية والخلفية.

لديك بيانات مشكلة في هذا الكائن JSON:

{payload_json}

مهمتك:

1) حدّد بدقة أين الجذر الأساسي للمشكلة:
   - إذا كان الخطأ ناتج من إعدادات أو كود الباك إند فقط → side = "backend"
   - إذا كان الخطأ ناتج من إعدادات أو كود الفرونت إند فقط → side = "frontend"
   - إذا كان هناك أخطاء حقيقية في الاثنين معاً (كل طرف فيه خطأ مستقل) → side = "both"

2) أرجع الاستجابة بصيغة JSON فقط، وبدون أي نص خارج JSON، وبالهيكل التالي بالضبط:

{{
  "side": "backend" | "frontend" | "both",
  "issue_title_ar": "عنوان قصير بالعربية يصف المشكلة",
  "summary_ar": "ملخص مبسط بالعربية لغير المتخصص",
  "steps_ar": [
    "خطوة 1 بالعربية...",
    "خطوة 2 بالعربية..."
  ],
  "backend_code": "إذا كان side يحتوي backend ضع هنا كود/تعديل الباك إند المناسب، وإلا اتركه نصاً فارغاً \"\".",
  "frontend_code": "إذا كان side يحتوي frontend ضع هنا كود/تعديل الفرونت إند المناسب، وإلا اتركه نصاً فارغاً \"\"."
}}

قواعد مهمة:
- التزم تماماً بالهيكل أعلاه.
- لا تضف حقولاً إضافية.
- لا تكتب أي نص خارج JSON.
- إذا كانت المشكلة backend فقط، اجعل side = "backend" و backend_code يحتوي الكود، و frontend_code = "".
- إذا كانت المشكلة frontend فقط، اجعل side = "frontend" و frontend_code يحتوي الكود، و backend_code = "".
- إذا كانت المشكلة حقيقية في الاثنين، اجعل side = "both" وضع كود لكل من backend_code و frontend_code.
"""

    try:
        completion = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "أنت مساعد تقني خبير في مشاكل الربط بين الواجهة الأمامية والخلفية وتحديد مصدر المشكلة بدقة."
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
        )

        content = completion.choices[0].message.content
        data = json.loads(content)

    except Exception as e:
        # أي خطأ من Groq → نرجع نتيجة مفهومة بدلاً من كسر الصفحة
        err = str(e)
        return {
            "side": "backend",
            "issue_title_ar": "تعذّر الاتصال بخدمة Groq.",
            "summary_ar": "حدث خطأ أثناء محاولة استخدام خدمة الذكاء الاصطناعي. قد يكون السبب عطلاً مؤقتاً أو مشكلة في الإعدادات.",
            "steps_ar": [
                "أعد المحاولة بعد بضع دقائق.",
                "تحقّق من صلاحية مفتاح GROQ_API_KEY.",
                "إذا استمر الخطأ، راجع سجلات السيرفر لمعرفة تفاصيله التقنية."
            ],
            "backend_code": f"# تفاصيل الخطأ:\n# {err}",
            "frontend_code": ""
        }

    # ضمان وجود كل الحقول
    defaults = {
        "side": "backend",
        "issue_title_ar": "",
        "summary_ar": "",
        "steps_ar": [],
        "backend_code": "",
        "frontend_code": "",
    }
    for k, v in defaults.items():
        data.setdefault(k, v)

    # تنظيف side
    if data["side"] not in ("backend", "frontend", "both"):
        data["side"] = "backend"

    return data


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
        <p>ادخل بيانات مشكلتك، وسيتم تحليلها بواسطة الذكاء الاصطناعي وتحديد ما إذا كان الخلل من الواجهة الأمامية أو الخلفية أو كليهما.</p>
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
    result = call_groq(frontend_url, backend_url, frontend_type, backend_type, error_message)

    side = result["side"]
    issue_title = result["issue_title_ar"]
    summary = result["summary_ar"]
    steps = result["steps_ar"]
    backend_code = result["backend_code"]
    frontend_code = result["frontend_code"]

    # نص القرار للمستخدم
    if side == "backend":
        decision_text = "القرار: المشكلة الأساسية في الباك إند فقط."
    elif side == "frontend":
        decision_text = "القرار: المشكلة الأساسية في الواجهة الأمامية فقط."
    else:
        decision_text = "القرار: توجد مشاكل حقيقية في الباك إند والواجهة الأمامية معاً."

    steps_html = "<br/>".join(s for s in steps if s.strip()) if steps else ""

    # نعرض الكود المناسبة حسب side
    backend_block = ""
    frontend_block = ""

    if side in ("backend", "both") and backend_code.strip():
        backend_block = f"""
        <h4>كود / تعديل الباك إند المقترح</h4>
        <pre style="background:#272822; color:#f8f8f2; padding:10px; white-space:pre-wrap;">{backend_code}</pre>
        """

    if side in ("frontend", "both") and frontend_code.strip():
        frontend_block = f"""
        <h4>كود / تعديل الواجهة الأمامية المقترح</h4>
        <pre style="background:#272822; color:#f8f8f2; padding:10px; white-space:pre-wrap;">{frontend_code}</pre>
        """

    return f"""
    <html dir="rtl">
      <head>
        <meta charset="utf-8" />
        <title>نتيجة التحليل</title>
      </head>
      <body style="font-family: sans-serif; max-width: 900px; margin: 40px auto;">
        <h2>نتيجة التحليل</h2>

        <h3>{issue_title}</h3>
        <p><strong>{decision_text}</strong></p>

        <h3>تشخيص مختصر (مجاني)</h3>
        <p>{summary}</p>

        <hr/>

        <h3>المحتوى الكامل (تجريبي الآن، لاحقاً سيكون مدفوع)</h3>

        <h4>الخطوات المقترحة</h4>
        <p>{steps_html}</p>

        {backend_block}
        {frontend_block}

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