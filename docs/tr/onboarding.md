# Ajan için uygulanabilir kurulum akışı

[English](../onboarding.md) · **Türkçe**

Kullanıcı repoyu kendi ChatGPT/Codex'ine açıp şunu söyleyebilir:

> Sincap Post'u benim için kur. AGENTS.md ve docs/tr/onboarding.md akışını izle.
> Önce mevcut araçları kontrol et ve sentetik önizlemeyi göster. Benden yalnız
> bülten tercihlerimi ve gereken işlem izinlerini iste; teknik alanları sen doldur.

Bu bir agent-tool entegrasyonudur: aşağıdaki yardımcılar gerçek Gmail/Library
çağrılarının girdisini ve doğrulamasını sağlar; dış çağrıyı ajan yapar. Python
komutları mail göndermez. Kullanıcının kurulum isteğini bütün dış işlemler için
sınırsız izin sayma. Mevcut açık yetkiyi kullan; eksik olan test/gönderim ve
schedule yetkisini somut önizlemeden sonra sor. Bu rehberi geliştirmek veya
offline denemek, provider taslağı/mail/schedule oluşturma yetkisi değildir.

## 1. Keşfet, tercihleri al, özel kaydı oluştur

README/setup/AGENTS kontrollerini yap; `bash scripts/setup.sh` çalıştır.
Mevcut `.local` varsa kaldığın aşamayı sürdür, `init` ile sıfırlama. Yeni
kurulumda `python3 -m sincap init --language tr`, özel `installation.json` dosyasını da yaratır.

Araç kataloğundan gerçek şemaları oku. Kullanılabilir en küçük yol:

| İş | Gerekli mevcut araç ve alanlar |
| --- | --- |
| Hesap | Gmail `get_profile(link_id)`; link yalnız o anki şemadaki hesap listesinden. |
| Taslak | `create_draft(link_id, from_address, to, subject, payload)`; nested MIME, content_id ve base64_url_content. |
| Geri okuma | `read_email(link_id, message_id, format="raw")`; tam raw byte elde edilemiyorsa bu yol tamamlanmaz. |
| Gönderim | `send_draft(link_id, draft_id)`; Sent arama/okuma da bulunmalı. |
| Ortak kayıt | Library create/read/replace; replace'in `expected_current_version` alanı ve tam dosya okuma. |
| Zamanlama | Mevcut scheduler create; ayrıca gerçekten bu repo/shell'e ulaşan hedef veya mevcut desteklenen dispatch yolu. |

Eksik araçta hangi aşamanın kullanılabildiğini söyle. İsim görünürlüğünü
bağlantı başarısı sayma. Yeni servis, credential veya plugin kurma.

Kullanıcıya topluca konu/kaynak tercihlerini, uzunluk/imza ve yerel yayın
saatini sor; zaten verilenleri tekrar sorma. Kaynak seçimini ajan araştırabilir.
Dil henüz belirtilmediyse açıkça **“Bültenin Türkçe mi, İngilizce mi olmasını
istersiniz?”** diye sor. Sohbet Türkçe diye bülteni Türkçe varsayma; kullanıcı
zaten dil seçtiyse tekrar sorma. Yanıtı `profile.language` alanına Türkçe için
`tr`, İngilizce için `en` olarak yaz. Yeni kurulumda yanıtla eşleşen
`init --language tr` veya `init --language en` kullan; CLI varsayılanı bu sorunun
yerine geçmez. Selamlama, imza, etiketler, konu/kaynak adları ve ajan tarafından
yazılan sayı içeriği seçilen dile uymalı. Mevcut profilde aynı kanonik kaydı
ve geçmişi koruyarak düzenleme yap; profil hash'i değişince etkilenen kanıtları
yeniden doğrula.
Birden fazla uygun mail hesabı varsa okunabilir hesap adlarıyla seçim iste.
Başka projeye ait hesap/kayıt/otomasyonu devralma. Seçilen hesapta zararsız
`get_profile` çağır; izin/reconnect ekranında o bağımlılığı beklet.

Başarılı cevabın gerçek `structuredContent` nesnesiyle:

```python
from sincap import onboarding as o
installation["mail"] = o.mail_connection(selected_link, profile_reply["structuredContent"])
profile["delivery"]["sender"] = installation["mail"]["email"]
```

Kimlikleri ajan doldurur; kullanıcıya link/file/draft/environment ID sorulmaz.
Gerçek runtime, git origin/HEAD ve profil hash'ini özel kayda ekle. Kullanıcının
seçtiği alıcıları profile yaz; ilk testin alıcısı aşağıda otomatik daraltılır.
`delivery.enabled` ve `schedule.enabled` şimdilik false kalır.

