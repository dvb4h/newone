#!/data/data/com.termux/files/usr/bin/bash
# =====================================================================
#  تشغيل برنامج أسيكودا العالمي (ASYCUDA World - العراق) على أندرويد
#  عبر Termux + Debian (proot) + Java 8 + شاشة VNC
#
#  طريقة التشغيل داخل Termux:
#     bash install-asycuda.sh          (التثبيت لأول مرة فقط)
#     asycuda                          (تشغيل البرنامج بعد التثبيت)
#     asycuda-stop                     (إيقاف البرنامج وشاشة VNC)
# =====================================================================
set -e

CODEBASE="https://asy.mof.gov.iq/aw/"
JNLP_NAME="AWIQWorld.jnlp"
DISTRO="debian"

echo "==> [1/4] تحديث Termux وتثبيت proot-distro ..."
pkg update -y
pkg install -y proot-distro

if [ ! -d "$PREFIX/var/lib/proot-distro/installed-rootfs/$DISTRO" ]; then
    echo "==> [2/4] تنزيل نظام Debian (قد يأخذ عدة دقائق) ..."
    proot-distro install "$DISTRO"
else
    echo "==> [2/4] Debian مثبّت مسبقاً"
fi

echo "==> [3/4] تجهيز Debian: Java 8 + VNC + خطوط عربية + ملفات أسيكودا ..."
ROOTFS="$PREFIX/var/lib/proot-distro/installed-rootfs/$DISTRO"
cat > "$ROOTFS/root/asy-setup.sh" <<INNER
#!/bin/bash
set -e
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y wget ca-certificates fontconfig fonts-dejavu fonts-noto-core \
    tigervnc-standalone-server tigervnc-tools openbox xterm python3 libxtst6 libxi6 libxrender1

# ---- Java 8 (Temurin) حسب معمارية الجوال ----
ARCH=\$(uname -m)
case "\$ARCH" in
    aarch64|arm64) JARCH=aarch64 ;;
    armv7l|armv8l|arm) JARCH=arm ;;
    x86_64) JARCH=x64 ;;
    *) echo "معمارية غير مدعومة: \$ARCH"; exit 1 ;;
esac
if [ ! -x /opt/java8/bin/java ]; then
    echo "تنزيل Java 8 للمعمارية \$JARCH ..."
    wget -q --show-progress -O /tmp/jre8.tar.gz \
      "https://api.adoptium.net/v3/binary/latest/8/ga/linux/\$JARCH/jre/hotspot/normal/eclipse"
    mkdir -p /opt/java8
    tar -xzf /tmp/jre8.tar.gz -C /opt/java8 --strip-components=1
    rm -f /tmp/jre8.tar.gz
fi
/opt/java8/bin/java -version

# ---- تنزيل ملف JNLP ومكتبات أسيكودا من السيرفر ----
mkdir -p /root/asycuda && cd /root/asycuda
wget -q -O "$JNLP_NAME" "${CODEBASE}${JNLP_NAME}" || {
    echo "تعذّر الوصول إلى ${CODEBASE} - تأكد من الإنترنت (قد يحتاج السيرفر اتصالاً من داخل العراق أو VPN)"; exit 1; }

python3 - "$JNLP_NAME" > jars.txt <<'PY'
import sys, xml.etree.ElementTree as ET
root = ET.parse(sys.argv[1]).getroot()
for j in root.iter('jar'):
    print(j.get('href'))
PY

echo "عدد المكتبات: \$(wc -l < jars.txt)"
FAILED=0
while read -r JAR; do
    [ -z "\$JAR" ] && continue
    mkdir -p "\$(dirname "\$JAR")"
    if wget -q -O "\$JAR.tmp" "${CODEBASE}\$JAR"; then
        mv "\$JAR.tmp" "\$JAR"
    elif wget -q -O "\$JAR.pack.gz" "${CODEBASE}\$JAR.pack.gz"; then
        /opt/java8/bin/unpack200 "\$JAR.pack.gz" "\$JAR" && rm -f "\$JAR.pack.gz"
    else
        rm -f "\$JAR.tmp"; echo "فشل تنزيل: \$JAR"; FAILED=\$((FAILED+1))
    fi
done < jars.txt
echo "فشل تنزيل \$FAILED ملف"

# ---- إعداد VNC بدون كلمة مرور (يعمل فقط على الجوال نفسه localhost) ----
mkdir -p /root/.vnc
cat > /root/.vnc/xstartup <<'XS'
#!/bin/sh
exec openbox-session
XS
chmod +x /root/.vnc/xstartup

# ---- سكربت التشغيل داخل Debian ----
cat > /usr/local/bin/run-asycuda <<'RUN'
#!/bin/bash
cd /root/asycuda
export USER=root HOME=/root DISPLAY=:1
vncserver -kill :1 >/dev/null 2>&1 || true
rm -f /tmp/.X1-lock /tmp/.X11-unix/X1
vncserver :1 -geometry 1600x900 -depth 24 -localhost yes -SecurityTypes None
CP=\$(sed '/^\$/d' jars.txt | paste -sd: -)
echo "تشغيل أسيكودا... افتح تطبيق VNC Viewer واتصل بـ  localhost:5901"
/opt/java8/bin/java -Xms128m -Xmx1024m \
    -Dfile.encoding=UTF-8 -Dawt.useSystemAAFontSettings=on \
    -Djava.util.logging.manager=so.util.logging.SOLogManager \
    -cp "\$CP" so.kernel.client.DesktopMain \
    https://asy.mof.gov.iq/aw/help/ //asy.mof.gov.iq:2006/ -dout 2>&1 | tee /root/asycuda/asycuda.log
RUN
chmod +x /usr/local/bin/run-asycuda
INNER

proot-distro login "$DISTRO" -- bash /root/asy-setup.sh

echo "==> [4/4] إنشاء أوامر التشغيل في Termux ..."
cat > "$PREFIX/bin/asycuda" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
termux-wake-lock 2>/dev/null || true
proot-distro login $DISTRO -- run-asycuda
EOF
cat > "$PREFIX/bin/asycuda-stop" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
proot-distro login $DISTRO -- bash -c 'pkill -f DesktopMain; vncserver -kill :1' || true
termux-wake-unlock 2>/dev/null || true
EOF
chmod +x "$PREFIX/bin/asycuda" "$PREFIX/bin/asycuda-stop"

echo ""
echo "تم التثبيت ✅"
echo "للتشغيل اكتب:   asycuda"
echo "ثم افتح تطبيق VNC Viewer واتصل بالعنوان:  localhost:5901"
