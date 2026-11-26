# Sunucu seçimi ve deneme bütçesi

Son kontrol: **26 Kasım 2026**.

Bu rehberde [DigitalOcean](https://m.do.co/c/c8ac65a302df) üzerinden örnek veriyoruz. Aynı Ubuntu/amd64, Docker ve ağ koşullarını sağlayan başka bir sunucuda da gözlemci kurulabilir.

## Kısa gözlemci denemesi

DigitalOcean Basic / Regular tablosundaki **8 vCPU, 16 GiB RAM, 320 GiB SSD** örneği `$0.14286/saat`, `$96/ay` tavanla listeleniyor. Bu, paylaşımlı CPU kullanan bir VPS. Örneğin dört saatlik yalnız sunucu bedeli yaklaşık **$0.57** eder. Vergi, ek disk, snapshot, yedek ve fazla trafik bu hesaba dahil değil. Oluşturma ekranındaki güncel toplamı esas alın.

Bu seçim bizim kısa observer denemesi için önerdiğimiz başlangıç örneği. FLOP'un ilan ettiği asgari validator paketi veya bu repoyla canlı test edilmiş bir kapasite değil. Zincirin arşivi büyüdükçe disk ve senkron yükü de değişebilir.

[DigitalOcean fiyatları](https://www.digitalocean.com/pricing/droplets) · [Droplet oluşturma](https://docs.digitalocean.com/products/droplets/how-to/create/)

## Kalıcı validator sunucusu

FLOP'un yayımladığı donanım referansı **8 fiziksel çekirdek / 3.4 GHz+, 32 GB ECC RAM (64 GB önerilen), 4 TB kurumsal NVMe, 1 Gbps simetrik bağlantı**. vCPU sayısı fiziksel çekirdek sayısı yerine geçmez. Uzak block-storage diski de otomatik olarak yerel kurumsal NVMe ile eşdeğer kabul edilmemeli.

Bu nedenle yukarıdaki küçük VPS ile başvuru provası yapmanız, aynı paketin aktif validator işletmeye yeterli olduğu anlamına gelmez. Kalıcı kapasiteyi ve sağlayıcı/bölge bilgisini FLOP'a gerçek değerlerle bildirin. Sunucu değişirse yeni makinenin hash, restart ve dış erişim kanıtlarını tekrar üretin.

[FLOP donanım ve kabul süreci](https://docs.flop.network/testnet-validator-prep/) · [DigitalOcean CPU türleri](https://docs.digitalocean.com/products/droplets/concepts/choosing-a-plan/)

## Kampanya ve faturayı kapatma

- Kayıt ekranında kampanya kredisi varsa, hesabınızda gerçekten görünen tutar ve son kullanım tarihini kontrol edin. Bu rehber sabit bir ücretsiz kredi miktarı vaat etmiyor.
- Sunucu çalışırken bütçe bildirimi kullanın. Bildirim, sunucuyu otomatik silen bir harcama limiti değildir.
- Docker'ı veya Droplet'i kapatmak ücretlendirmeyi bitirmez. Prova bittiğinde ihtiyaç duyduğunuz özel dosyaları saklayıp gereksiz Droplet'i silin.
- Ayrı volume ve snapshot'ları da inceleyin; sunucu silindiğinde hepsinin otomatik silindiğini varsaymayın.

[Droplet fiyatlandırma](https://docs.digitalocean.com/products/droplets/details/pricing/) · [Droplet silme](https://docs.digitalocean.com/products/droplets/how-to/destroy/)

## Sağlayıcı kullanım koşulları

DigitalOcean kripto madenciliği için yazılı izin şartı koyuyor. Bir validator/gözlemci ile madencilik aynı iş yükü değildir; sağlayıcının kendi Marketplace'inde validator örnekleri de bulunuyor. Yine de bu sayfalar FLOP validatorına özel bir uygunluk onayı sağlamaz. Uzun süreli ücretli validator kurulumu seçerken iş yükünü ve kaynak ihtiyacını doğru tarif edin.

[DigitalOcean kullanım koşulları](https://www.digitalocean.com/legal/acceptable-use-policy) · [Marketplace validator örneği](https://docs.digitalocean.com/products/marketplace/catalog/mainnet-fullnode/)