## 2. Önizlemeyi üret ve araç girdisine çevir

İlk demo için kullanıcının özelleştirilmiş profili yerine örnek profili kullan:

```sh
# Türkçe seçildiyse
python3 -m sincap prepare --demo --profile examples/tr/profile.json --input examples/tr/issue.json --at 2030-01-02T08:30:00Z --out .local/setup-preview-tr
# İngilizce seçildiyse
python3 -m sincap prepare --demo --profile examples/profile.json --input examples/issue.json --at 2030-01-02T08:30:00Z --out .local/setup-preview-en
```

Geniş/dar ekranda `preview.html` göster. Kullanıcının konu/kaynak/dil/uzunluk,
imza ve saat tercihlerini asıl özel profile uygula. Gerçek sayıya geçerken kaynakların yeterli
gövdesini/tarihini oku; görseller için normal erişim, byte ve piksel kontrolünü
uygula. Sentetik veri gerçek kaynak okuma kanıtı değildir.

`prepare` artık `delivery.json` içinde zarfı, içerik hash'ini ve görsel
manifestini de bırakır. Ajanın özel Python işinde:

```python
bundle = o.load_bundle(preview_directory)
test = o.self_test_bundle(bundle, installation["mail"], unique_test_key)
request = o.gmail_draft_args(test, installation["mail"])
```

`unique_test_key`, ajan tarafından üretilen ve özel kayda alınan `test/` anahtarıdır.
`request` tam `create_draft` girdisidir; bunu özel JSON dosyasında tut, tool'a
programatik taşı. Base64 byte'ları model çıktısına/loga dökme. Testin değişen
From/To/Subject alanlarını kullanıcıya göster. Henüz dış çağrı yapma.

## 3. Ayrı probe ile CAS'ı doğrula, sonra kanonik kaydı bağla

Library yoksa aynı dosya sisteminde manuel kullanım mümkündür; ayrı Cloud
görevleri için düzenli yayın kurulamaz. Mevcut Library skill'inin tam okuma,
materialization, xattr ve writeback kurallarını kullan.

Önce ayrı, sentetik ve tek kullanımlık bir özel Library probe dosyası oluştur.
Örneğin ilk JSON `{"version":0,"data":{"probe_only":true,"marker":"initial"}}`
olsun; gerçek profil, ledger, alıcı, mail veya geçmiş içermesin. Dönen gerçek
referansı `installation.shared_state.probe_library_file_id` içine yaz.
Bu referans kanonik `library_file_id` alanından ayrı kalır.

CAS yeteneği kanıtlanmadan gerçek kanonik ledger'a hiçbir deneme yazısı yapma.
Mevcut kurulumu sürdürürken kanonik referansı yalnız oku; sıfırlama, yerine
probe koyma veya probe'a canlı veri kopyalama. Aşağıdaki bütün capability/stale
yazıları yalnız bu yeni probe dosyasına gider.

Her görev aynı referansı tam okumalı. `has_more` varsa aynı dosya/sürümün bütün
parçalarını tamamla veya güncel Library skill'iyle tam dosyayı materialize et.
Tam `JSON.parse`/`json.loads` başarısı ve somut güncel provider sürümü gerekir.
Bu sayı materialization metadata'sındaki `current_version_number` gibi gerçek
bir değerden alınır; JSON içindeki `version` ile karıştırılmaz. Uygun bir
tamsayı sürüm elde edilemiyorsa CAS aşaması eksiktir.
Yeni Library kaydının ilk provider sürümü `0` olabilir; bu geçerli önkoşuldur.
`last_observed_version` yalnız özel bir nottur; sonraki işlemde güncel remote
sürümü yeniden oku. Kanonik JSON'un içinde kendi güncel provider sürümünü
sakladığını varsayma.

Yazma ve readback yolu (CAS kanıtlanana kadar yalnız probe hedefinde):

```python
candidate = o.library_candidate(snapshot, changed_data, unique_operation_id)
# candidate'ı yeni, 0600 bir özel JSON dosyasına yaz.
request = o.library_replace_args(probe_library_ref, actual_provider_version, candidate_path)
# Ajan: library_replace_library_file(**request), ardından aynı dosyayı tam geri oku.
o.verify_library_commit(candidate, full_readback, actual_provider_version, returned_new_version)
```

