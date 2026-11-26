#!/usr/bin/env bash
# Yalnızca hostu kontrol eder, açık zincir tanımını indirir ve PUBLIC_IP kaydeder.
set -euo pipefail
umask 077

fail() { printf 'HATA: %s\n' "$*" >&2; exit 1; }

if [[ $# -gt 1 ]]; then
  fail 'Kullanım: bash scripts/prepare.sh [SUNUCUNUN_PUBLIC_IPV4_ADRESI]'
fi
if [[ "${1:-}" == '--help' || "${1:-}" == '-h' ]]; then
  printf '%s\n' 'Kullanım: bash scripts/prepare.sh [SUNUCUNUN_PUBLIC_IPV4_ADRESI]' \
    'İlk çalıştırmada dış IPv4 adresini verin. Mevcut .env dosyası değiştirilmez.'
  exit 0
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd -P)"
SPEC_FILE="$REPO_DIR/chain.raw.json"
ENV_FILE="$REPO_DIR/.env"
SPEC_SHA='485ecb44635609ab261ea3002c3c9fdc7a5dab38caf28a86f654cadf443893be'
SPEC_URL='https://github.com/flop-labs/network/releases/download/testnet/v0.1.0-early.1/flop_testnet-918abd58fb16306b.raw.json'
TMP_SPEC=''
trap 'if [[ -n "$TMP_SPEC" && -f "$TMP_SPEC" ]]; then rm -f -- "$TMP_SPEC"; fi' EXIT

[[ "$(uname -s)" == 'Linux' ]] || fail 'Bu hazırlık Linux sunucuda çalıştırılmalı.'
[[ "$(uname -m)" == 'x86_64' ]] || fail 'Linux amd64 (x86_64) sunucu gerekli.'
for tool in python3 curl sha256sum docker; do
  command -v "$tool" >/dev/null 2>&1 || fail "Gerekli araç bulunamadı: $tool. Bu script kurulum yapmaz."
done

docker_query() {
  python3 - "$@" <<'PY'
import subprocess
import sys
try:
    result = subprocess.run(['docker', *sys.argv[1:]], capture_output=True, text=True, timeout=15, check=False)
except (OSError, subprocess.TimeoutExpired):
    raise SystemExit(1)
if result.returncode != 0:
    raise SystemExit(1)
print(result.stdout.strip())
PY
}

if ! DOCKER_VERSION="$(docker_query version --format '{{.Server.Version}}')"; then
  fail 'Docker sunucusuna erişilemiyor. Docker servisinin çalıştığını ve kullanıcı yetkinizi kontrol edin.'
fi
if [[ "$DOCKER_VERSION" =~ ^([0-9]+)\. ]]; then
  [[ "${BASH_REMATCH[1]}" -ge 28 ]] || fail "Docker Engine 28 veya üstü gerekli; sunucu sürümü: $DOCKER_VERSION"
else
  fail 'Docker sunucu sürümü okunamadı.'
fi
if ! DOCKER_PLATFORM="$(docker_query info --format '{{.OSType}}/{{.Architecture}}')"; then
  fail 'Docker sunucusunun işletim sistemi ve mimarisi okunamadı.'
fi
[[ "$DOCKER_PLATFORM" == 'linux/x86_64' || "$DOCKER_PLATFORM" == 'linux/amd64' ]] || \
  fail "Docker sunucusu Linux amd64 olmalı; görülen: $DOCKER_PLATFORM"
if ! COMPOSE_VERSION="$(docker_query compose version --short)"; then
  fail 'Docker Compose eklentisi bulunamadı veya çalışmıyor.'
fi
if [[ "$COMPOSE_VERSION" =~ ^v?([0-9]+)\. ]]; then
  [[ "${BASH_REMATCH[1]}" -ge 2 ]] || fail 'Docker Compose v2 veya üstü gerekli.'
else
  fail 'Docker Compose sürümü okunamadı.'
fi

ENV_EXISTED=0
if [[ -e "$ENV_FILE" || -L "$ENV_FILE" ]]; then ENV_EXISTED=1; fi
PUBLIC_IP="$(python3 - "$ENV_FILE" "${1:-}" <<'PY'
import ipaddress
import os
from pathlib import Path
import re
import stat
import sys

def fail(message):
    print(f"HATA: {message}", file=sys.stderr)
    raise SystemExit(1)

path = Path(sys.argv[1])
requested = sys.argv[2].strip()
existing = None
if os.path.lexists(path):
    if not stat.S_ISREG(path.lstat().st_mode):
        fail('.env normal bir dosya olmalı; sembolik bağlantı kabul edilmez.')
    try:
        if path.stat().st_size > 65536:
            fail('.env dosyası beklenenden büyük.')
        lines = path.read_text(encoding='utf-8').splitlines()
    except (OSError, UnicodeError):
        fail('.env dosyası okunamadı.')
    values = []
    for line in lines:
        match = re.match(r'^\s*PUBLIC_IP\s*=\s*(.*?)\s*$', line)
        if match:
            value = match.group(1)
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                value = value[1:-1]
            values.append(value)
    if len(values) != 1:
        fail('Mevcut .env içinde tam bir PUBLIC_IP satırı olmalı. Dosyanız değiştirilmedi.')
    existing = values[0]
    if requested and requested != existing:
        fail('Verilen IPv4 mevcut .env ile farklı. Dosyanız değiştirilmedi; adresi elle kontrol edin.')

value = existing if existing is not None else requested
try:
    address = ipaddress.ip_address(value)
except ValueError:
    fail('Sunucunun dış IPv4 adresini verin: bash scripts/prepare.sh SUNUCU_IPV4')
if (not isinstance(address, ipaddress.IPv4Address) or not address.is_global
        or address.is_multicast or address.is_reserved or address.is_unspecified
        or address.is_loopback or address.is_link_local or address.is_private):
    fail('PUBLIC_IP internette yönlendirilebilir genel bir IPv4 olmalı; özel/NAT/örnek adres kullanmayın.')
if str(address) != value:
    fail('PUBLIC_IP standart IPv4 biçiminde olmalı.')
print(address)
PY
)"

