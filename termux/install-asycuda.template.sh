#!/data/data/com.termux/files/usr/bin/bash
# =====================================================================
#  محرك أسيكودا المفتوح - المرحلة 1
#  تشغيل برنامج أسيكودا العالمي (العراق) على أندرويد عبر:
#    Termux + Termux:X11 + Debian (proot) + Java 8 + مكتبة jnlp-shim خاصة بنا
#
#  التثبيت:   bash install-asycuda.sh
#  الأوامر بعد التثبيت:
#     asycuda          تشغيل البرنامج على شاشة Termux:X11
#     asycuda-vnc      تشغيل البرنامج على شاشة VNC (بديل)
#     asycuda-stop     إيقاف البرنامج
#     asycuda-check    فحص الاتصال بسيرفر الوزارة
#     asycuda-log      عرض سجل الأخطاء ونسخه لمجلد التنزيلات
#     asycuda-update   إعادة تنزيل مكتبات أسيكودا من السيرفر
# =====================================================================
set -e

DISTRO="debian"
JNLP_URL="https://asy.mof.gov.iq/aw/AWIQWorld.jnlp"
ROOTFS="$PREFIX/var/lib/proot-distro/installed-rootfs/$DISTRO"

echo "==> [1/5] تثبيت أدوات Termux (proot-distro + termux-x11) ..."
pkg update -y
pkg install -y x11-repo
pkg install -y proot-distro termux-x11-nightly coreutils

if [ ! -d "$ROOTFS" ]; then
    echo "==> [2/5] تنزيل نظام Debian (عدة دقائق) ..."
    proot-distro install "$DISTRO"
else
    echo "==> [2/5] Debian مثبّت مسبقاً"
fi

echo "==> [3/5] نسخ مكتبة jnlp-shim ..."
mkdir -p "$ROOTFS/opt/asycuda"
base64 -d > "$ROOTFS/opt/asycuda/asycuda-jnlp-shim.jar" <<'SHIM'
__SHIM_B64__
SHIM

echo "==> [4/5] تجهيز Debian: Java 8 + خطوط عربية + أدوات ..."
cat > "$ROOTFS/root/asy-setup.sh" <<'SETUP'
#!/bin/bash
set -e
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends \
    wget curl ca-certificates python3 procps fontconfig \
    fonts-dejavu-core fonts-noto-core \
    openbox xterm libxext6 libxrender1 libxtst6 libxi6 libfreetype6 \
    tigervnc-standalone-server tigervnc-tools

# ---------- Java 8 (Eclipse Temurin) ----------
if [ ! -x /opt/java8/bin/java ]; then
    case "$(uname -m)" in
        aarch64|arm64) JARCH=aarch64 ;;
        armv7l|armv8l|arm) JARCH=arm ;;
        x86_64) JARCH=x64 ;;
        *) echo "معمارية غير مدعومة: $(uname -m)"; exit 1 ;;
    esac
    echo "تنزيل Java 8 ($JARCH) ..."
    wget -q --show-progress -O /tmp/jre8.tar.gz \
        "https://api.adoptium.net/v3/binary/latest/8/ga/linux/$JARCH/jre/hotspot/normal/eclipse"
    mkdir -p /opt/java8
    tar -xzf /tmp/jre8.tar.gz -C /opt/java8 --strip-components=1
    rm -f /tmp/jre8.tar.gz
fi
/opt/java8/bin/java -version

# ---------- asy-update: تنزيل JNLP والمكتبات ----------
cat > /usr/local/bin/asy-update <<'EOF'
#!/bin/bash
set -e
JNLP_URL="${1:-https://asy.mof.gov.iq/aw/AWIQWorld.jnlp}"
mkdir -p /root/asycuda && cd /root/asycuda
echo "تنزيل $JNLP_URL ..."
if ! wget -q -O AWIQWorld.jnlp.new "$JNLP_URL"; then
    rm -f AWIQWorld.jnlp.new
    echo "❌ تعذّر الوصول إلى سيرفر الوزارة."
    echo "   السيرفر لا يعمل إلا من داخل العراق، وبعض شبكات الواي فاي محجوبة - جرّب بيانات الجوال 4G."
    exit 1
fi
mv AWIQWorld.jnlp.new AWIQWorld.jnlp

