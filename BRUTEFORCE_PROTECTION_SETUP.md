# BRUTEFORCE_PROTECTION_SETUP.md
# دليل إعداد حماية Brute-Force باستخدام Flask-Limiter

## نظرة عامة

يشرح هذا الدليل كيفية إعداد **Flask-Limiter** لتقييد عدد طلبات تسجيل الدخول وحماية التطبيق من هجمات Brute-Force وهجمات الـ Credential Stuffing.

---

## 1. التثبيت

```bash
pip install flask-limiter
```

أو أضف `Flask-Limiter>=3.5.0` إلى `requirements.txt` ثم شغّل:

```bash
pip install -r requirements.txt
```

---

## 2. الإعداد الأساسي في app.py

```python
import os
from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv

load_dotenv()  # تحميل متغيرات .env

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change-me-in-production')

# تهيئة CSRF
csrf = CSRFProtect(app)

# تهيئة Rate Limiter
limiter = Limiter(
    get_remote_address,          # تقييد بالـ IP
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",     # للتطوير؛ استخدم Redis في الإنتاج
)
```

---

## 3. تطبيق حد المعدل على مسار تسجيل الدخول

```python
@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")   # ← الحد الموصى به لتسجيل الدخول
def login():
    ...
```

### حدود موصى بها

| المسار         | الحد              | السبب                                    |
|----------------|-------------------|------------------------------------------|
| `/login`       | 5 per minute      | منع Brute-Force                          |
| `/register`    | 3 per hour        | منع التسجيل الجماعي                      |
| `/reset`       | 3 per hour        | منع إساءة استخدام إعادة تعيين كلمة المرور |
| Default (كل)   | 200 per day       | حماية عامة                               |

---

## 4. معالج خطأ 429

```python
from flask import jsonify, render_template

@app.errorhandler(429)
def rate_limit_exceeded(e):
    # للـ API
    if request.accept_mimetypes.accept_json:
        return jsonify(error="Too many requests. Please try again later."), 429
    # للصفحات العادية
    return render_template('errors/429.html', retry_after=e.retry_after), 429
```

---

## 5. استخدام Redis في الإنتاج

```python
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri=os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
)
```

> **ملاحظة**: التخزين في الذاكرة (`memory://`) يُفقد عند إعادة تشغيل الخادم.  
> في الإنتاج، استخدم دائماً Redis أو Memcached.

---

## 6. اختبار Rate Limiter

```bash
# تشغيل اختبار الفيضان (flood test)
python tools/login_flood.py --count 20 --delay 0.05

# أو باستخدام curl (Linux/Mac)
for i in $(seq 1 10); do
  curl -s -o /dev/null -w "%{http_code}\n" \
    -X POST http://127.0.0.1:5000/login \
    -d "username=test&password=test&csrf_token=INVALID"
done
```

**نتيجة متوقعة**: بعد 5 طلبات خلال دقيقة، يجب أن تحصل على `HTTP 429`.

---

## 7. ملاحظات أمنية إضافية

- **لا تستخدم `@csrf.exempt`** على مسار `/login` إلا لأسباب موثقة ومبررة.
- تأكد من أن `SECRET_KEY` قوي وعشوائي:
  ```python
  import secrets
  print(secrets.token_hex(32))
  ```
- احرص على تفعيل `SESSION_COOKIE_SECURE = True` في بيئة HTTPS.
- استخدم `SESSION_COOKIE_HTTPONLY = True` لمنع XSS من سرقة الجلسة.

---

## 8. تشخيص المشكلات الشائعة

| المشكلة                              | السبب المحتمل                                | الحل                              |
|--------------------------------------|----------------------------------------------|-----------------------------------|
| CSRF token is missing                | `CSRFProtect(app)` غير مُهيَّأ              | أضف `csrf = CSRFProtect(app)`    |
| Bad Request 400 رغم إرسال التوكن    | `SECRET_KEY` يتغير بين الطلبات               | تأكد أن `SECRET_KEY` ثابت في .env |
| SyntaxError في app.py               | f-string متداخل مع أقواس قاموس بنفس الاقتباس | راجع قسم `download_name` في app.py |
| لا يظهر 429 مع flood test           | Flask-Limiter غير مُعد على مسار `/login`     | أضف `@limiter.limit("5 per minute")` |
| Rate limit لا يعمل بعد إعادة التشغيل | استخدام `memory://` في storage               | انتقل إلى Redis                  |
