"""
service.py
----------
Android arka plan servisi. AlarmManager tarafından belirlenen
saatte (uygulama tamamen kapalı olsa bile) başlatılır ve
bildirimi gönderip bir sonraki alarmı kurduktan sonra kapanır.

buildozer.spec içine EKLENMESİ GEREKEN satır:
    services = Hatirlatici:service.py

'tur' extra'sına göre çalışır:
  - 'gunluk' -> Her gün 10:00: "Kolay Gelsin Ustam 👋
                İşler nasıl gidiyor?"
  - 'alacak' -> Alınacak ödeme varsa 2 günde bir 12:00:
                "[Müşteri] kişisinden [tutar] TL alınacak
                paranız var!"

Bildirim gönderildikten sonra bir sonraki alarm tekrar
kurulur, böylece hatırlatma zinciri kendini sürdürür ve
uygulama kapalıyken de çalışmaya devam eder.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bildirimler import (
    bildirim_gonder,
    alinacaklari_getir,
    gunluk_hatirlatmayi_planla,
    alacak_hatirlatmasini_planla,
)

# Servisi Android'e "çalışıyor" olarak bildir (foreground service).
try:
    from android import AndroidService
    _servis = AndroidService("İş Takip", "Hatırlatmalar aktif")
    _servis.start("İş Takip arka planda çalışıyor")
except Exception as e:
    print(f"[service] AndroidService başlatılamadı: {e}")

# Bu alarmı hangi 'tur' tetikledi?
_tur = None
try:
    from jnius import autoclass
    PythonService = autoclass("org.kivy.android.PythonService")
    _intent = PythonService.mService.getIntent()
    if _intent is not None:
        _tur = _intent.getStringExtra("tur")
except Exception as e:
    print(f"[service] intent okunamadı: {e}")

if _tur == "gunluk":
    bildirim_gonder(
        "Kolay Gelsin Ustam 👋",
        "İşler nasıl gidiyor?"
    )
    gunluk_hatirlatmayi_planla()

elif _tur == "alacak":
    for _musteri, _tutar in alinacaklari_getir():
        bildirim_gonder(
            "💰 Alınacak Ödeme",
            f"{_musteri} kişisinden {_tutar:.2f} TL alınacak paranız var!"
        )
    alacak_hatirlatmasini_planla()

else:
    # Bilinmeyen/ilk tetikleme durumunda hatırlatma zincirinin
    # kopmaması için her iki alarmı da yeniden kur.
    gunluk_hatirlatmayi_planla()
    alacak_hatirlatmasini_planla()

# Servis işini bitirdi, kapanabilir (bir sonraki alarm zaten kuruldu).
try:
    _servis.stop()
except Exception:
    pass
