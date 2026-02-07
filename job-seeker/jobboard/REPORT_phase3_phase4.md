# گزارش فاز ۳ و ۴ پروژه JobBoard

## فاز ۳

### 1) تعریف User Model
- یک Custom User Model با نام `accounts.User` اضافه شد (inherits از `AbstractUser`)
- فیلدهای اضافه:
  - `email` (unique)
  - `role` (employer / jobseeker)
  - `is_email_verified`

در `settings.py` مقدار زیر تنظیم شد:
- `AUTH_USER_MODEL = "accounts.User"`

### 2) Session Management
در `settings.py`:
- `SESSION_COOKIE_AGE` (پیش‌فرض 3600 ثانیه)
- `SESSION_SAVE_EVERY_REQUEST = True`

در لاگین (`accounts.views.user_login`):
- `request.session.set_expiry(SESSION_COOKIE_AGE)`
- ذخیره نقش کاربر در `request.session["role"]`

### 3) Logging
در `settings.py` تنظیمات `LOGGING` اضافه شد:
- خروجی هم روی کنسول و هم روی فایل `logs/jobboard.log`

در Viewهای اصلی لاگ اضافه شد:
- accounts: register/login/logout/activate
- jobs: create/apply/schedule/reject/view applications
- resumes: upload/list


## فاز ۴

### 1) Managers
در `jobs/models.py`:
- `JobManager` و `JobQuerySet`
  - `recent()`, `search_title(q)`, `for_employer(employer)`
- `JobApplicationManager` و `JobApplicationQuerySet`
  - `submitted()`, `interviews()`, `rejected()`, `for_job(job)`, `for_jobseeker(profile)`

### 2) تایید ایمیل کاربر (Activation)
در ثبت‌نام‌ها:
- کاربر با `is_active=False` ساخته می‌شود
- ایمیل فعال‌سازی با لینک توکن‌دار ارسال می‌شود

مسیر فعال‌سازی:
- `/accounts/activate/<uidb64>/<token>/`

برای توسعه:
- `EMAIL_BACKEND` روی console تنظیم شده و ایمیل در ترمینال نمایش داده می‌شود.

### 3) بهینه‌سازی Template
- `base.html` بهبود داده شد:
  - navbar، لینک‌های ورود/خروج
  - نمایش پیام‌های Django messages
- صفحه‌های login و ثبت‌نام‌ها و home از base ارث‌بری می‌کنند.

### 4) PostgreSQL
تنظیمات دیتابیس PostgreSQL در `settings.py` موجود است و با env هم قابل تنظیم است:
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`
