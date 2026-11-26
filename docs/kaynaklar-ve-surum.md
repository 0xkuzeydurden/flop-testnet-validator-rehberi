# Resmî kaynaklar ve incelenen sürüm

**Kontrol tarihi: 26 Kasım 2026.** Bu depo FLOP Labs tarafından yayımlanmıyor. Türkçe anlatım ve yardımcı kontroller bu rehber için hazırlandı; ağ bilgileri aşağıdaki birincil kaynaklardan alındı.

## Kaynaklar

1. [Validator hazırlık kiti ve kabul sırası](https://docs.flop.network/testnet-validator-prep/)
2. [Testnet ağ profili](https://docs.flop.network/networks/testnet)
3. [Testnet v0.1.0-early.1 resmî yayını](https://github.com/flop-labs/network/releases/tag/testnet%2Fv0.1.0-early.1)
4. [CLI 0.10.2 katılım düzeltmesi](https://github.com/flop-labs/network/blob/main/releases/cli/v0.10.2.md)
5. [Testnet açılış SSS](https://docs.flop.network/docs/testnet-and-timeline?network=testnet)
6. [Airdrop ve kilit koşulları](https://flop.finance/airdrop/)
7. [Docker Ubuntu kurulumu](https://docs.docker.com/engine/install/ubuntu/)
8. [Docker portları ve UFW](https://docs.docker.com/engine/network/packet-filtering-firewalls/#docker-and-ufw)

## Gözlemci için sabit girdiler

| Alan | Değer |
| --- | --- |
| Ağ | FLOP Testnet |
| Chain ID | `flop_testnet` |
| Genesis | `0x918abd58fb16306b30ef3886514cfaebffecb4de43e82b6f8ec4795c43cfd800` |
| Public RPC | `https://testnet.flop.network/` / `wss://testnet.flop.network/` |
| Spec adı | `flop_testnet-918abd58fb16306b.raw.json` |
| Spec SHA-256 | `485ecb44635609ab261ea3002c3c9fdc7a5dab38caf28a86f654cadf443893be` |
| Node imajı | `ghcr.io/flop-labs/flop-core/node-testnet:v0.1.486` |
| İmaj digest | `sha256:811c84ccc5c49a5608da8d5aaef16f6b076b70b9b7bc26f7a292445c391711ea` |

Zincirdeki runtime, genesis runtime'ından bağımsız olarak yükseltilebilir. Bir runtime yükseltmesini tek başına ağın genesis'inin değiştiği şeklinde yorumlamayın. Buna karşılık ağ reseti nedeniyle genesis değişirse bu sabitleri ve resmî yayını yeniden incelemek gerekir.

## Koltuk onayından sonraki paket

Bu bölüm yalnız FLOP başvurunuzu onayladıktan sonraki katılım içindir. Paketin içindeki güncel `JOIN.md`, hesaba ve sponsorluk durumuna göre uygulanır.

| Alan | Değer |
| --- | --- |
| Dosya | `validator-public-testnet-0.5.0-testnet.2.tar.gz` |
| SHA-256 | `0ac7c12748c50ef80cf39a8209a2f3f04ee1a36c20ebe533ea1e0f0fc4ebe103` |
| İç klasör | `validator-public-testnet/` |
| CLI | Hazırlık kitine göre `0.10.2+`; bu rehberin örneği `0.10.2` |

Ubuntu sunucuda, rehber klasörünün içinden:

```bash
mkdir -p official-validator
curl -fL --connect-timeout 15 --max-time 180 --retry 2 \
  -o official-validator/validator-public-testnet-0.5.0-testnet.2.tar.gz \
  https://github.com/flop-labs/network/releases/download/testnet/v0.1.0-early.1/validator-public-testnet-0.5.0-testnet.2.tar.gz
printf '%s  %s\n' \
  '0ac7c12748c50ef80cf39a8209a2f3f04ee1a36c20ebe533ea1e0f0fc4ebe103' \
  'official-validator/validator-public-testnet-0.5.0-testnet.2.tar.gz' | sha256sum --check
```

Yalnız sonuç `OK` ise açın:

```bash
tar -xzf official-validator/validator-public-testnet-0.5.0-testnet.2.tar.gz -C official-validator
less official-validator/validator-public-testnet/JOIN.md
```

`--bundle` için açılan iç klasör kullanılır: `"$PWD/official-validator/validator-public-testnet"`. Node.js 24+ ve diğer katılım önkoşulları mevcut olmalı; [Node.js'in resmî kurulum sayfası](https://nodejs.org/en/download) kullanılabilir. Observer aşaması Node.js gerektirmez.

Yayın sırasında bazı eski sayfalar `0.9.1+` veya “kit yayımlanmadı” gösterebiliyordu. Güncel hazırlık kitinin ve release API'sinin verdiği `0.10.2+` alt sınırı esas alındı. Detached GPG imzaları henüz yayımlanmamıştı; SHA-256 kontrolü ve sabit imaj digest'i kullanıldı. Checksum, tek başına yayıncı imzası değildir.

## Neler doğrulandı?

- Resmî spec dosyasının ve katılım paketinin hash değerleri karşılaştırıldı.
- Yerel yardımcılar sözdizimi ve kontrollü hata senaryoları bakımından denetlendi.
- İki farklı finalized yükseklikte hash karşılaştırması ve restart kimlik kontrolü rehbere eklendi.
- Canlı VPS kurulumu, dışarıdan P2P erişimi, sponsor kabulü ve aktif validator üyeliği bu depo adına gerçekleştirilmedi. Rehber bunlar için kullanıcıdan gerçek kanıt üretmesini ister.

Bir adım hata verirse sürümü, ağ adını ve gizli bilgi içermeyen hata metnini kaydedin. FLOP'un mevcut issue'larında aynı sorun var mı kontrol edin. Özel anahtarları veya kimlik dosyalarını issue'ya eklemeyin.
