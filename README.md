# 🐿️ Sincap Post

Kendi ChatGPT/Codex ajanınızla hazırlayabileceğiniz kişisel haber bülteni için
küçük bir başlangıç paketi. Konuyu, kaynakları, dili, uzunluğu, alıcıları, saati
ve imzayı siz seçersiniz. Kendi mevcut mail bağlantınızı kullanırsınız.

Bu repo bir SaaS, mail servisi veya hazır çalışan otomasyon değildir. Python
çekirdeği çevrimdışı profil kontrolü, taze içerik seçimi, tekilleştirme,
HTML/plain metin, CID görsel paketleme ve gönderim durum geçişlerini sağlar.
Araştırmayı ajan yapar; mail ve zamanlama için ortamınızın gerçekten sunduğu
araçlar ayrıca doğrulanır. Kodda mail gönderen veya zamanlama oluşturan istemci
yoktur. Eksik bağlantı veya scheduler varsa kurulum o aşamada tamamlanmamıştır.

## İlk önizleme

Repoyu kendi çalışma dizininize alın. Metin hazırlamak için Python 3.9+ ve
standart kütüphane yeterli; paket kurulumu veya model API anahtarı gerekmez:

```sh
bash scripts/setup.sh
python3 -m sincap init
python3 -m sincap prepare --demo --input examples/issue.json --at 2030-01-02T08:30:00Z --out .local/demo
```

`.local/demo/preview.html` dosyasını tarayıcıda açın. Örnek haberler tamamen
sentetiktir, adresler çalışmayan örnek adreslerdir ve fotoğraf içermez. Demo
saati yalnız `--demo` ile kullanılabilir. Bu işlem provider taslağı oluşturmaz,
mail göndermez ve yayın geçmişini ilerletmez. Çıktı dizini yeniden yazılmaz.

Görsellerin gerçek PNG/JPEG byte'larını doğrulamak için ortamda zaten bulunan
Pillow decoder gerekir. Yoksa görsel desteği eksik bildirilir; script kurulum
yapmaz. Üç CID testi basit PNG'leri geçici dizinde üretir ve gerçek haber
görselleri kullanmaz. Görsel testleri atlandıysa görsel desteği doğrulanmış olmaz.

## Kendi bülteniniz

1. [Kurulum rehberi](docs/setup.md) ile başlayın; önce yetenek ve bağlantıları
   zararsız okumalarla kontrol edin.
2. `.local/profile.json` içindeki örnek kaynak/adresleri kendi tercihlerinizle
   değiştirin. `delivery.enabled` ve `schedule.enabled` başlangıçta `false` kalır.
3. Ajanınız gerçek kaynakları okuyup o güne ait içerik ve görsel kararlarını
   özel çalışma alanına yazar. [Editoryal kurallar](docs/editorial.md) ve
   [adaptör sözleşmesi](docs/adapters.md) bu adımı tarif eder.
4. HTML önizlemesini kontrol edin. Yalnız açık yetkiniz kapsamında, kendi
   doğrulanmış adresinize test edin. Sent ile alıcı görünümünü ayrı doğrulayın.
5. Gerçek bir scheduled test doğru ortam, aynı kalıcı kayıt ve mail bağlantısıyla
   çalışmadan düzenli gönderimi hazır saymayın.

Yerel hazırlık komutu, mevcut kanonik kayıtla çalışır:

```sh
python3 -m sincap prepare --profile .local/profile.json --input .local/today.json --state .local/state.json --out .local/preview-today
python3 -m sincap doctor --stage self-test
```

`today.json` örnekteki alanlarla, gerçek gün ve yeni araştırma bilgisiyle ajan
tarafından oluşturulur; `synthetic` alanı gerçek içerikte `false` olur. `doctor`
yalnız yerel koşulları ve ajan tarafından kaydedilen kanıtı denetler. Bağlantı
çağrısı yapmaz; eksik/eski kanıtta çıkış kodu `2` verir. Kanıt dosyasını elle
“verified” yapmak gerçek testin yerini tutmaz.

## Kapsam ve maliyet

[Destek matrisi](docs/support-matrix.md), gerçekten test edilen Python
çekirdeğini resmî belgelerdeki ürün olanaklarından ve henüz doğrulanmamış
entegrasyonlardan ayırır. `cloud_threads`, Library, Gmail veya scheduler her
hesapta var kabul edilmez. Farklı Cloud görevlerinin yerel dosyaları ortak bir
yayın kaydı sayılmaz.

Repo MIT lisanslıdır. Ücretsiz kod, sınırsız AI veya ücretsiz hosting hakkı
vermez; model kullanımı plan limitlerine ve uygulanabilir ücretlere tabidir.
[Güncel Codex kullanım bilgisi](https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan).
Yeni hesap, API anahtarı veya ücretli servis bu başlangıçta gerekmez.

## Katkı ve mahremiyet

`MANIFEST.txt` dağıtıma girebilen dosyaların açık listesidir. `.local/` yalnız
özel çalışma içindir; `.gitignore` tek başına güvenlik sınırı sayılmaz. Gerçek
adres, bağlantı kimliği, durum kaydı, mail, MIME, görsel veya log eklemeyin.

```sh
bash scripts/setup.sh
python3 scripts/preflight.py --staged
python3 scripts/preflight.py --manifest
```

İlk komut ağ veya mail kullanmadan kontrolleri çalıştırır. Commit öncesi index
taramasını ve staged diff'i birlikte inceleyin. Tarama, bağımsız manuel gizlilik
incelemesinin yerini tutmaz. Dosya görevleri ve sınırlar [AGENTS.md](AGENTS.md)
içindedir.
