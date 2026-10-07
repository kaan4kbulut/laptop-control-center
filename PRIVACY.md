# Yayımlama gizliliği

Runtime veritabanı, token, kişisel not, sohbet, özel yedek, ham günlük ve makine envanteri depoya eklenmez. Örneklerde gerçek kullanıcı hesabı yerine `user`, adreslerde örnek domain kullanılır. Git kimliği GitHub kullanıcı adı ve GitHub noreply e-postası olur.

`tools/install-privacy-hooks.sh` yerel commit öncesi kontrolü kurar; mevcut farklı hooksPath'i ezmez. `python3 tools/privacy_check.py` izlenen dosyaları ve bütün erişilebilir Git geçmişini tarar. CI push/PR ve haftalık olarak aynı kontrolü çalıştırır. Tarayıcı bulunamazsa kontrol başarısız olur; sessizce atlanmaz. Yeni görsel/PDF/arşiv, incelenmiş checksum listesine alınmadan commit edilemez. Checksum onayı yalnız elle içerik ve metadata kontrolünden sonra verilir.

Git geçmişi gizlilik temizliği nedeniyle yeniden yazıldı. Eski klon/branch/bundle'ı yeni geçmişe merge veya force-push etmeyin: eski verileri geri getirir. Yeni temiz klon kullanın; commit edilmemiş çalışmalarınızı hassas veri kontrolünden geçirerek taşıyın. Orijinal özel verileri kendi yerel yedeğinizde tutun.

Otomatik kontroller bütün kişisel bilgileri anlayamaz; özellikle yazılı kişisel içerik ve yeni görseller ayrıca incelenir. Daha önce alınmış dış kopyalar geri çağrılamaz. `.privacy-policy.json` içinde `private-only` olan kişisel bilgi depoları herkese açılmaz.
