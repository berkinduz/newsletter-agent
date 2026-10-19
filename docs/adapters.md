# Taşınabilir çekirdek ve ortam adaptörü

Python modülleri hiçbir uzak servise bağlanmaz. `core` profil/tarih/tercih ve
URL/DOI/olay tekilleştirmesi; `render` HTML/plain ve görsel inceleme kaydı;
`mime` related → alternative + inline PNG/JPEG ağacı; `delivery` alıcı ve
gönderim geçişleri; `store` aynı dosya sisteminde CAS sağlar. CLI yalnız
`init`, `doctor`, `prepare` sunar. Bunlar bağımsız test edilebilir çekirdektir.

Mail/scheduler adaptörü bu repo içinde kurulmuş bir servis değildir.
`sincap.onboarding`, mevcut Gmail şeması için somut draft girdisi/raw doğrulaması
ve Library için guarded replace/readback yardımcıları sağlar. Ajanın çağrı
sırası ve iki Cloud görevi CAS testi [onboarding akışında](onboarding.md).
Aşağıdaki sözleşme, kullanıcının ajanının mevcut araç şemasına göre uygulayacağı sınırdır.
Araç bulunamıyorsa veya alanları desteklemiyorsa başarı taklidi yapılmaz.

## Mail ve kalıcı kayıt

Özel durumun `data` alanı `profile_id`, `history`, `deliveries` içerir. Her günlük
issue key için delivery kaydı yalnız bir kez oluşturulur; mevcut kaydı
`new_delivery` ile değiştirmek veya resetlemek yasaktır. `prepare` geçmişi
ilerletmez; provider tarafında gerçek taslak oluşturmayan yerel bir pakettir.

1. Kullanıcının yetkisini, doğru bağlantı profilini, gerçek saati, son kanonik
   kaydı ve varsa Sent durumunu oku. `delivery.assert_send_allowed` ile profil
   bayrakları, yerel gün/saat ve self-test kapsamını ayrıca denetle. Bu fonksiyona
   `user_authorized=True` yazmak gerçek yetki oluşturmaz.
2. Hazırlanan HTML/plain ve görsel byte'larından `mime.package` ile
   `editorial_sha256` ve recipient snapshot'ı al. Bu hash alıcılardan bağımsızdır.
   Gün/sayı, içerik ve recipient_set_hash kalıcı kayda bağlı olmalı. Yalnız
   uygun kalan alıcılar için `delivery.to_header` kullan; Cc/Bcc ekleme.
3. Mevcut mail aracının şemasını incele. Tam MIME veya eşdeğer structured MIME
   ağacı destekleniyorsa bir create_draft çağrısı yap. Büyük byte/base64
   girdilerini programatik taşı; model çıktısına veya loga basma. Taslağı geri
   okuyup From/To/Subject, plain/HTML ve CID/hash'leri kontrol et. `mime.verify`
   çevrimdışı ağaç ve byte kontrolüdür; provider taslağının ayrıca okunması gerekir.
4. `delivery.reserve` sonucunu mevcut kayda CAS ile yaz; aynı sürümü/readback'i
   doğrula. `LocalStore.cas(expected_version, data)` kilit, sürüm ve byte
   readback'i uygular. Harici depoda eşdeğer atomik sözleşme gerekir. Aynı kayda
   ulaşamayan ayrı Cloud çalışma alanları için yerel kilit yeterli değildir.
   Sayfalı okumada tüm sayfalar aynı dosya/sürümde tamamlanmalı; kesik JSON veya
   yeni sürüm etiketiyle dönen eski içerik güncel kayıt sayılmaz.
5. Son anda zarfı ve saat/hesap/kayıt bağlamını yeniden doğrula. Yalnız hesap
   bağlantısı ve o gerçek draft kimliğiyle bir send_draft çağrısı yap. Büyük
   full-MIME send, kör update_draft veya yeni taslakla otomatik retry yapma.
   Onay döngüsü olursa onayı azaltarak aşma; işlemi belirsiz bırakıp uzlaştır.
6. Sonucu alıcı başına `delivery.record_result` ile işle. `provider_accepted`
   için gerçek mesaj kimliği, doğru Sent eşleşmesi ve evidence gerekir.
   `definitively_rejected` yalnız açık non-acceptance kanıtıyla verilir.
   Timeout/iptal/sonuç yoksa `uncertain` kullan. Başarılı alıcı korunur;
   belirsiz alıcı/girişim varken yeni send açılmaz.
7. `delivery.advance_once`, ilk doğrulanmış kabulde sayıyı yalnız bir kez
   ilerletir. `core.record_publication` ile history/cutoff ve delivery sonucunu
   aynı CAS içinde kaydet. Kısmi düzeltme aynı sayıya bağlı kalır ve başarılı
   alıcıyı içermez. State yazımı başarısızsa maili tekrarlama; Sent ile kayıt
   onarılır. Sonradan bounce gelmesi accepted→pending reset izni değildir.

