from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse

app = FastAPI()


@app.get("/", response_class=HTMLResponse)
def read_root():
    return """
    <html>
      <head>
        <title>AI CORS Doctor</title>
        <meta charset="utf-8" />
      </head>
      <body style="font-family: sans-serif; max-width: 600px; margin: 40px auto;">
        <h1>إصلاح مشاكل الربط بين الواجهة الأمامية والخلفية</h1>
        <p>ادخل بيانات مشكلتك، وسيتم تحليلها بواسطة الذكاء الاصطناعي (لاحقاً).</p>
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
            <option value="other">غير ذلك</option>
          </select><br/><br/>

          <label>نوع الواجهة الخلفية</label><br/>
          <select name="backend_type" style="width:100%; padding:6px;">
            <option value="fastapi">FastAPI</option>
            <option value="express">Express</option>
            <option value="laravel">Laravel</option>
            <option value="django">Django</option>
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
    # لاحقاً: هنا سنربط بالذكاء الاصطناعي + Stripe
    issue_title = "تم استلام المشكلة."
    preview = "هذه نتيجة تجريبية. في النسخة النهائية سيتم تحليل مشكلتك فعلياً بالذكاء الاصطناعي وإظهار جزء مجاني + جزء مدفوع."

    return f"""
    <html>
      <head>
        <meta charset="utf-8" />
        <title>نتيجة التحليل</title>
      </head>
      <body style="font-family: sans-serif; max-width: 600px; margin: 40px auto;">
        <h2>النتيجة (الجزء المجاني)</h2>
        <h3>{issue_title}</h3>
        <p>{preview}</p>

        <h2>الحل الكامل (الجزء المدفوع)</h2>
        <p>سيتم هنا لاحقاً عرض الشرح الكامل، الخطوات، والكود الجاهز بعد الدفع.</p>
        <button disabled style="padding:8px 16px; opacity:0.5;">
          عرض الحل الكامل (مدفوع - قيد التطوير)
        </button>

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
