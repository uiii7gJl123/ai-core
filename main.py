import os
import json
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from groq import Groq

app = FastAPI()

# إنشاء عميل Groq باستخدام متغير البيئة
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


def call_groq_analysis(
    frontend_url: str,
    backend_url: str,
    frontend_type: str,
    backend_type: str,
    error_message: str,
):
    """
    يستدعي نموذج Groq ويطلب منه يرجع JSON منظم يحتوي:
    - جزء مجاني: عنوان + وصف مختصر
    - جزء كامل: شرح، خطوات، أكواد، نصائح
    """

    if client is None:
        # لو المفتاح غير موجود، نرجّع نتيجة بسيطة بدل ما نكسر الصفحة
        return {
            "issue_title_ar": "إعداد الذكاء الاصطناعي غير مكتمل.",
            "preview_one_line_ar": "يبدو أنه لم يتم إعداد مفتاح GROQ_API_KEY في الخادم بعد.",
            "explanation_simple_ar": "الخادم لا يملك صلاحية الاتصال بخدمة الذكاء الاصطناعي حالياً. راجع إعداد متغير البيئة GROQ_API_KEY في Render.",
            "explanation_technical_ar": "",
            "step_by_step_ar": [],
            "backend_fix_snippet": "",
            "frontend_fix_snippet": "",
            "common_mistakes_ar": [],
            "checklist_ar": [],
        }

    prompt = f"""
أنت خبير في مشاكل الربط بين الواجهة الأمامية والخلفية (CORS, URLs, Proxies, HTTP errors).

المطلوب: حلّل المشكلة وأرجِع استجابة بصيغة JSON فقط (بدون أي نص آخر)،
وبالهيكل التالي بالضبط:

{{
  "issue_title_ar": "...",
  "preview_one_line_ar": "...",
  "explanation_simple_ar": "...",
  "explanation_technical_ar": "...",
  "step_by_step_ar": ["...", "..."],
  "backend_fix_snippet": "...",
  "frontend_fix_snippet": "...",
  "common_mistakes_ar": ["...", "..."],
  "checklist_ar": ["...", "..."]
}}

قواعد مهمة:
- اكتب كل الشرح بالعربية الفصحى المبسطة.
- اكتب الشرح التقني بالعربية، ويمكنك استخدام مصطلحات إنجليزية فقط عند الحاجة (CORS, origin, headers...).
- backend_fix_snippet: اكتب كود مناسب لنوع الباك إند المذكور.
- frontend_fix_snippet: اكتب كود مناسب لنوع الفرونت المذكور (مثل إعداد proxy أو استخدام env).
- step_by_step_ar: خطوات عملية واضحة يمكن لمبرمج مبتدئ أن يتبعها.
- common_mistakes_ar: أخطاء شائعة لها علاقة بهذه الحالة.
- checklist_ar: قائمة تحقق نهائية قبل التجربة مرة أخرى.

بيانات المشكلة:

- Frontend URL: {frontend_url}
- Backend URL: {backend_url}
- Frontend type: {frontend_type}
- Backend type: {backend_type}
- Error message: {error_message}
"""

    completion = client.chat.completions.create(
        model="llama3-70b-8192",  # أو أي موديل مدعوم آخر
        messages=[
            {
                "role": "system",
                "content": "أنت مساعد خبير يساعد المبرمجين على حل مشاكل الربط بين الواجهة الأمامية والخلفية.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )

    content = completion.choices[0].message.content

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        # في حال أخطأ النموذج، نرجع شيء بسيط
        data = {
            "issue_title_ar": "حدث خطأ في تنسيق استجابة الذكاء الاصطناعي.",
            "preview_one_line_ar": "تعذر قراءة الاستجابة كـ JSON. حاول مرة أخرى لاحقاً.",
            "explanation_simple_ar": content,
            "explanation_technical_ar": "",
            "step_by_step_ar": [],
            "backend_fix_snippet": "",
            "frontend_fix_snippet": "",
            "common_mistakes_ar": [],
            "checklist_ar": [],
        }

    # تأكد من وجود كل الحقول، حتى لو كانت ناقصة
    defaults = {
        "issue_title_ar": "",
        "preview_one_line_ar": "",
        "explanation_simple_ar": "",
        "explanation_technical_ar": "",
        "step_by_step_ar": [],
        "backend_fix_snippet": "",
        "frontend_fix_snippet": "",
        "common_mistakes_ar": [],
        "checklist_ar": [],
    }
    for k, v in defaults.items():
        data.setdefault(k, v)

    return data


@app.get("/", response_class=HTMLResponse)
def read_root():
    return """
    <html>
      <head>
        <title>AI CORS Doctor</title>
        <meta charset="utf-8" />
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
            <option value="react_vite">React + Vite</option>
            <option value="react">React</option>
            <option value="vue">Vue</option>
            <option value="nextjs">Next.js</option>
            <option value="angular">Angular</option>
            <option value="other">غير ذلك</option>
          </select><br/><br/>

          <label>نوع الواجهة الخلفية</label><br/>
          <select name="backend_type" style="width:100%; padding:6px;">
            <option value="fastapi">FastAPI</option>
            <option value="express">Express</option>
            <option value="laravel">Laravel</option>
            <option value="django">Django</option>
            <option value="nestjs">NestJS</option>
            <option value="other">غير ذلك</option>
          </select><br/><br/>

          <label>رسالة الخطأ (اختياري)</label><br/>
          <textarea name="error_message" rows="4" style="width:100%; padding:6px;"></textarea><br/><br/>

          <button type="submit" style="padding:8px 16px;">حلل المشكلة</button>
        </form>
      </body>
    </html>
    """


@app.post("/analyze", response_class=HTMLResponse)
def analyze(
    frontend_url: str = Form(...),
    backend_url: str = Form(...),
    frontend_type: str = Form(...),
    backend_type: str = Form(...),
    error_message: str = Form(""),
):
    ai_data = call_groq_analysis(
        frontend_url=frontend_url,
        backend_url=backend_url,
        frontend_type=frontend_type,
        backend_type=backend_type,
        error_message=error_message,
    )

    # جزء مجاني
    issue_title = ai_data["issue_title_ar"]
    preview = ai_data["preview_one_line_ar"]

    # الجزء الكامل (لاحقاً سيكون خلف الدفع)
    explanation_simple = ai_data["explanation_simple_ar"]
    explanation_technical = ai_data["explanation_technical_ar"]
    steps = ai_data["step_by_step_ar"]
    backend_snippet = ai_data["backend_fix_snippet"]
    frontend_snippet = ai_data["frontend_fix_snippet"]
    common_mistakes = ai_data["common_mistakes_ar"]
    checklist = ai_data["checklist_ar"]

    # الآن نعرض الكل مع فصل واضح بين مجاني ومدفوع
    # لاحقاً يمكن إخفاء القسم المدفوع حتى تتم عملية الدفع.

    steps_html = "".join(f"<li>{s}</li>" for s in steps)
    mistakes_html = "".join(f"<li>{s}</li>" for s in common_mistakes)
    checklist_html = "".join(f"<li>{s}</li>" for s in checklist)

    return f"""
    <html>
      <head>
        <meta charset="utf-8" />
        <title>نتيجة التحليل</title>
      </head>
      <body style="font-family: sans-serif; max-width: 900px; margin: 40px auto;">
        <h2>النتيجة (الجزء المجاني)</h2>
        <h3>{issue_title}</h3>
        <p>{preview}</p>

        <hr/>

        <h2>الحل الكامل (الجزء المدفوع - معروض الآن للتجربة)</h2>

        <h3>شرح مبسط</h3>
        <p>{explanation_simple}</p>

        <h3>شرح تقني</h3>
        <pre style="background:#f4f4f4; padding:10px; white-space:pre-wrap;">{explanation_technical}</pre>

        <h3>الخطوات</h3>
        <ol>{steps_html}</ol>

        <h3>كود الباك إند المقترح</h3>
        <pre style="background:#272822; color:#f8f8f2; padding:10px; overflow:auto;">{backend_snippet}</pre>

        <h3>كود الواجهة الأمامية / الإعداد المقترح</h3>
        <pre style="background:#272822; color:#f8f8f2; padding:10px; overflow:auto;">{frontend_snippet}</pre>

        <h3>أخطاء شائعة</h3>
        <ul>{mistakes_html}</ul>

        <h3>قائمة التحقق قبل التجربة مرة أخرى</h3>
        <ul>{checklist_html}</ul>

        <hr/>
        <h3>بيانات المشكلة التي أدخلتها</h3>
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