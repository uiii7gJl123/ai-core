import os
import json
from fastapi import FastAPI, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from groq import Groq

app = FastAPI(title="Frontend-Backend Issue Doctor")

# السماح للواجهة الأمامية (من نفس السيرفس أو من دومينات أخرى إن أردت)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # لاحقاً تقدر تحصرها على دومين معين
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = "llama-3.1-8b-instant"  # عدّل لو Groq غيّر الاسم لاحقاً


def build_client():
    if not GROQ_API_KEY:
        return None
    return Groq(api_key=GROQ_API_KEY)


def classify_side(frontend_url: str, backend_url: str, error_message: str) -> str:
    """
    قواعد أولية لتحديد الجهة (backend / frontend / both / uncertain)
    بناءً على نص رسالة الخطأ.
    """
    msg = (error_message or "").lower()

    backend = False
    frontend = False

    # CORS → غالباً Backend
    if ("cors" in msg or
        "access-control-allow-origin" in msg or
        "cross origin" in msg):
        backend = True

    # Mixed Content → مشكلة نشر/بروتوكول → Backend غالباً
    if "mixed content" in msg:
        backend = True

    # أخطاء سيرفر 5xx → Backend
    if "500" in msg or "502" in msg or "503" in msg:
        backend = True

    # 404 Not Found على مسار API → غالباً Frontend (مسار غلط)
    if "404" in msg and "not found" in msg:
        frontend = True

    # 405 Method Not Allowed → غالباً Frontend (method غلط)
    if "405" in msg or "method not allowed" in msg:
        frontend = True

    # DNS / اتصال بالسيرفر → Backend/شبكة
    if "enotfound" in msg or "dns" in msg or "econnrefused" in msg:
        backend = True

    # failed to fetch بدون CORS → نعتبرها غامضة، نخليها للـAI
    if "failed to fetch" in msg and "cors" not in msg:
        pass

    if backend and frontend:
        return "both"
    if backend:
        return "backend"
    if frontend:
        return "frontend"

    return "uncertain"


def call_groq(frontend_url, backend_url, frontend_type, backend_type, error_message, rule_side: str):
    """
    استدعاء Groq لتوليد التشخيص والكود.
    ترجع دائماً JSON منسّق للواجهة الأمامية.
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
            "extra_notes_ar": "",
            "rule_side": rule_side,
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

3) أرجِع الاستجابة بصيغة JSON فقط، وبالهيكل التالي بالضبط:

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
            "extra_notes_ar": "",
            "rule_side": rule_side,
        }

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

    if data["side"] not in ("backend", "frontend", "both"):
        if rule_side in ("backend", "frontend", "both"):
            data["side"] = rule_side
        else:
            data["side"] = "backend"

    if rule_side in ("backend", "frontend", "both"):
        data["side"] = rule_side

    data["rule_side"] = rule_side
    return data


@app.get("/health", response_class=JSONResponse)
def health():
    return {"status": "ok"}


@app.post("/api/analyze", response_class=JSONResponse)
def analyze(
    frontend_url: str = Form(""),
    backend_url: str = Form(""),
    frontend_type: str = Form(""),
    backend_type: str = Form(""),
    error_message: str = Form(""),
):
    rule_side = classify_side(frontend_url, backend_url, error_message)
    result = call_groq(frontend_url, backend_url, frontend_type, backend_type, error_message, rule_side)
    return JSONResponse(result)


# ===== هنا نربط الواجهة الأمامية (frontend/index.html) =====

# يتوقع وجود مجلد اسمه frontend بجانب main.py
if os.path.isdir("frontend"):
    app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")