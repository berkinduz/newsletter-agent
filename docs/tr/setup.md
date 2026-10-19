# Kendi ortamında kurulum

[English](../setup.md) · **Türkçe**

Bu sıra ajanla birlikte izlenir. Repo, kendi mevcut ChatGPT/Codex kullanımın
ve bağlantıların üzerinde çalışır. Kurulum süreci mail, zamanlama veya yeni
erişim izni oluşturmak için genel bir yetki değildir.

Kullanıcı için giriş mesajı ve ajan için Gmail/Library çağrı sırası,
[uygulanabilir onboarding akışında](onboarding.md). Aşağıdaki rehber tercihleri
ve doğrulama aşamalarını açıklar; teknik araç alanlarını ajan doldurur.

## 1. Yetenekleri doğrula

Ajan önce gerçek çalışma ortamını, repo dizinini/sürümünü, dosya ve shell
erişimini, Python'u, kaynak okuma aracını, görsel incelemeyi, mail araçlarını,
kalıcı kayıt yolunu ve scheduler'ı kontrol eder. Araç adı görmek yeterli olmaz.
Plan ve workspace sınırlarını [destek matrisinden](support-matrix.md) değerlendir.

Mevcut mail bağlantısı varsa kullanıcının seçtiği hesapta zararsız profil
okuması yap. Okunan hesap ile istenen göndereni eşleştir; kimlik tahmin etme.
Bağlantı ekranı, yeniden giriş veya ek onay istenirse o bağımlılığı bildir.
Kurulum adına yeni hesap, credential, plugin veya kapsam oluşturma.

Eksikleri somut yaz: “Python dosya erişimi var, mail taslak aracı yok;
HTML hazırlayabiliriz, gönderim kurulmadı.” Scheduler yoksa manuel hazırlık
kullanılabilir; günlük çalışıyor denmez. `cloud_threads` veya özel bir Library
aracı bu paketin bağımlılığı değildir.

## 2. Profili ve tek kalıcı kaydı seç

Dil henüz belirtilmediyse ajan **“Bültenin Türkçe mi, İngilizce mi olmasını
istersiniz?”** diye sorar. Sohbet dilinden içerik dilini çıkarmaz ve bilinen
tercihi tekrar sormaz. Aşağıdaki komut Türkçe seçeneğidir; kullanıcı İngilizce
seçerse `--language en` kullanılır.

```sh
bash scripts/setup.sh
python3 -m sincap init --language tr
```

`init` yalnız yeni dizin oluşturur; mevcut kaydı sıfırlamaz. Başlangıçta
`.local/profile.json`, `.local/capabilities.json`, `.local/state.json` oluşur.
Keşfedilen hesap, ortak kayıt ve scheduler referansları için özel
`.local/installation.json` da oluşturulur; başlangıçta bu alanlar boştur.
Birden fazla bağımsız profil gerekiyorsa başlangıçtan itibaren ayrı dizin ve
kimlik kullan:

```sh
python3 -m sincap init --language tr --directory .local/reading --profile-id reading
```

Profilde konu başlıklarını, kaynakların keşif URL'lerini, önceliklerini ve
hariç tutulan kaynak kimliklerini seç. Kaynak listesi okunabilirlik veya kalite
sertifikası değildir. Dil için aşağıdaki hazır başlangıçları kullanabilir veya görünen `labels`
metinlerini ve içerik dilini birlikte özelleştirebilirsin; Python çeviri yapmaz. Uzunluk için hedef dakika ve zorunlu min/max sözcük
aralığını belirle; dakika yaklaşık 200 sözcük/dakika hesabıdır. Sözcük kontrolü
açılış, özet ve yorum gövdelerini kapsar.

Haber URL'si varsayılan olarak keşif URL'siyle aynı host'a ait olmalı. Feed
sunucusu ve yayın sitesi farklıysa kaynağa açık bir `article_hosts` listesi
ekle; ajan yalnız gerçekten seçilen yayın host'larını bu listeye yazar.