# استخراج: المكتبات، الوسائط، الكلاس الرئيسي، الخصائص، عنوان الكود
python3 - AWIQWorld.jnlp <<'PY'
import sys, xml.etree.ElementTree as ET
root = ET.parse(sys.argv[1]).getroot()
codebase = root.get('codebase', 'https://asy.mof.gov.iq/aw/')
if not codebase.endswith('/'): codebase += '/'
open('codebase.txt', 'w').write(codebase + '\n')
open('jars.txt', 'w').write(''.join(j.get('href') + '\n' for j in root.iter('jar')))
app = root.find('application-desc')
open('main.txt', 'w').write(app.get('main-class') + '\n')
open('args.txt', 'w').write(''.join((a.text or '').strip() + '\n' for a in app.findall('argument')))
skip = {'java.util.logging.config.file', 'jnlp.packEnabled'}
props = ['-D%s=%s' % (p.get('name'), p.get('value')) for p in root.iter('property') if p.get('name') not in skip]
open('props.txt', 'w').write(''.join(p + '\n' for p in props))
PY

CODEBASE=$(cat codebase.txt)
TOTAL=$(grep -c . jars.txt)
echo "تنزيل $TOTAL مكتبة من $CODEBASE ..."

fetch_one() {
    local JAR="$1" CODEBASE="$2"
    mkdir -p "$(dirname "$JAR")"
    if wget -q -O "$JAR.tmp" "$CODEBASE$JAR" && python3 -c "import zipfile,sys; sys.exit(0 if zipfile.is_zipfile('$JAR.tmp') else 1)"; then
        mv "$JAR.tmp" "$JAR"; echo "ok $JAR"; return 0
    fi
    rm -f "$JAR.tmp"
    if wget -q -O "$JAR.pack.gz" "$CODEBASE$JAR.pack.gz" && /opt/java8/bin/unpack200 "$JAR.pack.gz" "$JAR"; then
        rm -f "$JAR.pack.gz"; echo "ok $JAR (pack200)"; return 0
    fi
    rm -f "$JAR.pack.gz"; echo "FAIL $JAR"; return 0
}
export -f fetch_one
xargs -a jars.txt -P 6 -I{} bash -c 'fetch_one "$1" "$2"' _ {} "$CODEBASE" > download.log
OK=$(grep -c '^ok' download.log || true)
echo "✅ تم تنزيل $OK من $TOTAL"
if grep -q '^FAIL' download.log; then
    echo "❌ فشل تنزيل:"; grep '^FAIL' download.log; exit 1
fi
EOF
chmod +x /usr/local/bin/asy-update

# ---------- asy-run: تشغيل البرنامج ----------
cat > /usr/local/bin/asy-run <<'EOF'
#!/bin/bash
MODE="${1:-x11}"
cd /root/asycuda || { echo "شغّل asycuda-update أولاً"; exit 1; }
[ -s jars.txt ] || { echo "المكتبات غير موجودة - شغّل asycuda-update"; exit 1; }
export USER=root HOME=/root LANG=C.UTF-8

if [ "$MODE" = "vnc" ]; then
    export DISPLAY=:1
    vncserver -kill :1 >/dev/null 2>&1 || true
    rm -f /tmp/.X1-lock /tmp/.X11-unix/X1
    vncserver :1 -geometry 1600x900 -depth 24 -localhost yes -SecurityTypes None -xstartup /usr/bin/openbox-session
    echo "افتح تطبيق VNC واتصل بـ localhost:5901"
else
    export DISPLAY=:0
    for i in $(seq 1 20); do [ -e /tmp/.X11-unix/X0 ] && break; sleep 0.5; done
    [ -e /tmp/.X11-unix/X0 ] || { echo "❌ شاشة Termux:X11 غير جاهزة. تأكد أن تطبيق Termux:X11 مثبّت."; exit 1; }
    pgrep -x openbox >/dev/null || (openbox >/dev/null 2>&1 &)
fi

CP="/opt/asycuda/asycuda-jnlp-shim.jar:$(grep . jars.txt | paste -sd: -)"
MAIN=$(cat main.txt)
mapfile -t ARGS < <(grep . args.txt)
mapfile -t PROPS < <(grep . props.txt)

echo "تشغيل أسيكودا ... (السجل: /root/asycuda/asycuda.log)"
/opt/java8/bin/java \
    -Xms256m -Xmx1024m \
    -Djava.io.tmpdir=/tmp \
    -Dfile.encoding=UTF-8 \
    -Dawt.useSystemAAFontSettings=on -Dswing.aatext=true \
    -Djava.net.preferIPv4Stack=true \
    -Djnlp.codebase="$(cat codebase.txt)" \
    "${PROPS[@]}" \
    -cp "$CP" "$MAIN" "${ARGS[@]}" 2>&1 | tee asycuda.log
