# ⚡️ FLOP Testnet Validator Rehberi

GPU olmadan bir sunucu hazırlıyoruz, **Testnet'e bağlanan gözlemci düğümü** çalıştırıyoruz ve FLOP'a sunabileceğimiz kontrol çıktısını alıyoruz. Koltuk onayı geldikten sonraki validator katılımı da aşağıda.

**Son kontrol: 26 Kasım 2026.** FLOP'un resmî belgelerinden yararlanılarak hazırlanmış bağımsız Türkçe topluluk rehberidir.

> Başvuru, çalışan gözlemci ve aktif validator farklı aşamalar. Başlangıç dönemi puansız; önceki işlemlere sonradan puan verilmeyecek. Bu rehberdeki gözlemci kurulumunda cüzdan, seed veya stake kullanılmaz.

📌 **Doğrulama sınırı:** Komutlar, ağ bilgileri ve kontrol aracının hata senaryoları incelendi. Bu depo için kiralık VPS üzerinde uçtan uca kurulum ve validator kabulü yapılmadı.

## 1. Önce aday kaydımızı açalım

[FLOP başvuru formunu açın](https://github.com/flop-labs/network/issues/new?template=operator-application.yml).

- Network: **testnet**
- Requested role: **validator candidate**
- Herkese açık ekip adı, planlanan sunucu sayısı, sağlayıcı, bölge ve hazırlık durumunu yazın.
- Sunucu henüz hazır değilse bunu belirtin. Başvuru için önce sunucu kiralamak şart değil.
- Aynı ekip/ağ için mevcut başvurunuzu güncelleyin. Özel iletişim bilgileri için FLOP'tan özel koordinasyon kanalı isteyin.

Başvurunun numarasını kaydedin. Örneğin `#1234`. **Kayıt ücretsiz; onay ve ödül garantisi vermiyor.**

## 2. Sunucuyu seçelim

[DigitalOcean'da hesap açın veya giriş yapın](https://m.do.co/c/c8ac65a302df). **Create → Droplets** bölümünden bir Linux sunucu oluşturabilirsiniz.

Bu rehberin kısa gözlemci provası için örnek seçimimiz:

| Ayar | Seçim |
| --- | --- |
| İşletim sistemi | Ubuntu 24.04 LTS, **x86_64 / amd64** |
| Örnek paket | Basic / Regular, 8 vCPU, 16 GiB RAM, 320 GiB SSD |
| Bölge | Başvuruda bildireceğiniz bölge; örneğin Frankfurt |
| Bağlantı | Public IPv4 ve SSH anahtarı |
| GPU | Gerekmez |

**Bu paket bir prova önerisidir; resmî validator donanımının karşılığı veya test edilmiş yeterlilik garantisi değildir.** 26 Kasım'da bu örnek planın listesi `$0.14286/saat`, aylık tavanı `$96` idi. Vergi, yedek, snapshot, ek disk ve trafik dahil toplamı sipariş ekranından kontrol edin. Kampanya kredisi varsa hesabınızda görünen tutar ve süreyi esas alın.

Uzun süreli validator için FLOP'un referansı daha yüksek:

| Bileşen | Resmî referans |
| --- | --- |
| CPU | 8 fiziksel çekirdek, 3.4 GHz veya üstü |
| Bellek | 32 GB ECC; 64 GB öneriliyor |
| Disk | 4 TB kurumsal NVMe |
| Ağ | 1 Gbps simetrik bağlantı |

**vCPU, fiziksel çekirdekle aynı şey değil.** Yukarıdaki DigitalOcean örneğinin RAM'i ve diski de bu referansın altında. Kalıcı validator sunucusunu FLOP'la kapasiteyi netleştirerek seçin. Prova sunucusunu değiştirirseniz yeni sunucunun kontrollerini de tekrar yapın.

[Sağlayıcı ve maliyet notları](docs/saglayici-secimi.md) · [Güncel FLOP donanım referansı](https://docs.flop.network/testnet-validator-prep/)

## 3. SSH anahtarını ekleyelim

Bu bölüm **kendi bilgisayarınızda**. Mac'te Terminal, Windows'ta PowerShell/OpenSSH kullanabilirsiniz. Mac/Linux örneği:

```bash
mkdir -p "$HOME/.ssh"
chmod 700 "$HOME/.ssh"
if [ -e "$HOME/.ssh/flop_validator" ] || [ -e "$HOME/.ssh/flop_validator.pub" ]; then
  echo 'Mevcut anahtar korundu.'
else
  ssh-keygen -t ed25519 -f "$HOME/.ssh/flop_validator" -C 'flop-validator'
fi
cat "$HOME/.ssh/flop_validator.pub"
```

DigitalOcean sunucu oluşturma ekranında **Authentication → SSH keys** bölümüne yalnızca `.pub` çıktısını ekleyin. Sunucu adı için kişisel bilgi içermeyen `flop-testnet` kullanabilirsiniz.

## 4. Firewall ve bağlantı

Sağlayıcının firewall'unda şu giriş kurallarını oluşturup **bu sunucuya bağlayın**:

| Port | Kaynak | Kullanım |
| --- | --- | --- |
| TCP 22 | Kendi internet IP'niz | SSH |
| TCP 30333 | Tüm IPv4 adresleri | FLOP eş bağlantısı |

Çıkış trafiği açık kalsın. **9944, 9615 ve 7000 için herkese açık giriş kuralı eklemeyin.** Bu gözlemci aşamasında DA portu 7001 de gerekmiyor. Docker'ın yayımladığı portlar UFW'yi aşabildiğinden yalnız UFW'ye güvenmiyoruz; RPC'yi ayrıca localhost'a bağlıyoruz.

Sunucunun panelde yazan public IPv4 adresini `SUNUCU_IP` yerine koyun:

```bash
ssh -i "$HOME/.ssh/flop_validator" root@SUNUCU_IP
```

**Aşağıdaki kurulum komutları bu SSH oturumunda, Ubuntu sunucuda çalışır.**

## 5. Docker'ı hazırlayalım

Bu adımlar yeni Ubuntu 24.04 sunucu içindir. Üzerinde başka işler çalışan bir sunucuda mevcut Docker paketlerini kaldırmayın.

```bash
apt-get update
apt-get install -y ca-certificates curl git python3 jq gnupg
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
. /etc/os-release
cat > /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: ${UBUNTU_CODENAME:-$VERSION_CODENAME}
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker
docker version
docker compose version
```

Docker Engine **28 veya üstü**, Compose eklentisi ve çalışan daemon görünmeli. Farklı işletim sistemi için [Docker'ın resmî kurulumunu](https://docs.docker.com/engine/install/ubuntu/) kullanın.

## 6. Rehber dosyalarını alalım

```bash
cd "$HOME"
git clone https://github.com/0xkuzeydurden/flop-testnet-validator-rehberi.git
cd flop-testnet-validator-rehberi
bash scripts/prepare.sh SUNUCU_IP
```

`SUNUCU_IP` yine sağlayıcı panelindeki public IPv4 adresiniz. Hazırlık aracı Linux/amd64 ve Docker'ı kontrol eder, resmî Testnet zincir dosyasını indirir ve SHA-256'sını sabit değerle karşılaştırır. `.env` içine public IP'yi yazar. Mevcut dosyaları körlemesine değiştirmez; hata varsa burada durun.

Bu depo **26 Kasım sürümüne sabitlenmiştir**. Ağ sıfırlanır veya FLOP imajı kullanım dışı bırakırsa güncel resmî sürümle yeniden karşılaştırın. Hash kontrolünü kaldırarak devam etmeyin.

## 7. Gözlemciyi başlatalım

```bash
docker compose config --quiet
docker compose pull
docker compose up -d
docker compose ps
docker compose logs --tail=40 observer
```

Konteyner adı `flop-testnet-observer`. Veri, `flop-testnet-observer-data` adlı kalıcı Docker volume'unda tutulur. Loglarda senkron ilerlemesini görebilirsiniz. Süre, ağ ve sunucuya bağlıdır.

Bu düğüm zinciri takip eder. Aktif validator üyeliği veya ödül kazanımı anlamına gelmez.

## 8. İlk kontrol çıktısını alalım

```bash
python3 scripts/check-node.py --phase before
```

Araç şu kontrolleri yapar:

- Yerel düğüm ve resmî RPC doğru Testnet genesis'inde mi?
- Yerel düğüm senkronu tamamlamış ve eşlere bağlanmış mı?
- İki kaynakta **aynı kesinleşmiş yükseklikteki** blok hash'i aynı mı?
- Çalışan konteyner ve zincir dosyası beklenen sabit sürümle uyumlu mu?

Başarılı sonuç `reports/before.json` dosyasına yazılır. Senkron devam ediyorsa logları kontrol edip biraz sonra aynı komutu tekrar çalıştırın. Hata alınca başarılı çıktı üretilmez.

## 9. Yeniden başlatma provasını yapalım

```bash
docker compose restart observer
```

Düğüm yeniden bağlantı kurup bloklar ilerledikten sonra:

```bash
python3 scripts/check-node.py --phase after
```

İkinci kontrolde **peer ID aynı kalmalı**, ortak kesinleşmiş yükseklik artmalı ve hash'ler yeniden eşleşmeli. Araç ayrıca konteynerin ilk rapordan sonra yeniden başladığını kontrol eder. Sonuç `reports/after.json` olur. Kontrol aracı eski raporların üzerine yazmaz. Yeni bir prova seti başlatacaksanız `reports` klasörünü önce farklı bir adla arşivleyin.

## 10. Portu dışarıdan kontrol edelim

Bu komutu **kendi bilgisayarınızdan**, sunucunun dışındaki bir ağdan çalıştırın:

```bash
nc -vz -w 5 SUNUCU_IP 30333
```

Mac/Linux'ta bağlantı başarılı olmalı. Windows PowerShell karşılığı:

```powershell
Test-NetConnection -ComputerName SUNUCU_IP -Port 30333
```

Ayrıca 9944'e dışarıdan erişim **başarısız** olmalı:

```bash
nc -vz -w 5 SUNUCU_IP 9944
```

30333 kapalıysa sağlayıcı firewall'u, sunucuya atanmış kurallar ve `.env` public IP'sini kontrol edin. RPC dışarıdan açıksa devam etmeden port eşlemesini düzeltin.

## 11. Başvurumuza kanıt ekleyelim

Başvuru issue'nuzu güncelleyin. `reports/before.json` ve `reports/after.json`, yayımlanabilir kontrol alanlarını içerir; paylaşmadan önce kendiniz de okuyun. Şu kısa İngilizce şablonu doldurabilirsiniz:

```text
Testnet host check completed.
Provider / region: ...
Node image digest: ...
Chain spec SHA-256: ...
Genesis: ...
Before restart: UTC ..., finalized height ..., block hash ..., peer ID ...
After restart: UTC ..., finalized height ..., block hash ..., peer ID ...
Same peer ID after restart: yes/no
Public TCP 30333 reachable from a separate network: yes/no
RPC 9944 not reachable from the public internet: yes/no
Detailed private coordination available on request.
```

Kendi ölçmediğiniz satıra `yes` yazmayın. Sunucunun özel anahtarı, cüzdan yedeği, şifre veya erişim tokenı paylaşılmaz.

## 12. Koltuk onayı gelince

FLOP'un başvurunuz için verdiği onayı bekleyin. Güncel [resmî validator hazırlık kiti](https://docs.flop.network/testnet-validator-prep/) katılım için **CLI 0.10.2 veya üstünü**, Node.js 24+ ve yayımlanan joining bundle'ı kullanıyor.

Bu noktada gerçek validator kapasitesini ve sağlayıcının bu iş yüküne uygunluğunu da netleştirmiş olun. İlk provadaki küçük paketi otomatik olarak yeterli kabul etmeyin.

26 Kasım'daki paket ve doğrulama bilgileri [sürüm notlarımızda](docs/kaynaklar-ve-surum.md). Paketteki **`JOIN.md`** dosyasını okuyup FLOP'un hesap, sponsorluk ve DA adımlarını uygulayın. Observer ile validator aynı portları kullanacağından geçişten önce gözlemciyi durdurun:

```bash
docker compose down
```

Bu komut volume'u silmez. Resmî join'in genel biçimi:

```bash
npx --yes --package @flop-labs/cli@0.10.2 flop validator join \
  --network testnet \
  --bundle /PAKETIN/ACILDIGI/KLASOR \
  --public-ip SUNUCU_IP \
  --application flop-labs/network#BASVURU_NUMARASI \
  --background
```

Sponsorlukla katılacaksanız **kendiniz `validators.register` çağırmayın**; resmî belge bunun sponsorlu yolu kapatabildiğini söylüyor. Onaylı hesabın sponsor talebi, paketteki `sponsor-request.mjs` ile önce dry-run yapılarak gönderilir. Komutları güncel `JOIN.md` ile doğrulayın.

Kayıt veya sıraya giriş çıktısı aktif validator olduğunuzu kanıtlamaz. FLOP'un istediği kesinleşmiş oturumda aktif üyelik ve BABE/Aleph anahtar eşleşmesi kontrol edilmeli. Bu aşama hesabınıza verilen onayla tamamlanır.

## 13. Durdurma, veriyi koruma ve ücret

```bash
docker compose stop
```

Yalnız uygulamayı durdurur. Tekrar başlatma:

```bash
docker compose start
```

Observer kimliği ve zincir verisi volume'da kalır. Aynı kimliği korumak istiyorsanız `docker compose down -v` veya `docker volume prune` çalıştırmayın. Resmî validator katılımı kendi ayrı volume'unu kullanır; observer verisi oraya taşınmaz.

**Sunucuyu kapatmak DigitalOcean faturasını durdurmaz.** İşiniz bittiyse gereken özel dosyaları güvenli şekilde saklayıp Droplet'i panelden silin; ayrıca volume, snapshot ve diğer ücretli kaynakları kontrol edin. Gerçek validator olarak kabul edildiyseniz sunucuyu kapatmak aktif görevinizi keser.

## Sık takılan yerler

| Durum | İlk bakılacak yer |
| --- | --- |
| `prepare.sh` yanlış mimari diyor | ARM yerine x86_64/amd64 sunucu seçilmiş olmalı |
| Checksum veya genesis uyuşmuyor | Güncel resmî sürümü kontrol edin; denetimi atlamayın |
| Senkron bitmedi / peer yok | Loglar, çıkış ağı, bootnode erişimi ve disk |
| İlk kontrol geçti, ikinci yükseklik aynı | Finality ilerlemesini bekleyip ikinci kontrolü tekrar deneyin |
| Restart sonrası peer ID değişti | Aynı Docker volume'u kullandığınızı kontrol edin |
| Referans RPC hata veriyor | Yerel düğümün bozuk olduğu sonucu çıkmaz; daha sonra kontrol edin |
| 30333 dışarıdan kapalı | Sağlayıcı firewall'u, public IPv4 ve port eşlemesi |

## 1,2 milyon FLOP konusu

Resmî airdrop taslağında, testnet sıralamasıyla mainnet'in en fazla 1.000 validator koltuğuna kabul edilenlere koltuk başına **1.200.000 FLOP teminat** ayrılıyor. Başvurunun veya bu provanın karşılığı olarak hemen verilmiyor. Genesis'te likit kısmı yok; yaklaşık on yılda açılıyor ve aktif koltuk için gereken teminat bağlı kalıyor.

Başlangıç ağı hâlâ **unscored**. Sayılacak dönemin başlangıcı ayrıca duyurulacak. [Ödül koşulları](https://flop.finance/airdrop/) · [Güncel testnet durumu](https://flop.finance/testnet/)

---

[Resmî kaynaklar ve sabit sürümler](docs/kaynaklar-ve-surum.md) · [DigitalOcean](https://m.do.co/c/c8ac65a302df) · Hazırlayan [@kuzeydurdn](https://x.com/kuzeydurdn)