Göndereni, alıcıları ve imzayı kendin belirle. Bare adres kullan; Cc/Bcc yoktur.
Bu sürüm aynı içeriği tek To zarfıyla paylaşır: birden fazla alıcı birbirinin
adresini görür. Kullanıcı bu kapsamı seçmeden listeyi genişletme. Tek kişilik
bültende yalnız kendi doğrulanmış adresini kullan. Saat IANA timezone ve
`HH:MM` alanlarından alınır. Bayrakları şimdilik kapalı tut. JSON'da bayrağı
açmak mail veya scheduler kurmaz.

`state.json` aynı profil için tek kanonik kayıt olmalı. İlk kurulumdan sonra
profil kimliğini değiştirerek yeni yayın geçmişi yaratma. Yerel `LocalStore`
aynı dosya sistemi üzerinde CAS sağlar. Ayrı worktree veya Cloud görevinde
`.local` kendiliğinden paylaşılmaz. Ortamlar arası atomik kayıt erişimi
doğrulanmamışsa düzenli gönderim kurulamaz; [adaptör kuralları](adapters.md).

## 3. Kaynak testi ve HTML önizleme

Seçilen her etkin kaynaktan küçük bir örnek al: gerçek yayın tarihi ve
yeterli görünür gövdeyi oku. RSS/arama kısa metni veya HTTP başarısı yetmez.
Erişilemeyen kaynağı açık bırakıp çalışıyor deme; gerekirse devre dışı bırak.
Bu bir üretim bülteni gönderimi değildir.

Önce `README` içindeki sentetik demoyu aç. Sonra ajan her gün güncel kaynakları
okuyarak `examples/tr/issue.json` biçiminde `.local/today.json` hazırlar. Gerçek
günün `issue_date`, `researched_at`, içerik dili ve `synthetic: false` alanları
gerekir. URL/DOI ve olay kimlikleri tekilleştirme içindir; anlamlı yeni gelişme
yeni revision, gerçek güncelleme tarihi ve açık development_note gerektirir.