`provider_accepted` Inbox teslimi iddiası değildir. Karşı kutu görünümü/teslimi
ayrı kontrol edilir. Boş Sent araması da tek başına kesin non-acceptance değildir.

Yerel CAS, aynı diskte tek kanonik dosyaya erişen süreçler için test edildi.
Network filesystem semantiği ve farklı işletim sistemleri burada doğrulanmadı.
Kalan lock dosyası veya state çakışması otomatik kilit kırma/yeniden gönderim
izni vermez. State yedeği özel kalır ve geri yükleme sonrası önce Sent ile
uzlaşılır; Git'e veya environment snapshot'ına canlı ledger konulmaz.

## Görsel devri

Görselin haberle ilişkisi kodla ispatlanamaz. Ajan pikselleri, olay/tarih,
kredi, kaynak ve kullanım kapsamını gerçekten inceler; kod kaydın eksiksizliğini
ve byte/hash bağını sınar. Her article `image_decision` taşır. Seçilen image:

| Alan | Anlam |
| --- | --- |
| `article_id`, `event_key`, `issue_date` | Aynı haber, olay ve sayı gününe bağlanır. |
| `file` | `--images-root` altında göreli düzenli dosya; symlink ve `..` reddedilir. |
| `source_page`, `observed_on`, `image_url`, `observed_via` | Sayfa/RSS'de gerçekten görülen kaynak; tahmin edilen URL değildir. |
| `use_scope`, `role` | Gerçek sayı için newsletter, test için contract_test; story veya explanatory. |
| `sha256`, `mime_type`, `size_bytes`, `width`, `height` | Gerçek byte ve decode sonucuyla aynı olmalı. |
| `alt`, `credit`, `rights_note`, `selection_reason` | Kısa doğru alt/kredi ve özel seçim/hak gerekçesi. |
| `access_status`, `review` | normal_public_access; pixels_viewed, context_verified, date_verified, credit_verified, rights_verified_for_scope true ve note. |

Ölçüm için `render.inspect_image(Path(...))` kullanılır; normal erişimden
alınmış PNG/JPEG dosyası gerekir. Önce var olan decoder kontrol edilir. Yeni
kurulum gerektiriyorsa eksik yeteneği bildir; doğrulanmamış dosyayı ekleme.
WebP dönüştürme bu çekirdekte yoktur. Görsel başına 10 MiB, toplam 20 MiB ve
40 milyon piksel üst sınırı vardır; provider'ın daha düşük limiti ayrıca geçerlidir.

Bir başka mevcut araç aynı kaynaktan dosya edinmeyi destekliyorsa özel handoff
kaydı şu alanları bağlar: issue key, hazırlık sahibi, article/event/observed URL,
tek collector claim, dosya referansı/sürümü, hash ve inceleme. Claim CAS/readback
ile kesinleşmeden indirme başlamaz. Aynı claim yeniden indirme izni değildir;
receipt/import çakışırsa uzlaşılır. Bu repo Library xattr veya parent worker
varlığını varsaymaz. Somut handoff adaptörü ve gerçek ortam testi yoksa handoff
destekleniyor denmez; alternatif görsel veya gerekçeli görselsizlik kullanılır.

Doğrudan güvenlik reddinde indirici durur. Desteklenen normal tarayıcı aynı
açık kaynağa normal erişebiliyorsa bu ayrı kanıt olarak kaydedilir; tarayıcı
da CAPTCHA/güvenlik/erişim engeli gösterirse durulur. Proxy, kimlik taklidi veya
gizli endpoint ile aşma yapılmaz. Önceki günün veya testin görseli yeni sayıya
otomatik taşınmaz.

## Zamanlama ve çalışma bağlamı

Scheduler kaydı bir yürütme kanıtı değildir. Mevcut araçta önce kullanıcıya ait
gerçek timezone ve hedef proje doğrulanır. İlk scheduled test doğru runtime,
repo sürümü, aynı kalıcı kayıt, mail bağlantısı ve self-test kapsamını gerçek
tetiklenmede kaydeder. Dönen sohbet kimliğini doğrulama yerine kullanma.

`cloud_threads` veya parent/child dispatch genel bir API kabul edilmez. Bazı
ortamlarda kullanıcının zaten sahip olduğu doğrulanmış dispatch yolu bulunabilir;
yeni kullanıcıya bunu varmış gibi kurma. Yalnız doğrulanmış yöntem kullanılır.
Bu paket scheduler adaptörü, sürekli worker veya Cloud ortamı oluşturmaz.
