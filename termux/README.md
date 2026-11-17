# تشغيل أسيكودا العالمي (العراق) على الجوال

برنامج أسيكودا (`AWIQWorld.jnlp`) هو برنامج **Java Swing** للحاسوب، يتصل بالسيرفر
`asy.mof.gov.iq` على المنفذ **2006**. أندرويد ما يدعم Java Swing مباشرة،
لذلك هذا السكربت يشغّل نظام Linux صغير (Debian) داخل تطبيق **Termux**، ويثبّت فيه
Java 8، ويعرض البرنامج على شاشة افتراضية (VNC) تفتحها من الجوال نفسه.

## المتطلبات
- جوال أندرويد **64-bit** (arm64)، وفيه **4GB RAM** على الأقل، و**3GB** مساحة فارغة.
- تطبيق **Termux** من F-Droid (نسخة Google Play قديمة ولا تشتغل).
- تطبيق عارض VNC مثل **AVNC** أو **RealVNC Viewer**.

## التثبيت (مرة واحدة)
داخل Termux:
```bash
curl -LO https://raw.githubusercontent.com/dvb4h/newone/claude/amazing-lamport-rttgyw/termux/install-asycuda.sh
bash install-asycuda.sh
```
(إذا المستودع خاص، انسخ الملف `install-asycuda.sh` للجوال يدوياً.)

## التشغيل
1. في Termux اكتب: `asycuda`
2. افتح تطبيق VNC واتصل بـ `localhost:5901` (بدون كلمة مرور).
3. راح تطلع شاشة دخول أسيكودا، وتدخل باسم المستخدم وكلمة المرور مالتك.

للإيقاف: `asycuda-stop`

## ملاحظات
- أول تشغيل يكون بطيء لأن Java تحمّل أكثر من 130 مكتبة.
- إذا ظهر خطأ، راجع ملف السجل: `proot-distro login debian -- cat /root/asycuda/asycuda.log`
- لتحديث مكتبات البرنامج بعد تحديث السيرفر، أعد تشغيل `bash install-asycuda.sh`.
- قد لا يقبل السيرفر الاتصال إلا من داخل العراق.
