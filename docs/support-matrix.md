# Destek ve doğrulama sınırları

Kontrol tarihi: **19 Ekim 2026**. “Belgede var”, bu repo veya kullanıcının
hesabı üzerinde uçtan uca test edildi anlamına gelmez. Ürün yüzeyi, plan,
workspace, bölge ve bağlantı yetkileri değişebilir.

| Katman/ortam | Bu paketteki durum | Gerekli doğrulama |
| --- | --- | --- |
| Python + standart kütüphane | Profil, seçim, HTML/plain/MIME, yerel CAS ve alıcı koruması bu hazırlık ortamında offline test edildi. | Kullanıcının shell/dosya erişimi ve Python 3.9+ kontrolü. |
| PNG/JPEG + mevcut Pillow | Üç CID'nin byte koruması geçici sentetik PNG'lerle test edildi. | Gerçek dosya decode'u, piksel/olay/hak incelemesi ve gerçek mail istemcisi ayrıca gerekir. |
| ChatGPT/Codex Cloud | Resmî belge, yayımlanan ortamdan her görev için ayrı workspace başlatıldığını söylüyor. Bu paket adına yayımlanmış ortam ve mail/scheduler testi yok. | Kendi repoyla ortam hazırlama, Publish sonrası gerçek task ve ortak atomik state erişimi. [Cloud belgesi](https://learn.chatgpt.com/docs/environments/cloud-environments). |
| ChatGPT web tasks | Belgede mevcut bağlama açık dosya/araç desteği var; yerel klasörün görevler arasında tutulduğu söylenmiyor. | Dosyalar, araçlar ve kalıcı kayıt gerçek scheduled çalışmada doğrulanmalı. [Scheduled tasks](https://learn.chatgpt.com/docs/automations). |
| Desktop proje tasks | Belgede yerel proje/worktree zamanlaması var; bilgisayar ve app açık olmalı. Burada desktop scheduler testi yapılmadı. | Aynı özel state dosyasına erişim ve gerçek tetikleme testi. [Scheduled tasks](https://learn.chatgpt.com/docs/automations). |
| Codex CLI / IDE | Çekirdek dosya/shell erişimi varsa çalıştırılabilir. Belgede Scheduled yönetim arayüzü bu yüzeylerde sunulmuyor. | Scheduling için mevcut desteklenen yüzey gerekir; bu repo cron/servis kurmaz. [Scheduled tasks](https://learn.chatgpt.com/docs/automations). |
| Mail bağlantısı | Adaptör sözleşmesi var; hazır provider istemcisi ve bu starter üzerinde canlı mail testi yok. | Mevcut hesapta profil okuma, MIME taslak roundtrip, kullanıcı yetkisiyle kendine test. [Connected apps](https://help.openai.com/en/articles/11487775-connected-apps-in-chatgpt). |
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
