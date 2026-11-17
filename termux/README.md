# محرك أسيكودا المفتوح — المرحلة 1 (التجربة على الجوال)

يشغّل برنامج **أسيكودا العالمي (العراق)** على أندرويد باستخدام مكونات مفتوحة المصدر فقط:

| المكوّن | الوظيفة |
|---|---|
| Termux + proot-distro (Debian) | بيئة Linux داخل الجوال |
| Eclipse Temurin **Java 8** | تشغيل برنامج أسيكودا |
| **Termux:X11** | شاشة عرض الواجهة (Swing) |
| `asycuda-jnlp-shim.jar` (مكتبتنا — `engine/jnlp-shim`) | بديل مكتبة `javax.jnlp` الخاصة بـ Java Web Start |

مكتبات أسيكودا (131 ملف `.jar`) **لا تُضمَّن** — تُنزَّل مباشرة من سيرفر الوزارة `asy.mof.gov.iq`.

## المتطلبات
- جوال أندرويد 64-bit، رام 4GB أو أكثر، 3GB مساحة فارغة.
- **اتصال إنترنت عراقي** (يفضّل بيانات الجوال 4G).
- تطبيق **Termux** من F-Droid: https://f-droid.org/packages/com.termux/
- تطبيق **Termux:X11** (ملف `app-arm64-v8a-debug.apk`): https://github.com/termux/termux-x11/releases/tag/nightly

## التثبيت (مرة واحدة)
انسخ `install-asycuda.sh` للجوال، ثم في Termux:
```bash
termux-setup-storage
bash ~/storage/downloads/install-asycuda.sh
```

## الأوامر
| الأمر | الوظيفة |
|---|---|
| `asycuda` | تشغيل أسيكودا على شاشة Termux:X11 |
| `asycuda-vnc` | تشغيل على VNC (بديل إذا لم يعمل X11) — اتصل بـ `localhost:5901` |
| `asycuda-check` | فحص DNS + HTTPS + منفذ 2006 |
| `asycuda-log` | عرض السجل ونسخه إلى `Download/asycuda.log` |
| `asycuda-update` | إعادة تنزيل مكتبات أسيكودا (بعد تحديث الوزارة) |
| `asycuda-stop` | إيقاف كل شيء |

## عند حدوث مشكلة
شغّل `asycuda-check` ثم `asycuda-log`، وأرسل الناتج (أو ملف `Download/asycuda.log`).

## للمطوّرين
بعد تعديل `engine/jnlp-shim` أو `termux/install-asycuda.template.sh` شغّل:
```bash
engine/build.sh
```
(يولّد `termux/install-asycuda.sh` مع المكتبة مدمجة بداخله.)
