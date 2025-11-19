import os
import json
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from groq import Groq

app = FastAPI()

# إعدادات Groq من متغيرات البيئة
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = "llama-3.1-8b-instant"  # غيّره لاحقاً لو Groq غيّر الأسماء


# --------- أدوات مساعدة --------- #

def build_client():
    if not GROQ_API_KEY:
        return None
    return Groq(api_key=GROQ_API_KEY)


def classify_side(frontend_url: str, backend_url: str, error_message: str) -> str:
    """
    دالة القواعد (Rules):
    تحاول تحديد جهة المشكلة من النص فقط.

    ترجع واحدة من:
    - "backend"
    - "frontend"
    - "both"
    - "uncertain"
    """
    msg = (error_message or "").lower()

    backend = False
    frontend = False

    # 1) مشاكل CORS → غالباً من الباك إند
    if ("cors" in msg or
        "access-control-allow-origin" in msg or
        "cross origin" in msg):
        backend = True

    # 2) Mixed Content (https يطلب http) → إعدادات سيرفر / نشر → نعتبرها backend غالباً
    if "mixed content" in msg:
        backend = True

    # 3) 5xx في السيرفر (500, 502, 503...) → غالباً من الباك إند
    if "500" in msg or "502" in msg or "503" in msg:
        backend = True

    # 4) 404 Not Found على مسار API → غالباً من الفرونت (يطلب مسار غلط)
    if "404" in msg and "not found" in msg:
        frontend = True

    # 5) 405 Method Not Allowed → غالباً من الفرونت (method غلط: GET بدل POST)
    if "405" in msg or "method not allowed" in msg:
        frontend = True

    # 6) failed to fetch بدون كلمة CORS → قد تكون عنوان غلط أو سيرفر مطفأ
    # نصنّفها هنا كـ "uncertain" حتى نستعين بالذكاء الاصطناعي فيها
    if "failed to fetch" in msg and "cors" not in msg:
        # لا نضبط backend/frontend مباشرة، نخليها غامضة
        pass

    # 7) أخطاء DNS / ENOTFOUND → غالباً Backend / DNS
    if "enotfound" in msg or "dns" in msg or "econnrefused" in msg:
        backend = True

    # اتخاذ القرار
    if backend and frontend:
        return "both"
    if backend:
        return "backend"
    if frontend:
        return "frontend"

    # إذا ما قدرنا نحسم → نستعين بالذكاء الاصطناعي
    return "uncertain"


def call_groq(frontend_url, backend_url, frontend_type, backend_type, error_message, rule_side: str):
    """
    يستدعي Groq ويرجع استجابة منظمة.

    rule_side:
      - backend / frontend / both  → قرار القواعد
      - uncertain                  → نخلي Groq يقرر
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
            "frontend_code": "",
            "extra_notes_ar": ""
        }

    payload = {
        "frontend_url": frontend_url,
        "backend_url": backend_url,
        "frontend_type": frontend_type,
        "backend_type": backend_type,
        "error_message": error_message,
        "rule_side": rule_side,
    }
    payload_json = json.dumps(payload, ensure_ascii=False)

    # تعليمات خاصة حسب القواعد
    if rule_side in ("backend", "frontend", "both"):
        side_instruction = f"""
التحليل المبدئي (Rules في الخادم) قرر أن الجهة الأساسية للمشكلة هي:
fixed_side = "{rule_side}"

يجب عليك الالتزام بهذا القرار وعدم تغييره.
"""
    else:
        side_instruction = """
لم يستطع الخادم تحديد الجهة بدقة من خلال القواعد.
مهمتك أن تقرر أنت هل المشكلة في:
- backend
- frontend
- both

واختر side مناسب بناءً على البيانات.
"""

    prompt = f"""
أنت خبير في مشاكل الربط بين الواجهة الأمامية والخلفية.

هذه بيانات المشكلة في JSON:

{payload_json}

{side_instruction}

مهمتك:

1) إذا أعطيتك fixed_side:
   - استخدم نفس القيمة تماماً في الحقل side ولا تغيّرها.
   - "backend" يعني أن التعديل العملي في كود الباك إند فقط.
   - "frontend" يعني أن التعديل العملي في كود الفرونت إند فقط.
   - "both" يعني أن هناك أخطاء حقيقية في الاثنين.

2) إذا لم أعطك fixed_side (rule_side = "uncertain"):
   - استخدم خبرتك لتحديد واحدة فقط من القيم: "backend" أو "frontend" أو "both".

3) أرجِع الاستجابة بصيغة JSON فقط، وبدون أي نص خارج JSON، وبالهيكل التالي بالضبط:

