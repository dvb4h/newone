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
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
kvBpjOFFQ14QaxRIXYv0W0fa0zrmaVX9P9Gf84XD2ZMLkR31yiQRv6zTb2CzLp3aEPXPP1BLBwio
ex8GugIAAPkEAABQSwMECgAACAAA0olxXQAAAAAAAAAAAAAAAAYAAABqYXZheC9QSwMECgAACAAA
0olxXQAAAAAAAAAAAAAAAAsAAABqYXZheC9qbmxwL1BLAwQUAAgICADSiXFdAAAAAAAAAAAAAAAA
HQAAAGphdmF4L2pubHAvQmFzaWNTZXJ2aWNlLmNsYXNzVY49bsJAEIXfAsH8RqFAXME0bJMuHYmo
kJBiISQ6swywltm1dm3I2Sg4AIdCmXWVTDGj0fvmzXs8b3cA73iN0BCYZOkl/ZGZyQs5T71WCbmL
VhShJfAWRJmn5ihXu4xUKdA/Uvlp98QsMRBPlzVjqJTr7+WHQFf71eGQa8NyM55uBQb+ZK9fVlVn
Muwwiv+fBGSs/YZ2c2evnlxSFYV1Je0FeomtnKKFztlt9DffLHi0BfgJQrU47gvaCLEjdOrZRa+e
/bAzOeDewPAXUEsHCOWZF5bMAAAAAgEAAFBLAwQUAAgICADSiXFdAAAAAAAAAAAAAAAAIQAAAGph
dmF4L2pubHAvQ2xpcGJvYXJkU2VydmljZS5jbGFzc42OuwrCQBBF70RNfDQ2VvY+GrexswxYCRaK
/SSOkrBsZLNGv83CD/CjxKxYiJVTXS73DOfxvN0BzNGLEBCGOVd8VbnRJxXr7JQUbPcbsVWWSoQm
oe8HSrM5qnWSS+oIvaO4uDBOjCsJo8l09d7wxak9O3aWTXkQq7afwImWRY2V39h48g813RG6m+Js
U1lmWgiDX8mZ/xISCA34C2rnFkJ49wjtuiF0fI/uC1BLBwgMVsqSqwAAAPsAAABQSwMEFAAICAgA
0olxXQAAAAAAAAAAAAAAACAAAABqYXZheC9qbmxwL0Rvd25sb2FkU2VydmljZS5jbGFzc51U207C
QBA9qyiKeOWi4v0SU17si5ooj6LGpAlEIkZ9qmXFJbU13Yp8mw9+gB9l3C0g2pbYdB920jNzZjpn
Jvv59f4B4AC7SYwQFFp6W++oLct8Ucv2m2XaeqNGnTYzaBIJgjnpV03daqqVhxY1XAExfkW5/eoY
9FQ3nmiDYEfRvDiLuur1lVbSBqya6zCrWSreEaQZr+qO2yfllPCwvHIf7sgxftZxqcWZbf1OdPhv
9fB8R//yhvxIWqrU14DgIlr9cJU1xkVL1CkV6wSps45BX1zRH09iniDjZWK2eln58RBMSLoUgOA4
RMOoxU7CdI5KnpeOP9MguI0xh6j17uLMKmryGYc+2206mGiEfZbT6tK6zYduc33YNgtHpsv2aRhr
l+txd1kQl5rULdNH/dV0q47ddCjnN8xq2G8Ee0oxioJCiJqn2zkzhXZZX9y+TDFOQDAKeebEqzKG
ccjXJYmJnp30bApTPZv27DRmBG9WsBLCSuYCMgEk60NyyAeQRR+yhGUfUsBKAFn1IWtYDyAbPmQT
W+KLYFvcI9j5BlBLBwgg3rtSngEAAHAFAABQSwMEFAAICAgA0olxXQAAAAAAAAAAAAAAACgAAABq
YXZheC9qbmxwL0Rvd25sb2FkU2VydmljZUxpc3RlbmVyLmNsYXNzhVBNa8JAEH3jV9Ra8Qf0VKno
xb305kkoghIoNLT3bXaIG5ZN2Kyxv62H/oD+qNJNEHoqzmFmmHnvzcf3z+cXgEdMI3QI97ms5YfI
rSnFU3G2ppAqYVfrlGNdebbsIvQIswYnjLSZeH7POfWEYemKzHFVERbLuO1b9uL1Jd7Ef+jEO22z
zeGwX70RxrU0WkkfSkHzVGZOqpBvXXrUNRMergrtW52puuy6k9qwIsyvEtvxSXFyKe8Ch3D3z73r
hjogELporBfO72OA5g3RJQ4xauMYNwFBmATfwe0vUEsHCHVnoB/bAAAAXQEAAFBLAwQUAAgICADS
iXFdAAAAAAAAAAAAAAAAIAAAAGphdmF4L2pubHAvRXh0ZW5kZWRTZXJ2aWNlLmNsYXNzfY/LCsJA
DEVvfPXhA0FXfkFFcDbuXEoFQXDh0lVtg7SUmdLW0m9z4Qf4UeKMoogLAyHk3uSQ3O6XK4AFBhYa
hEkSVEEtEplmwq9LlhFHe86rOGQLLcLQ+CIN5EnsjgmHJcFWGct1nDJh6m2ffqyEEZbT7RfOKCsl
NbMslgTXr0POyljJwoJDGL03N7uPQ3De8IIw8w4/+MM//l6d85Bfh41/fpmbvQ6B0ISJhn6tjY7u
Ld21dLW14qL7rejsmVn0H1BLBwj3NfsdwQAAADUBAABQSwMEFAAICAgA0olxXQAAAAAAAAAAAAAA
AB0AAABqYXZheC9qbmxwL0ZpbGVDb250ZW50cy5jbGFzc2VRy07CQBQ9g0gBKw9BEb+gbOwGV66M
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
Wx6sTLVUdYZZkqU9ZB1spChQ/YvsDSZYn+oYqVZeVC3MYyHTWsumKaVaWp1ULt5lT5KdesrWiV5M
gaU/UEsHCGUe9NLCAQAAOAMAAFBLAwQUAAgICADSiXFdAAAAAAAAAAAAAAAAIwAAAGphdmF4L2pu
bHAvU2VydmljZU1hbmFnZXJTdHViLmNsYXNzZU+7jsJADBzzSIADjgZR0SJoSHMdNVRwV0RXUW0i
K9qwbKKwQXzbFfcBfBTCkRAgcGPPeEZjny9//wC+0PdRI4xTdVSnILUmD0IujjrmjbIq4SJ0ZeSj
QRhUksAomwQ/UcqxI3gmy3ZlTphM149t6Aptk8Vs/WpYEDrLU8y505k9+GiL8Sn318qsjYoM3064
iwmfCbsb+632fCAMp7Pte6pEhFlZxLzShgmj92fmlccjEOqoqia/NeEJ9gU1pLeE6eBDEKFbKdC7
AlBLBwhhXQ0oygAAAC8BAABQSwMEFAAICAgA0olxXQAAAAAAAAAAAAAAACcAAABqYXZheC9qbmxw
L1NpbmdsZUluc3RhbmNlTGlzdGVuZXIuY2xhc3M79W/XPgYGBhMGTnYGJkYGxazEssQK/ay8nAL9
4My89JxUz7ziksS85FSfzOKS1LzUInYGFkYGAZAy/ZzEvHR9/6Ss1OQSRgbevNRyx+SSzLLEksz8
PEYGMY1oH4Sq4JIioGnWmmGMDFzB+aVFyalumTmpjAzS2C3RA+lkY2RgZGBmAAFGoJ2sDGwgFgM7
kGRi4AAAUEsHCJ9i0VqUAAAAuQAAAFBLAwQUAAgICADSiXFdAAAAAAAAAAAAAAAAJgAAAGphdmF4
L2pubHAvU2luZ2xlSW5zdGFuY2VTZXJ2aWNlLmNsYXNzO/Vv1z4GBgYTBi52BiZGBoWsxLLECv2s
vJwC/eDMvPScVM+84pLEvOTU4NSisszkVHYGFkYGAZAq/ZzEvHR9/6Ss1OQSRgbJxJQUVA0+mcUl
qXmpRYwMaho+OI2FqbLWDGNkkClKzc0vS8VlDldwfmlRcqpbZk4qI4MUVufpgSxiY2RgZGBmAAEm
oGtZGdgYQK5mB9FAGQ6QOAMnAFBLBwi57tm3nQAAAPoAAABQSwMEFAAICAgA0olxXQAAAAAAAAAA
AAAAACwAAABqYXZheC9qbmxwL1VuYXZhaWxhYmxlU2VydmljZUV4Y2VwdGlvbi5jbGFzczv1b9c+
BgYGEwYBLgYmBmZ2BhYeBlYGNkYG4azEskT9nMS8dH3XiuTUgpLM/DxGBjabzLzMEjtGBmYNzTCQ
Dg6Qck5GBlENH4SG4JKizLx0a80wdgZuRgY1kESFflZeToF+aB6QnZmTmJSTGpxaVJaZnIpkOItz
fkoqIwO/T2Zeql9pblJqUQhIISMDV3B+aVFyqlsmiKOAxww9kFUMigwgl4EAEwMjyDdAkgfIkwXS
jECaVWs7A+NGIIORgRdIsoEFmcFKOaFK5YBaQUawaWlvZ2BHV8sCJPnAxvMDAFBLBwgJ8esF3gAA
AEABAABQSwECCgAKAAAIAADSiXFdAAAAAAAAAAAAAAAACQAEAAAAAAAAAAAAAAAAAAAATUVUQS1J
TkYv/soAAFBLAQIUABQACAgIANKJcV1T+4TlOgAAADkAAAAUAAAAAAAAAAAAAAAAACsAAABNRVRB
LUlORi9NQU5JRkVTVC5NRlBLAQIKAAoAAAgAANKJcV0AAAAAAAAAAAAAAAAIAAAAAAAAAAAAAAAA
AKcAAABhc3ljdWRhL1BLAQIKAAoAAAgAANKJcV0AAAAAAAAAAAAAAAANAAAAAAAAAAAAAAAAAM0A
AABhc3ljdWRhL3NoaW0vUEsBAhQAFAAICAgA0olxXZe0ckECAwAAmAUAACsAAAAAAAAAAAAAAAAA
+AAAAGFzeWN1ZGEvc2hpbS9TaGltU2VydmljZU1hbmFnZXJTdHViJDEuY2xhc3NQSwECFAAUAAgI
CADSiXFdqHsfBroCAAD5BAAAKQAAAAAAAAAAAAAAAABTBAAAYXN5Y3VkYS9zaGltL1NoaW1TZXJ2
aWNlTWFuYWdlclN0dWIuY2xhc3NQSwECCgAKAAAIAADSiXFdAAAAAAAAAAAAAAAABgAAAAAAAAAA
AAAAAABkBwAAamF2YXgvUEsBAgoACgAACAAA0olxXQAAAAAAAAAAAAAAAAsAAAAAAAAAAAAAAAAA
iAcAAGphdmF4L2pubHAvUEsBAhQAFAAICAgA0olxXeWZF5bMAAAAAgEAAB0AAAAAAAAAAAAAAAAA
sQcAAGphdmF4L2pubHAvQmFzaWNTZXJ2aWNlLmNsYXNzUEsBAhQAFAAICAgA0olxXQxWypKrAAAA
+wAAACEAAAAAAAAAAAAAAAAAyAgAAGphdmF4L2pubHAvQ2xpcGJvYXJkU2VydmljZS5jbGFzc1BL
AQIUABQACAgIANKJcV0g3rtSngEAAHAFAAAgAAAAAAAAAAAAAAAAAMIJAABqYXZheC9qbmxwL0Rv
d25sb2FkU2VydmljZS5jbGFzc1BLAQIUABQACAgIANKJcV11Z6Af2wAAAF0BAAAoAAAAAAAAAAAA
AAAAAK4LAABqYXZheC9qbmxwL0Rvd25sb2FkU2VydmljZUxpc3RlbmVyLmNsYXNzUEsBAhQAFAAI
CAgA0olxXfc1+x3BAAAANQEAACAAAAAAAAAAAAAAAAAA3wwAAGphdmF4L2pubHAvRXh0ZW5kZWRT
ZXJ2aWNlLmNsYXNzUEsBAhQAFAAICAgA0olxXfFhjfA4AQAAVgIAAB0AAAAAAAAAAAAAAAAA7g0A
AGphdmF4L2pubHAvRmlsZUNvbnRlbnRzLmNsYXNzUEsBAhQAFAAICAgA0olxXQUjvJjLAAAAcgEA
ACAAAAAAAAAAAAAAAAAAcQ8AAGphdmF4L2pubHAvRmlsZU9wZW5TZXJ2aWNlLmNsYXNzUEsBAhQA
FAAICAgA0olxXWELoMPcAAAArgEAACAAAAAAAAAAAAAAAAAAihAAAGphdmF4L2pubHAvRmlsZVNh
dmVTZXJ2aWNlLmNsYXNzUEsBAhQAFAAICAgA0olxXbaOSN7nAAAAiAEAACMAAAAAAAAAAAAAAAAA
tBEAAGphdmF4L2pubHAvSW50ZWdyYXRpb25TZXJ2aWNlLmNsYXNzUEsBAhQAFAAICAgA0olxXVOR
Zu0SAQAA1AEAACUAAAAAAAAAAAAAAAAA7BIAAGphdmF4L2pubHAvSk5MUFJhbmRvbUFjY2Vzc0Zp
bGUuY2xhc3NQSwECFAAUAAgICADSiXFd2VKX/HUBAACwAgAAIwAAAAAAAAAAAAAAAABRFAAAamF2
YXgvam5scC9QZXJzaXN0ZW5jZVNlcnZpY2UuY2xhc3NQSwECFAAUAAgICADSiXFdkyfx+csAAABe
AQAAHQAAAAAAAAAAAAAAAAAXFgAAamF2YXgvam5scC9QcmludFNlcnZpY2UuY2xhc3NQSwECFAAU
AAgICADSiXFdZR700sIBAAA4AwAAHwAAAAAAAAAAAAAAAAAtFwAAamF2YXgvam5scC9TZXJ2aWNl
TWFuYWdlci5jbGFzc1BLAQIUABQACAgIANKJcV1hXQ0oygAAAC8BAAAjAAAAAAAAAAAAAAAAADwZ
AABqYXZheC9qbmxwL1NlcnZpY2VNYW5hZ2VyU3R1Yi5jbGFzc1BLAQIUABQACAgIANKJcV2fYtFa
lAAAALkAAAAnAAAAAAAAAAAAAAAAAFcaAABqYXZheC9qbmxwL1NpbmdsZUluc3RhbmNlTGlzdGVu
ZXIuY2xhc3NQSwECFAAUAAgICADSiXFdue7Zt50AAAD6AAAAJgAAAAAAAAAAAAAAAABAGwAAamF2
YXgvam5scC9TaW5nbGVJbnN0YW5jZVNlcnZpY2UuY2xhc3NQSwECFAAUAAgICADSiXFdCfHrBd4A
AABAAQAALAAAAAAAAAAAAAAAAAAxHAAAamF2YXgvam5scC9VbmF2YWlsYWJsZVNlcnZpY2VFeGNl
cHRpb24uY2xhc3NQSwUGAAAAABkAGQBfBwAAaR0AAAAA
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