echo "انتهى البرنامج (رمز الخروج: ${PIPESTATUS[0]})"
EOF
chmod +x /usr/local/bin/asy-run

# ---------- asy-check: فحص الاتصال ----------
cat > /usr/local/bin/asy-check <<'EOF'
#!/bin/bash
HOST=asy.mof.gov.iq; PORT=2006
if [ -s /root/asycuda/args.txt ]; then
    R=$(grep -o '//[^/:]*:[0-9]*' /root/asycuda/args.txt | head -1)
    [ -n "$R" ] && HOST=${R#//} && PORT=${HOST#*:} && HOST=${HOST%:*}
fi
echo "== فحص الاتصال بـ $HOST =="
if IP=$(getent hosts "$HOST" | awk '{print $1}' | head -1) && [ -n "$IP" ]; then
    echo "✅ DNS: $IP"
else
    echo "❌ DNS: لا يمكن إيجاد السيرفر"; exit 1
fi
CODE=$(curl -s -o /dev/null -m 15 -w '%{http_code}' "https://$HOST/aw/AWIQWorld.jnlp")
[ "$CODE" = "200" ] && echo "✅ HTTPS (443): يعمل" || echo "❌ HTTPS (443): فشل (الرمز $CODE)"
if timeout 10 bash -c "echo > /dev/tcp/$HOST/$PORT" 2>/dev/null; then
    echo "✅ منفذ أسيكودا ($PORT): مفتوح"
else
    echo "❌ منفذ أسيكودا ($PORT): مغلق - جرّب بيانات الجوال 4G بدل الواي فاي"
fi
echo "Java: $(/opt/java8/bin/java -version 2>&1 | head -1)"
echo "المكتبات: $(ls /root/asycuda/lib 2>/dev/null | wc -l) ملف في lib/"
EOF
chmod +x /usr/local/bin/asy-check
SETUP

proot-distro login "$DISTRO" -- bash /root/asy-setup.sh

echo "==> [5/5] إنشاء أوامر التشغيل ..."
cat > "$PREFIX/bin/asycuda" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
termux-wake-lock 2>/dev/null || true
pkill -f "com.termux.x11" 2>/dev/null || true
termux-x11 :0 >/dev/null 2>&1 &
sleep 2
am start --user 0 -n com.termux.x11/com.termux.x11.MainActivity >/dev/null 2>&1 || true
proot-distro login $DISTRO --shared-tmp -- asy-run x11
EOF
cat > "$PREFIX/bin/asycuda-vnc" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
termux-wake-lock 2>/dev/null || true
proot-distro login $DISTRO -- asy-run vnc
EOF
cat > "$PREFIX/bin/asycuda-stop" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
proot-distro login $DISTRO --shared-tmp -- bash -c 'pkill -f java; pkill openbox; vncserver -kill :1' >/dev/null 2>&1 || true
pkill -f "com.termux.x11" 2>/dev/null || true
termux-wake-unlock 2>/dev/null || true
echo "تم الإيقاف"
EOF
cat > "$PREFIX/bin/asycuda-check" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
proot-distro login $DISTRO -- asy-check
EOF
cat > "$PREFIX/bin/asycuda-update" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
proot-distro login $DISTRO -- asy-update "$JNLP_URL"
EOF
cat > "$PREFIX/bin/asycuda-log" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
LOG="$ROOTFS/root/asycuda/asycuda.log"
[ -f "\$LOG" ] || { echo "لا يوجد سجل بعد"; exit 0; }
tail -n 80 "\$LOG"
if [ -d "\$HOME/storage/downloads" ]; then
    cp "\$LOG" "\$HOME/storage/downloads/asycuda.log" && echo "" && echo "📄 تم نسخ السجل إلى: Download/asycuda.log"
else
    echo "" && echo "لنسخ السجل لمجلد التنزيلات شغّل مرة واحدة: termux-setup-storage"
fi
EOF
chmod +x "$PREFIX/bin/asycuda" "$PREFIX/bin/asycuda-vnc" "$PREFIX/bin/asycuda-stop" \
         "$PREFIX/bin/asycuda-check" "$PREFIX/bin/asycuda-update" "$PREFIX/bin/asycuda-log"

echo ""
echo "==> تنزيل مكتبات أسيكودا من سيرفر الوزارة ..."
asycuda-update || echo "⚠️  لم يكتمل التنزيل - شغّل asycuda-update لاحقاً من شبكة عراقية."

echo ""
echo "✅ اكتمل التثبيت"
echo "   1) تأكد أن تطبيق Termux:X11 مثبّت على الجوال"
echo "   2) اكتب:  asycuda"