{{
  "side": "backend" | "frontend" | "both",
  "issue_title_ar": "عنوان قصير بالعربية يصف المشكلة",
  "summary_ar": "ملخص مبسط بالعربية لغير المتخصص",
  "steps_ar": [
    "خطوة 1 بالعربية...",
    "خطوة 2 بالعربية..."
  ],
  "backend_code": "إذا كان side يحتوي backend ضع هنا كود/تعديل الباك إند المناسب، وإلا اتركه نصاً فارغاً \"\".",
  "frontend_code": "إذا كان side يحتوي frontend ضع هنا كود/تعديل الفرونت إند المناسب، وإلا اتركه نصاً فارغاً \"\".",
  "extra_notes_ar": "ملاحظات إضافية إن لزم الأمر (يمكن أن تكون فارغة)."
}}

قواعد مهمة:
- التزم تماماً بالهيكل أعلاه.
- لا تضف حقولاً إضافية.
- لا تكتب أي نص خارج JSON.
- إذا كان side = "backend": backend_code يجب أن يحتوي كوداً أو مثالاً واضحاً، و frontend_code = "".
- إذا كان side = "frontend": frontend_code يجب أن يحتوي كوداً أو مثالاً واضحاً، و backend_code = "".
- إذا كان side = "both": backend_code و frontend_code يجب أن يحتوي كل واحد منهما حلاً واضحاً للجهة الخاصة به.
"""

    try:
        completion = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "أنت مساعد تقني خبير في مشاكل الربط بين الواجهة الأمامية والخلفية وتحديد مصدر المشكلة بدقة، ثم اقتراح حلول عملية."
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
        )

        content = completion.choices[0].message.content
        data = json.loads(content)

    except Exception as e:
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
            "frontend_code": "",
            "extra_notes_ar": ""
        }

    # ضمان وجود كل الحقول
    defaults = {
        "side": "backend",
        "issue_title_ar": "",
        "summary_ar": "",
        "steps_ar": [],
        "backend_code": "",
        "frontend_code": "",
        "extra_notes_ar": "",
    }
    for k, v in defaults.items():
        data.setdefault(k, v)

    # تنظيف side من Groq
    if data["side"] not in ("backend", "frontend", "both"):
        # لو القواعد حاسمة نلتزم بها
        if rule_side in ("backend", "frontend", "both"):
            data["side"] = rule_side
        else:
            data["side"] = "backend"

    # إذا القواعد كانت حاسمة (backend/frontend/both) نُلزم النتيجة بنفس الجهة
    if rule_side in ("backend", "frontend", "both"):
        data["side"] = rule_side

    return data


# --------- الواجهات --------- #

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
        <p>ادخل بيانات مشكلتك، وسيتم تحليلها وتحديد ما إذا كان الخلل من الواجهة الأمامية أو الخلفية أو كليهما.</p>
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

          <label>رسالة الخطأ من المتصفح أو من Postman (اختياري)</label><br/>
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
    # 1) القرار المبدئي من القواعد
    rule_side = classify_side(frontend_url, backend_url, error_message)

    # 2) استدعاء Groq مع تمرير قرار القواعد
    result = call_groq(frontend_url, backend_url, frontend_type, backend_type, error_message, rule_side)

    side = result["side"]
    issue_title = result["issue_title_ar"]
    summary = result["summary_ar"]
    steps = result["steps_ar"]
    backend_code = result["backend_code"]
    frontend_code = result["frontend_code"]
    extra_notes = result["extra_notes_ar"]

    # نص القرار للمستخدم
    if side == "backend":
        decision_text = "القرار: المشكلة الأساسية في الباك إند."
    elif side == "frontend":
        decision_text = "القرار: المشكلة الأساسية في الواجهة الأمامية."
    else:
        decision_text = "القرار: توجد مشاكل حقيقية في الباك إند والواجهة الأمامية معاً."

    # وصف مبسط للقرار
    if rule_side == "uncertain":
        rule_note = "التصنيف تم بالاعتماد على تحليل الذكاء الاصطناعي لأن رسالة الخطأ غير حاسمة بصورة مباشرة."
    else:
        rule_note = f"التصنيف المبدئي تم بواسطة قواعد ثابتة في الخادم (Rules) ثم تم توليد الشرح والكود بناءً عليه. (rule_side = {rule_side})"

    steps_html = "<br/>".join(s for s in steps if s.strip()) if steps else ""

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

    extra_html = f"<p>{extra_notes}</p>" if extra_notes else ""

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
        <p style="color: #555;">{rule_note}</p>

        <h3>تشخيص مختصر (مجاني)</h3>
        <p>{summary}</p>

        <hr/>

        <h3>المحتوى الكامل (تجريبي الآن، لاحقاً سيكون مدفوع)</h3>

        <h4>الخطوات المقترحة</h4>
        <p>{steps_html}</p>

        {backend_block}
        {frontend_block}

        {extra_html}

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