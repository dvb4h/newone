#!/bin/bash
# يبني مكتبة jnlp-shim ويدمجها داخل termux/install-asycuda.sh
set -e
cd "$(dirname "$0")/.."
OUT=$(mktemp -d)
javac --release 8 -encoding UTF-8 -nowarn -d "$OUT" $(find engine/jnlp-shim/src -name '*.java')
(cd "$OUT" && jar cf "$OLDPWD/engine/jnlp-shim/asycuda-jnlp-shim.jar" .)
rm -rf "$OUT"
python3 - <<'PY'
import base64
b64 = base64.encodebytes(open('engine/jnlp-shim/asycuda-jnlp-shim.jar','rb').read()).decode().strip()
t = open('termux/install-asycuda.template.sh', encoding='utf-8').read()
open('termux/install-asycuda.sh', 'w', encoding='utf-8').write(t.replace('__SHIM_B64__', b64))
PY
chmod +x termux/install-asycuda.sh
echo "built termux/install-asycuda.sh"