Çatışma: aynı referansı yeniden oku, değişikliği uzlaştır; eski byte'larla veya
sürüm önkoşulunu kaldırarak retry yapma. Timeout/sonuç belirsizliğinde önce tam
readback ve `last_operation` ile uzlaş. Send rezervasyonu yazılamadıysa mail yok.

**Gerçek iki Cloud görevi testi** (bu metin/test kodu testi geçmiş sayılmaz):

1. Görev A'da yalnız probe dosyasının provider sürümü N'yi al. Rastgele A
   işaretini CAS N ile yaz; tam readback ve yeni M sürümünü doğrula. Ajan özel
   devam promptunu hazırlar: probe referansı, beklenen origin/HEAD, N/M ve
   A adayının tam içerik hash'i içinde hazır olsun. Gerekli kurulum tercihleri
   özel devam promptunda taşınabilir; probe'un sentetik içeriğine eklenmez.
2. Kullanıcı aynı kayıtlı Cloud projesinde yeni görev açıp bu hazır promptu
   verir. Görev B, A'nın yerel dizinine güvenmeden aynı **probe** referansını
   tam okur ve A adayının sürüm/hash'ini doğrular; kanonik ledger'a yazmaz.
3. B, yalnız sentetik probe içeriğiyle **eski N** sürümünde guarded replace
   dener. Kesin sürüm çatışması beklenir. Sonra probe'u tam oku: A adayının
   hash'i ve M aynı kalmalı. Provider önkoşulu yok sayarsa yalnız probe etkilenir;
   test başarısızdır, kanonik yazma/gönderim açılmaz. Başka yazar, beklenmedik
   sürüm değişimi veya belirsizlikte de dur; canlı kayıtta telafi denemesi yapma.
4. B'nin yeni M sürümünde normal probe güncellemesi ve tam readback'i de geçerse
   aynı bağlantı/araç/runtime için çapraz görev CAS kanıtını özel kurulum kaydına
   yaz. Probe referansını kanonik referansa dönüştürme veya üretimde yeniden kullanma.

Bu test geçtikten sonra yeni kurulumda yerel `state.json` zarfının `data` alanına
`profile`, `installation` ve `capabilities` kopyalarını ekle; ayrı kanonik dosyayı
`create_library_file(file=...)` ile bir kez kaydet. Mevcut kurulumda yalnız mevcut
kanonik referansla devam et. Gerçek referans `installation.shared_state.library_file_id`
olur. Kanonik güncellemelerde yukarıdaki helper'a bu referansı ve o dosyanın yeni
okunmuş sürümünü ver; probe'un referans/sürümünü taşıma. Bağlantı veya CAS yolu
değişirse capability testini yine yeni, ayrı bir probe'da yap.

Kullanıcı bu teknik alanları elle doldurmaz. Ajan devam promptunu üretir; yeni
görev açmak desteklenen UI ile yapılabilir. Çağrılabilir dispatch yokken varmış
gibi bir API veya parent worker icat etme.

Sonraki görevde test içeriği de erişilebilir olmalı. Onaylanan sentetik bundle'ın
`raw` byte'larını ayrı, özel ve değiştirilmeyen bir `.eml` Library dosyasında tut.
Kanonik `data.onboarding_artifact` kaydına gerçek dosya/sürüm referansını ve
`o.bundle_contract(bundle)` sonucunu ekle. Bu manifest görsel byte'larını
çoğaltmaz. Yeni görev o sürümün gerçek byte'larını getirip
`o.restore_bundle(raw_bytes, saved_contract)` ile hash/zarf/CID kontrolünü yapar;
sonra yeni test anahtarıyla `self_test_bundle` üretir. Eski `.local` klasörünü
veya provider'daki gönderilmiş taslağı yeniden kullanmayı varsayma.

## 4. Açık yetkiyle Gmail taslak → doğrulama → gönderim

Bu aşama yalnız kullanıcının kendi doğrulanmış adresine test yetkisiyle yapılır.
Kanonik kayıtta bu test anahtarının sonuç/draft intent durumunu önce oku.
Sent/sending/uncertain veya sonucu belirsiz create varsa yeni çağrı açma.

1. `data.draft_intents[test_key]` içine hesap, içerik/recipient hash ve tek
   operation ID'li `requested` niyetini yukarıdaki CAS/readback ile yaz.
2. Hazır `request` ile Gmail `create_draft` çağır. Dönen **gerçek draft_id ve
   message_id** değerlerini kaydet. Alanlar belirsizse mevcut `list_drafts`
   metadata'sıyla o taslağı çöz; mesaj ID'sini draft ID yerine geçirme. Oluşturma
   sonucu belirsizse yeni taslak yaratma; önce mevcut taslaklarla uzlaştır.
