# TESTING_INSTRUCTIONS.md
# خطوات تشغيل الاختبارات والتشخيص

## المتطلبات الأولية

```bash
# 1. إنشاء بيئة افتراضية (Virtual Environment)
python -m venv .venv

# 2. تفعيل البيئة الافتراضية
# Windows (PowerShell):
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
. .\.venv\Scripts\Activate.ps1

# Linux / macOS:
source .venv/bin/activate

# 3. تثبيت المتطلبات
pip install -r requirements.txt
```

---

## تشغيل خادم Flask المحلي

### PowerShell (Windows)
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
. .\.venv\Scripts\Activate.ps1
python -u app.py 2>&1 | Tee-Object -FilePath server.log
```

أو استخدم السكربت الجاهز:
```powershell
.\run_server.ps1
```

### CMD (Windows)
```cmd
.venv\Scripts\activate.bat
python -u app.py > server.log 2>&1
```

### Linux / macOS
```bash
source .venv/bin/activate
python -u app.py 2>&1 | tee server.log
```

---

## تشغيل الاختبارات

### 1. فحص الاستيرادات والبيئة
```bash
python test_csrf_simple.py
```
**المتوقع**: `5/5 checks passed`

---

### 2. فحص تهيئة CSRF وإعدادات الأمان في app.py
```bash
python test_csrf_config.py
```
**المتوقع**: `6/6 checks passed`

---

### 3. التحقق من إصلاحات الأمان
```bash
python verify_security_fixes.py
```
**المتوقع**: `6/6 security fix checks passed`

---

### 4. اختبار CSRF الكامل (يتطلب تشغيل الخادم)
```bash
# في نافذة أولى: شغّل الخادم
python app.py

# في نافذة ثانية: شغّل اختبار CSRF
python test_csrf_fix.py
```
**المتوقع**:  
- Test 1: CSRF token found + HTTP 200 أو 302  
- Test 2: HTTP 400 (CSRF protected)

---

### 5. اختبار تدفق تسجيل الدخول الكامل
```bash
python test_flow.py --base-url http://127.0.0.1:5000
```
**المتوقع**: `Passed: 3  Failed: 0`

---

### 6. اختبار تأمين النظام عند بدء التشغيل
```bash
python test_security_startup.py
```

---

### 7. تحقق سريع من البيئة
```bash
python verify.py
```
**المتوقع**: `All checks passed ✓`

---

### 8. تحليل مسارات app.py
```bash
python analyze_routes.py
```

---

### 9. اختبار حد المعدل (Rate Limiter)
```bash
# اختبار طلب مفرد
python tools/login_test.py --username admin --password wrong

# اختبار فيضان (20 طلب بفارق 0.1 ثانية)
python tools/login_flood.py --count 20 --delay 0.1
```
**المتوقع**: ظهور `HTTP 429` بعد تجاوز الحد المحدد.

---

## ملاحظات للمراجعين

1. **شارك ملف `server.log`** إذا ظهر أي Traceback أو خطأ عند تشغيل `app.py`.
2. **شارك ناتج الأوامر** أعلاه مع فريق التطوير.
3. إذا ظهر `SyntaxError` عند تشغيل `app.py`، راجع السطر المتعلق بـ `download_name` في `app.py` وطبّق الإصلاح المقترح في `BRUTEFORCE_PROTECTION_SETUP.md`.

---

## الإصلاح المقترح لـ f-string (SyntaxError)

ابحث في `app.py` عن:
```python
# مثال على الكود المعيب (يسبب SyntaxError في Python < 3.12):
download_name = f"grades_{cls['name']}_{active_name}.pdf".replace(' ', '_')
```

استبدله بـ:
```python
name_part = cls['name'] if isinstance(cls, dict) and 'name' in cls else class_id
download_name = f"grades_{name_part}_{active_name}.pdf".replace(' ', '_')
return send_file(buf, mimetype='application/pdf', as_attachment=True, download_name=download_name)
```

---

## الإصلاح المقترح لـ CSRF وSECRET_KEY في app.py

أضف/عدّل في بداية `app.py`:
```python
import os
from dotenv import load_dotenv
from flask import Flask
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

load_dotenv()  # تحميل متغيرات .env

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change-me-in-production')
app.config['WTF_CSRF_ENABLED'] = True

csrf = CSRFProtect(app)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)
```

أنشئ ملف `.env` في جذر المشروع:
```
SECRET_KEY=your-strong-random-key-here
```

لإنشاء مفتاح قوي:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```