Görseller haberle eşleşen gerçek görsellerdir. [Editoryal rehber](editorial.md)
ve [görsel sözleşmesi](adapters.md#görsel-devri) uygulanır. Haber görseli
dosyaları ve inceleme kayıtları `.local` içinde kalır.

```sh
python3 -m sincap prepare --input .local/today.json --state .local/state.json --out .local/preview-today
```

Komut HTML/plain/MIME ve rapor üretir; gerçek provider taslağı oluşturmaz.
`preview.html` dosyasını geniş ve dar ekranda aç: taşma, başlık/görsel/yorum
sırası, alt metin, kredi ve kaynak bağlantılarını kontrol et. Mail HTML'sindeki
CID'ler ayrı `newsletter.html` ve `newsletter.eml` dosyasında korunur; tarayıcı
önizlemesinde yerel assets yoluna çevrilir. Bu dosyaların hiçbiri Git'e girmez.

## 4. Açık yetkiyle kendine test

Kullanıcının açık test talimatı geldiğinde alıcıyı yalnız mevcut bağlantıda
zararsız okumayla doğrulanmış kendi adresine indir. Başka alıcıya test gönderme.
Test için ayrı state/dizin ve `test/` issue anahtarı kullan; üretim kaydını veya
sayı numarasını tüketme. Gönderilecek somut HTML/plain ve alıcı görünür olsun.

Mevcut araç destekliyorsa bir taslak oluştur, sonra taslağı geri okuyarak
From/To/Subject, HTML/plain ve bütün CID byte'larını doğrula. Ardından yalnız
hesap bağlantısı ve gerçek draft kimliğiyle gönder. Yerel `.eml` dosyası
araç şeması tarafından desteklenmiyorsa alanları doğrulanmış MIME ağacına
eşleştir; ham MIME desteği varmış gibi davranma. Doğal onayları koru.

Provider sonucu ve Sent eşleşmesini kaydet; alıcının Inbox/görüntülemesini
ayrıca doğrula. Belirsiz sonuçta tekrar gönderme. Üç inline görselle test
isteniyorsa üçü de doğru byte/CID ile görünmeli. Offline üç CID testi, bu gerçek
istemci kontrolünün yerine geçmez.

## 5. Gerçek scheduled test ve düzenli çalışma

Mail testi geçmeden düzenli gönderim açma. Scheduler mevcut ve kullanıcı
yetkiliyse önce tek seferlik gerçek bir scheduled test planla. Normal bir
“şimdi çalıştır” çağrısı bu kanıtın yerine geçmez. Test yalnız kullanıcının
kendisine gider; ayrı test state'i kullanır.

Gerçek tetiklenmede runtime, repo sürümü, doğru profil/hash, aynı tek kalıcı
kayıt ve doğru mail hesabını yeniden doğrula. Dönen hedef etiketinin doğru
görünmesine güvenme; gerçek işin nerede çalıştığını incele. Dosya/bağlantı/saat
kapısı kontrolü başarısızsa mail göndermeden dur.

Scheduler saati IANA timezone ile kaydeder. Çalışma anında aynı timezone ile
gerçek saate bak; erken tetiklenmede gönderme. Desteklenen yeniden planlama
yolunu kullan veya beklenen saatte yeni tetikleme iste; sürekli VM varsayma.
Yerel task için bilgisayar ve app açık olmalı. Dakikasında teslim garanti edilmez.

Kabul edilen schedule kaydı, gerçek çalışmanın doğru ortamda başlaması,
provider kabulü ve Inbox görünümü ayrı kanıtlardır. Scheduler ve kalıcı kayıt
bu testi geçmediyse düzenli yayın hazır değildir. Eski/başka projeye ait
otomasyonları değiştirme veya tekrar etkinleştirme.

## Kanıt kaydı

Ajan gerçek işlemlerden sonra `.local/capabilities.json` içindeki context ve
check alanlarını günceller. Kanıtlar bu runtime/repo sürümü ve `doctor` çıktısının
güncel `profile_sha256` değeriyle eşleşir. Her `verified` check için gerçek
işlem açıklaması ve ISO timezone'lu `checked_at` gerekir. Bu başlangıç,
kontrollerin son 24 saatte yapılmasını ister; profil/hesap/ortam değişince
etkilenen kontroller yeniden yapılır. Kimlikler ve ayrıntılı sonuçlar özel kalır.

```sh
python3 -m sincap doctor --stage self-test
python3 -m sincap doctor --stage scheduled
```

İlk komuttaki `mail_draft_roundtrip`, açık test yetkisiyle oluşturulmuş taslağın
kontrolüdür; eksikse henüz test gönderimine hazır değilsin. İkinci komuttaki
`scheduler_execution`, gerçekten tetiklenen testin kanıtıdır. Çıkış kodu `0`,
yalnız kaydedilen kanıtların eksiksiz ve güncel olduğunu gösterir; harici
servislerin bağımsız otomatik sertifikası değildir. Engeller çözülmeden
bayrakları açma veya kurulumu tamamlandı diye bildirme.

## Dil seçimi

Yeni profil için `python3 -m sincap init --language tr` Türkçe,
`python3 -m sincap init --language en` İngilizce başlangıç oluşturur.
Varsayılan İngilizcedir. Türkçe demo için `examples/tr/issue.json`, İngilizce
demo için `examples/issue.json` kullan. Selamlama, imza, etiketler ve örnek
konu/kaynak adları hazır profilde seçilen dildedir.

Mevcut profili değiştirmek için `init` çalıştırma. Kanonik profilde `language`,
`greeting`, `signature`, `labels`, konu başlıkları ve görünen kaynak adlarını
birlikte düzenle; kendi kimliğini, adreslerini, saat dilimini ve geçmişini koru.
Mevcut bir otomasyon varsa değişikliği aynı kanonik kayda CAS/readback ile yaz.
Sonraki sayı aynı `language` değerini kullanmalı; açılış, başlık, tür, özet,
yorum, kapanış sorusu ve görsel alt metni/kredisi ajan tarafından o dilde yazılır.
Gerekli özel adları ve atıfları koru. Python mevcut yazıları çevirmez.
Profil hash'i değiştiği için etkilenen kanıtları yeniden doğrula.

`scheduled_test_prompt(..., language="tr")` Türkçe operasyon yönergesi üretir;
varsayılan İngilizcedir. Bu, bültenin içerik dilinden ayrıdır. Diğer içerik
dilleri özel profil ve eşleşen sayı girdisiyle kullanılabilir; hazır
başlangıçlar yalnız İngilizce ve Türkçedir. Komut adları, JSON anahtarları ve
tanı mesajları İngilizcedir; JSON anahtarlarını çevirmeyin.