3. Aynı hesap ve gerçek message ID ile `read_email(format="raw")` çağır.
   Cevabın tam base64url raw alanını `o.verify_gmail_raw(test, returned_raw)` ile
   doğrula. Bu kontrol zarfı, plain/HTML ve bütün CID hash/byte'larını sınar.
   Başarılı draft roundtrip'i ve gerçek draft/message kimliklerini CAS ile kaydet.
4. `candidate = o.reserve_bundle(latest_snapshot, test, attempt_id)` üret;
   guarded replace ve `verify_library_commit` ile **sending** kaydını doğrula.
   Gerçek saat, hesap, alıcı ve mevcut açık yetkiyi son anda yeniden kontrol et;
   `delivery.assert_send_allowed` için yalnız bu hesabın kendine-test profilini,
   `self_test=True` ve `test/` anahtarını kullan.
5. Yalnız `send_draft(link_id=verified_link, draft_id=actual_draft_id)` çağır.
   Dönen provider mesajını ve aynı hesaptaki eşleşen Sent'i oku. Zarf/içerik/CID
   kontrolünü tekrar yap; alıcının Inbox görünümünü ayrıca doğrula.
6. `delivery.record_result` sonucunu `data.test_deliveries[test_key]` içinde
   CAS/readback ile işle. Testte `advance_once`/`record_publication` çağırma;
   üretim sayısı/geçmişi değişmez. Timeout/iptal kaydı uncertain kalır, kör retry yok.

Üretim akışı da aynı helper ve CAS yolunu kullanır; her gün yeni hazırlanmış
bundle gerekir. `delivery.assert_send_allowed` ile gerçek gün/saat ve profil
bayraklarını kontrol et. Sonuç + `advance_once` + `core.record_publication`
aynı CAS içindedir. Kısmi onarımda mevcut delivery/eligible alıcıları koru;
`reserve_bundle` yeni issue içindir, mevcut issue'yu resetleme yolu değildir.

## 5. Scheduled test ve kurulumun bitişi

Mail testi ve iki görev CAS testi geçmeden düzenli yayın oluşturma. Scheduler
şeması hedef Cloud projesini seçemiyor ve mevcut bağlamın o repo/shell'e ulaşacağı
doğrulanamıyorsa bu aşamada dur: **manuel kullanım hazır, otomasyon eksik**.
Kullanıcıdan API alanları istemek veya başka projeye dispatch yapmak çözüm değildir.

Desteklenen hedef yolu ve açık schedule yetkisi varsa ajan `o.scheduled_test_prompt`
ile gerçek kanonik referans/repo sürümü/yeni `test/` anahtarını içeren özel promptu
üretir. Türkçe operasyon yönergesi için `language="tr"` verir; varsayılan
İngilizcedir ve bültenin kaydedilmiş içerik dilini değiştirmez. Mevcut automation create çağrısına `title`, bu `prompt`, kullanıcının
timezone'unda gerçek gelecek `schedule` ve uygun `timing_mode` verir. Hedef seçimi
yalnız mevcut şemanın/UI'nın desteklediği alanlarla yapılır; hayali environment
parametresi ekleme. Kabul edilen schedule kaydı yalnız kayıt kabulüdür.

Gerçek tetiklenmede repo/runtime, aynı Library dosyası ve CAS, aynı Gmail hesabı,
yerel saat kapısı ve kendine-test sonucu yeniden kanıtlanmalı. Test gerçek saati
bekler; `now/run_now` yerine gerçek scheduler tetiklemesi gerekir. Sonuç aynı
özel kayda yazılır. `doctor --stage scheduled` ancak gerçek ve güncel kanıtla
geçer; bayrağı/kanıt alanını elle açmak kurulum değildir.

Sonra kullanıcının düzenli yayın yetkisi kapsamında profil bayraklarını ve
onaylanan saati aynı kanonik kayıtta etkinleştir; mevcut test schedule'ını günlük
yeni araştırma/prepare/CAS/draft/verify/send akışına dönüştür. Saat/konu/alıcı
değişikliğini izin kapsamıyla eşleştir; ikinci sender/schedule yaratma.
Profil bayrakları hash'i değiştirdiğinden etkilenen kanıtları güncel etkin
profil ve gerçek okumalarla yeniden bağla; eski profile ait doktor sonucunu
yeni yapılandırmaya taşıma.
