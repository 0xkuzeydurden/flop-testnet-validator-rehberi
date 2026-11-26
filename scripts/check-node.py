#!/usr/bin/env python3
"""Observer için salt-okunur ağ kontrolü; yalnız yerel kanıt JSON'u oluşturur."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
LOCAL_RPC = 'http://127.0.0.1:9944/'
REFERENCE_RPC = 'https://testnet.flop.network/'
EXPECTED_GENESIS = '0x918abd58fb16306b30ef3886514cfaebffecb4de43e82b6f8ec4795c43cfd800'
EXPECTED_SPEC_SHA = '485ecb44635609ab261ea3002c3c9fdc7a5dab38caf28a86f654cadf443893be'
EXPECTED_IMAGE = 'ghcr.io/flop-labs/flop-core/node-testnet:v0.1.486@sha256:811c84ccc5c49a5608da8d5aaef16f6b076b70b9b7bc26f7a292445c391711ea'
EXPECTED_REPO_DIGEST = 'ghcr.io/flop-labs/flop-core/node-testnet@sha256:811c84ccc5c49a5608da8d5aaef16f6b076b70b9b7bc26f7a292445c391711ea'
CONTAINER = 'flop-testnet-observer'
TIMEOUT = 15
MAX_RESPONSE = 1024 * 1024
HASH = re.compile(r'0x[0-9a-fA-F]{64}\Z')
IMAGE_ID = re.compile(r'sha256:[0-9a-f]{64}\Z')
PEER_ID = re.compile(r'[1-9A-HJ-NP-Za-km-z]{16,128}\Z')
STARTED_AT = re.compile(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d{1,9}))?Z\Z')


class CheckError(Exception):
    pass


class TurkishParser(argparse.ArgumentParser):
    def error(self, message):
        raise CheckError('Kullanım: python3 scripts/check-node.py --phase before veya --phase after')


def require(condition, message):
    if not condition:
        raise CheckError(message)


def block_hash(value, label):
    require(isinstance(value, str) and HASH.fullmatch(value), f'{label}: boş veya geçersiz blok hash değeri.')
    return value.lower()


def started_at(value):
    match = STARTED_AT.fullmatch(value) if isinstance(value, str) else None
    require(match, 'Konteynerin başlama zamanı okunamadı.')
    try:
        second = datetime.strptime(match.group(1), '%Y-%m-%dT%H:%M:%S').replace(tzinfo=timezone.utc)
    except ValueError:
        raise CheckError('Konteynerin başlama zamanı geçersiz.') from None
    return second, int((match.group(2) or '0').ljust(9, '0'))


def regular_file(path, label):
    try:
        info = path.lstat()
    except OSError:
        raise CheckError(f'{label} bulunamadı veya okunamıyor.') from None
    require(stat.S_ISREG(info.st_mode), f'{label} normal bir dosya olmalı; sembolik bağlantı kabul edilmez.')
    return info


def verified_spec():
    path = ROOT / 'chain.raw.json'
    regular_file(path, 'chain.raw.json')
    digest = hashlib.sha256()
    try:
        with path.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(chunk)
    except OSError:
        raise CheckError('chain.raw.json okunamadı.') from None
    result = digest.hexdigest()
    require(result == EXPECTED_SPEC_SHA, 'Zincir tanımının SHA-256 değeri resmi sabitle eşleşmiyor.')
    return result


def docker_json(args):
    try:
        result = subprocess.run(['docker', *args], capture_output=True, text=True, timeout=TIMEOUT, check=False)
    except FileNotFoundError:
        raise CheckError('Docker komutu bulunamadı.') from None
    except subprocess.TimeoutExpired:
        raise CheckError('Docker kontrolü 15 saniyede yanıt vermedi.') from None
    except OSError:
        raise CheckError('Docker kontrolü çalıştırılamadı.') from None
    require(result.returncode == 0, 'Docker incelemesi başarısız. Observer konteynerini ve kullanıcı yetkinizi kontrol edin.')
    try:
        value = json.loads(result.stdout)
    except (ValueError, TypeError):
        raise CheckError('Docker incelemesi geçerli JSON döndürmedi.') from None
    require(isinstance(value, dict), 'Docker inceleme yanıtı beklenen biçimde değil.')
    return value


def verified_container():
    template = '{"image":{{json .Config.Image}},"running":{{json .State.Running}},"image_id":{{json .Image}},"started_at":{{json .State.StartedAt}}}'
    container = docker_json(['inspect', '--type', 'container', '--format', template, CONTAINER])
    require(container.get('running') is True, 'Observer konteyneri çalışmıyor.')
    require(container.get('image') == EXPECTED_IMAGE, 'Çalışan observer resmi sabit sürüm ve digest ile eşleşmiyor.')
    image_id = container.get('image_id')
    require(isinstance(image_id, str) and IMAGE_ID.fullmatch(image_id), 'Çalışan image kimliği okunamadı.')
    started_at(container.get('started_at'))
    image = docker_json(['image', 'inspect', '--format', '{"image_id":{{json .Id}},"repo_digests":{{json .RepoDigests}}}', EXPECTED_IMAGE])
    require(image.get('image_id') == image_id, 'Konteynerin gerçek image kimliği onaylı image ile farklı.')
    require(isinstance(image.get('repo_digests'), list) and EXPECTED_REPO_DIGEST in image['repo_digests'],
            'Yerel image kaydında onaylı repository digest bulunamadı.')
    return container


def rpc(url, method, params=None):
    payload = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params or []}).encode('utf-8')
    request = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'}, method='POST')
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            require(response.geturl() == url, 'RPC beklenmeyen bir adrese yönlendirdi; kontrol durduruldu.')
            body = response.read(MAX_RESPONSE + 1)
    except CheckError:
        raise
    except (urllib.error.URLError, TimeoutError, OSError):
        label = 'Yerel' if url == LOCAL_RPC else 'Resmi referans'
        raise CheckError(f'{label} RPC erişilemedi veya 15 saniyede yanıt vermedi ({method}).') from None
    require(len(body) <= MAX_RESPONSE, 'RPC yanıtı beklenenden büyük.')
    try:
        value = json.loads(body)
    except (ValueError, UnicodeError):
        raise CheckError(f'RPC geçerli JSON döndürmedi ({method}).') from None
    require(isinstance(value, dict) and value.get('id') == 1 and value.get('jsonrpc') == '2.0',
            f'RPC yanıt biçimi veya istek kimliği yanlış ({method}).')
    require(value.get('error') is None, f'RPC bir hata döndürdü ({method}); kanıt oluşturulmadı.')
    require('result' in value and value['result'] is not None, f'RPC boş sonuç döndürdü ({method}).')
    return value['result']


def finalized_height(url):
    head = block_hash(rpc(url, 'chain_getFinalizedHead'), 'Finalized head')
    header = rpc(url, 'chain_getHeader', [head])
    require(isinstance(header, dict), 'Finalized blok başlığı beklenen biçimde değil.')
    number = header.get('number')
    require(isinstance(number, str) and re.fullmatch(r'0x[0-9a-fA-F]{1,16}', number),
            'Finalized blok yüksekliği geçersiz.')
    return int(number, 16)


def check_health():
    health = rpc(LOCAL_RPC, 'system_health')
    require(isinstance(health, dict), 'Düğüm sağlık yanıtı beklenen biçimde değil.')
    peers = health.get('peers')
    require(type(peers) is int and peers > 0, 'Observer henüz bir eşe bağlı değil (peers=0).')
    require(health.get('isSyncing') is False, 'Observer henüz senkron oluyor; tamamlandıktan sonra tekrar deneyin.')
    return {'peers': peers, 'isSyncing': False}


def check_report_target(phase):
    directory = ROOT / 'reports'
    if os.path.lexists(directory):
        require(stat.S_ISDIR(directory.lstat().st_mode), 'reports normal bir klasör olmalı; sembolik bağlantı kabul edilmez.')
    target = directory / f'{phase}.json'
    require(not os.path.lexists(target), f'reports/{phase}.json zaten var. Üzerine yazılmadı; önce mevcut kanıtınızı arşivleyin.')
    return target


def load_before():
    path = ROOT / 'reports' / 'before.json'
    info = regular_file(path, 'reports/before.json')
    require(info.st_size <= 128 * 1024, 'before.json beklenenden büyük.')
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError, UnicodeError):
        raise CheckError('before.json okunamadı veya geçerli JSON değil.') from None
    require(isinstance(value, dict) and value.get('schema_version') == 1 and value.get('phase') == 'before',
            'before.json bu kontrol aracının before kanıtı olmalı.')
    require(value.get('expected_genesis') == EXPECTED_GENESIS and value.get('local_genesis') == EXPECTED_GENESIS
            and value.get('reference_genesis') == EXPECTED_GENESIS and value.get('spec_sha256') == EXPECTED_SPEC_SHA
            and value.get('container_image') == EXPECTED_IMAGE, 'before.json farklı ağ veya sürüm içeriyor.')
    require(type(value.get('common_finalized_height')) is int and value['common_finalized_height'] >= 0,
            'before.json ortak finalized yüksekliği geçersiz.')
    block_hash(value.get('common_block_hash'), 'before.json')
    peer = value.get('peer_id')
    require(isinstance(peer, str) and PEER_ID.fullmatch(peer), 'before.json peer ID geçersiz.')
    started_at(value.get('container_started_at'))
    return value


def write_report(path, value):
    try:
        path.parent.mkdir(mode=0o700, exist_ok=True)
        require(stat.S_ISDIR(path.parent.lstat().st_mode), 'reports klasörü güvenli bir normal klasör değil.')
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0)
        fd = os.open(path, flags, 0o600)
    except FileExistsError:
        raise CheckError(f'{path.name} zaten var; üzerine yazılmadı.') from None
    except OSError:
        raise CheckError('Kanıt dosyası oluşturulamadı.') from None
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, indent=2, ensure_ascii=False)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
    except OSError:
        path.unlink(missing_ok=True)
        raise CheckError('Kanıt dosyası tamamen yazılamadı.') from None


def inspect_node(phase):
    target = check_report_target(phase)
    before = load_before() if phase == 'after' else None
    spec_sha = verified_spec()
    container = verified_container()
    local_genesis = block_hash(rpc(LOCAL_RPC, 'chain_getBlockHash', [0]), 'Yerel genesis')
    reference_genesis = block_hash(rpc(REFERENCE_RPC, 'chain_getBlockHash', [0]), 'Referans genesis')
    require(local_genesis == EXPECTED_GENESIS, 'Yerel düğüm onaylı FLOP Testnet genesis ile eşleşmiyor.')
    require(reference_genesis == EXPECTED_GENESIS, 'Referans RPC onaylı FLOP Testnet genesis ile eşleşmiyor.')
    health = check_health()
    local_height = finalized_height(LOCAL_RPC)
    reference_height = finalized_height(REFERENCE_RPC)
    common_height = min(local_height, reference_height) - 2
    require(common_height > 0, 'Finalized blok sayısı karşılaştırma için henüz yeterli değil.')
    local_hash = block_hash(rpc(LOCAL_RPC, 'chain_getBlockHash', [common_height]), 'Yerel ortak blok')
    reference_hash = block_hash(rpc(REFERENCE_RPC, 'chain_getBlockHash', [common_height]), 'Referans ortak blok')
    require(local_hash == reference_hash, 'Aynı finalized yükseklikte blok hashleri eşleşmiyor; kanıt yazılmadı.')
    peer_id = rpc(LOCAL_RPC, 'system_localPeerId')
    require(isinstance(peer_id, str) and PEER_ID.fullmatch(peer_id), 'Düğüm geçerli bir peer ID döndürmedi.')
    if before is not None:
        require(started_at(container['started_at']) > started_at(before['container_started_at']),
                'Observer before kanıtından sonra yeniden başlatılmamış. Önce docker compose restart observer çalıştırın.')
        require(peer_id == before['peer_id'], 'Restart öncesi ve sonrası peer ID değişmiş; kalıcı volume kontrol edilmeli.')
        require(common_height > before['common_finalized_height'],
                'Restart sonrası ortak finalized yüksekliği ilerlememiş. Biraz bekleyip tekrar deneyin.')
    report = {
        'schema_version': 1,
        'phase': phase,
        'observed_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
        'network': 'flop_testnet',
        'local_rpc': LOCAL_RPC,
        'reference_rpc': REFERENCE_RPC,
        'expected_genesis': EXPECTED_GENESIS,
        'local_genesis': local_genesis,
        'reference_genesis': reference_genesis,
        'spec_sha256': spec_sha,
        'container_image': container['image'],
        'container_image_id': container['image_id'],
        'container_started_at': container['started_at'],
        'local_finalized_height': local_height,
        'reference_finalized_height': reference_height,
        'common_finalized_height': common_height,
        'common_block_hash': local_hash,
        'reference_common_block_hash': reference_hash,
        'peer_id': peer_id,
        'health': health,
        'checks': {
            'spec_checksum': True, 'running_image': True, 'genesis': True,
            'local_health': True, 'common_finalized_hash': True,
            'container_restarted': True if before is not None else None,
            'same_peer_after_restart': True if before is not None else None,
            'higher_finalized_height_after_restart': True if before is not None else None,
        },
        'limits': 'Bu RPC karşılaştırması observer kontrolüdür; bağımsız kriptografik finality doğrulaması, dış P2P erişimi veya validator aktivasyonu değildir.',
    }
    if before is not None:
        report['before_observed_at_utc'] = before.get('observed_at_utc')
        report['before_common_finalized_height'] = before['common_finalized_height']
    write_report(target, report)
    print(f'OK: Resmi zincir tanımı ve çalışan image doğrulandı.\nOK: Genesis ve finalized blok hashleri eşleşti (yükseklik {common_height}).')
    if before is not None:
        print('OK: Aynı peer ID korundu ve finalized yükseklik ilerledi.')
    print(f'Kanıt kaydedildi: reports/{phase}.json (600).')
    print('Bu kontrol observer içindir; aktif validator veya ödül kanıtı değildir.')
    return report


def main(argv=None):
    parser = TurkishParser(description='FLOP Testnet observer için salt-okunur kontrol ve yerel kanıt.')
    parser.add_argument('--phase', choices=('before', 'after'), required=True, help='restart öncesi before, sonrası after')
    try:
        args = parser.parse_args(argv)
        inspect_node(args.phase)
    except CheckError as exc:
        print(f'HATA: {exc}', file=sys.stderr)
        return 1
    except OSError:
        print('HATA: Yerel dosya veya klasöre erişilemedi; kontrol tamamlanmadı.', file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print('HATA: Kontrol kullanıcı tarafından durduruldu.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