if [[ -e "$SPEC_FILE" || -L "$SPEC_FILE" ]]; then
  [[ -f "$SPEC_FILE" && ! -L "$SPEC_FILE" ]] || fail 'chain.raw.json normal bir dosya olmalı; değiştirilmedi.'
  ACTUAL_SHA="$(sha256sum -- "$SPEC_FILE")"
  ACTUAL_SHA="${ACTUAL_SHA%% *}"
  [[ "$ACTUAL_SHA" == "$SPEC_SHA" ]] || fail 'Mevcut chain.raw.json resmi checksum ile eşleşmiyor. Üzerine yazılmadı.'
  chmod 644 "$SPEC_FILE"
  printf '%s\n' 'OK: Mevcut zincir tanımının SHA-256 değeri doğru.'
else
  TMP_SPEC="$(mktemp "$REPO_DIR/.chain.raw.json.XXXXXX")"
  printf '%s\n' 'Resmi Testnet zincir tanımı indiriliyor...'
  curl --fail --silent --show-error --location --proto '=https' --proto-redir '=https' \
    --connect-timeout 15 --max-time 15 --retry 0 --output "$TMP_SPEC" "$SPEC_URL" || \
    fail 'Zincir tanımı indirilemedi. .env oluşturulmadı; daha sonra tekrar deneyin.'
  ACTUAL_SHA="$(sha256sum -- "$TMP_SPEC")"
  ACTUAL_SHA="${ACTUAL_SHA%% *}"
  [[ "$ACTUAL_SHA" == "$SPEC_SHA" ]] || fail 'İndirilen zincir tanımının SHA-256 değeri yanlış. Dosya kullanılmadı.'
  # Zincir tanımı halka açıktır; konteynerin root olmayan kullanıcısı da okuyabilmeli.
  chmod 644 "$TMP_SPEC"
  # Aynı anda başka bir işlem dosyayı oluşturduysa onun üzerine yazılmaz.
  ln -- "$TMP_SPEC" "$SPEC_FILE" 2>/dev/null || fail 'chain.raw.json bu sırada oluşturuldu. Üzerine yazılmadı; tekrar kontrol edin.'
  rm -f -- "$TMP_SPEC"
  TMP_SPEC=''
  printf '%s\n' 'OK: Zincir tanımı indirildi ve SHA-256 doğrulandı.'
fi

python3 - "$ENV_FILE" "$PUBLIC_IP" "$ENV_EXISTED" <<'PY'
import os
from pathlib import Path
import re
import stat
import sys

path = Path(sys.argv[1])
if os.path.lexists(path):
    if sys.argv[3] != '1' or not stat.S_ISREG(path.lstat().st_mode):
        print('HATA: .env bu sırada değişti veya oluşturuldu. Üzerine yazılmadı.', file=sys.stderr)
        raise SystemExit(1)
    try:
        values = []
        for line in path.read_text(encoding='utf-8').splitlines():
            match = re.match(r'^\s*PUBLIC_IP\s*=\s*(.*?)\s*$', line)
            if match:
                value = match.group(1)
                if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                    value = value[1:-1]
                values.append(value)
    except (OSError, UnicodeError):
        print('HATA: Mevcut .env tekrar okunamadı; değiştirilmedi.', file=sys.stderr)
        raise SystemExit(1)
    if values != [sys.argv[2]]:
        print('HATA: .env bu sırada değişti. Dosyanızın üzerine yazılmadı.', file=sys.stderr)
        raise SystemExit(1)
    print('OK: Mevcut .env korundu.')
else:
    if sys.argv[3] == '1':
        print('HATA: Mevcut .env bu sırada kaldırıldı; yeniden oluşturulmadı.', file=sys.stderr)
        raise SystemExit(1)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0)
    try:
        fd = os.open(path, flags, 0o600)
    except OSError:
        print('HATA: .env oluşturulamadı; mevcut dosyanın üzerine yazılmadı.', file=sys.stderr)
        raise SystemExit(1)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            stream.write(f'PUBLIC_IP={sys.argv[2]}\n')
            stream.flush()
            os.fsync(stream.fileno())
    except OSError:
        path.unlink(missing_ok=True)
        print('HATA: .env yazılamadı.', file=sys.stderr)
        raise SystemExit(1)
    print('OK: Yalnız PUBLIC_IP içeren .env oluşturuldu (600).')
PY

printf 'OK: Docker Engine %s, Compose %s, PUBLIC_IP=%s\n' "$DOCKER_VERSION" "$COMPOSE_VERSION" "$PUBLIC_IP"
printf '%s\n' 'Hazırlık tamam. Konteyner başlatılmadı; hesap, anahtar veya işlem oluşturulmadı.'
