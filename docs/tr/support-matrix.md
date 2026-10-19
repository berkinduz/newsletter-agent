# Destek ve doğrulama sınırları

[English](../support-matrix.md) · **Türkçe**

Kontrol tarihi: **19 Ekim 2026**. “Belgede var”, bu repo veya kullanıcının
hesabı üzerinde uçtan uca test edildi anlamına gelmez. Ürün yüzeyi, plan,
workspace, bölge ve bağlantı yetkileri değişebilir.

| Katman/ortam | Bu paketteki durum | Gerekli doğrulama |
| --- | --- | --- |
| Python + standart kütüphane | Profil, seçim, HTML/plain/MIME, yerel CAS ve alıcı koruması offline test edildi. Gmail MIME girdisi/raw doğrulaması ve Library CAS girdi/readback yardımcıları da sentetik testlidir. | Kullanıcının shell/dosya erişimi ve Python 3.9+ kontrolü; yardımcı testleri gerçek provider testi değildir. |
| Türkçe/İngilizce başlangıç | Eşleşen profiller, sentetik sayılar, etiketler, HTML/plain/MIME ve CLI kurulumu iki dilde de offline test edildi. | Kurulumda bülten dilini kullanıcıya sor; gerçek ajan içeriğinin seçilen dilde olduğunu kontrol et. Python çeviri yapmaz. |
| PNG/JPEG + mevcut Pillow | Üç CID'nin byte koruması geçici sentetik PNG'lerle test edildi. | Gerçek dosya decode'u, piksel/olay/hak incelemesi ve gerçek mail istemcisi ayrıca gerekir. |
| ChatGPT/Codex Cloud | Temiz repo görevinde shell/Python, offline çekirdek ve Pillow testleri geçti. Resmî belge her görev için ayrı workspace tarif ediyor; bu starter üzerinde canlı mail/scheduler testi yok. | Kendi repoyla gerçek görev açılışı ve ortak atomik state erişimi ayrıca kontrol edilir. [Cloud belgesi](https://learn.chatgpt.com/docs/environments/cloud-environments). |
| ChatGPT web tasks | Belgede mevcut bağlama açık dosya/araç desteği var; yerel klasörün görevler arasında tutulduğu söylenmiyor. | Dosyalar, araçlar ve kalıcı kayıt gerçek scheduled çalışmada doğrulanmalı. [Scheduled tasks](https://learn.chatgpt.com/docs/automations). |
| Desktop proje tasks | Belgede yerel proje/worktree zamanlaması var; bilgisayar ve app açık olmalı. Burada desktop scheduler testi yapılmadı. | Aynı özel state dosyasına erişim ve gerçek tetikleme testi. [Scheduled tasks](https://learn.chatgpt.com/docs/automations). |
| Codex CLI / IDE | Çekirdek dosya/shell erişimi varsa çalıştırılabilir. Belgede Scheduled yönetim arayüzü bu yüzeylerde sunulmuyor. | Scheduling için mevcut desteklenen yüzey gerekir; bu repo cron/servis kurmaz. [Scheduled tasks](https://learn.chatgpt.com/docs/automations). |
| Mail bağlantısı | Gmail structured MIME/raw/send_draft şemaları incelendi; somut ajan akışı ve offline yardımcılar var. Bu starter üzerinde canlı draft/send testi yok. | Mevcut hesapta profil okuma, MIME taslak roundtrip, kullanıcı yetkisiyle kendine test. [Onboarding](onboarding.md), [Connected apps](https://help.openai.com/en/articles/11487775-connected-apps-in-chatgpt). |
| Library ortak kayıt | Create/read/expected_current_version şemaları incelendi; aday, guarded replace ve tam readback yardımcıları var. | Önce ayrı, tek kullanımlık sentetik probe iki Cloud görevinde sınanır; stale yazı kesin çatışmalı ve içerik değişmemeli. CAS kanıtlanmadan kanonik ledger'a deneme yazılmaz. Offline benzetim bu canlı CAS testi değildir. |
| Cloud scheduler hedefi | Create şeması mevcut; incelenen araçta Cloud environment hedefi/dispatch alanı görünmedi. | Doğru projeye gerçek yürütme yolu olmadan schedule oluşturulmaz; kabul edilen kayıt başarı sayılmaz. |
| Library / cloud_threads / özel dispatcher | Çekirdeğin bağımlılığı değil; evrensel destek iddiası yok. | Somut araç erişimi ve hesap/runtime testi olmadan handoff veya dispatch hazır sayılmaz. |
| Uçtan uca günlük gönderim | Bu başlangıç için henüz doğrulanmadı. | Kendi test maili, doğru state ve gerçek scheduled test tamamlanmalı. |

Bağlantılar tüm kullanıcılarda aynı değildir. Resmî belge de kullanılabilirliği
hesap/plan/yüzey koşullarına bağlıyor; işlem onayı gerekiyorsa korunur.
[Connected apps](https://help.openai.com/en/articles/11487775-connected-apps-in-chatgpt).

Ücretsiz kaynak kodu AI kullanım limitlerini veya barındırma haklarını
değiştirmez. Uygulanabilir plan/kredi/ücret koşulları devam eder; ayrı API
kullanımı bu pakette gerekmez.
[Codex plan ve kullanım bilgisi](https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan).

Bu tablo bir hesap için canlı destek sertifikası değildir. Gerçek kurulum
sonucu `.local/capabilities.json` içinde kanıtlanır; çalışma çıktıları veya
özel kimlikler public kaynak dosyalarına eklenmez.
