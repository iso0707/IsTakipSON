# =========================================================
# BİLDİRİMLER
# =========================================================
#
# Bu modül üç şeyi yönetir:
#   1) Her gün saat 10:00 -> "Kolay Gelsin Ustam 👋 İşler nasıl
#      gidiyor?" bildirimi
#   2) Alınacak ödeme varsa, 2 günde bir saat 12:00 ->
#      "[Müşteri] kişisinden [tutar] TL alınacak paranız var!"
#   3) Ayarlar ekranındaki "Test Bildirimi Gönder" butonu için
#      anlık test bildirimi
#
# Zamanlanmış bildirimler (uygulama kapalıyken de gelsin diye)
# Android AlarmManager + arka planda çalışan bir Python servisi
# (service.py) ile kurulur. AlarmManager, belirlenen saatte
# servisi uyandırır; servis bildirimi gönderir ve bir sonraki
# alarmı tekrar kurar.
#
# ÖNEMLİ (buildozer.spec):
#   services = Hatirlatici:service.py
#   android.permissions = INTERNET,POST_NOTIFICATIONS,
#       RECEIVE_BOOT_COMPLETED,WAKE_LOCK,SCHEDULE_EXACT_ALARM
#   requirements = ... ,plyer
#
# NOT: Bu dosya sadece Android'de alarm kurar. Masaüstünde
# (Windows/Linux/Mac) hiçbir şey yapmaz, mevcut özellikleri
# etkilemez.

import os
import json
import time
from datetime import datetime, timedelta

from kivy.utils import platform

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ISLER_DOSYASI = os.path.join(BASE_DIR, "isler.json")


# ---------------------------------------------------------
# isler.json'dan bağımsız, küçük yardımcılar (main.py ile
# döngüsel import olmasın diye burada tekrar tanımlandı)
# ---------------------------------------------------------

def _oku(dosya, varsayilan=None):
    if varsayilan is None:
        varsayilan = []
    if not os.path.exists(dosya):
        return varsayilan
    try:
        with open(dosya, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return varsayilan


def _para(deger):
    try:
        if isinstance(deger, str):
            deger = deger.replace(",", ".")
        return float(deger or 0)
    except Exception:
        return 0.0


def _toplam_malzeme(is_):
    toplam = 0
    for m in is_.get("malzemeler", []):
        toplam += _para(m.get("fiyat", 0))
    return toplam


def _alinacak_hesapla(malzemeli, iscilik, malzeme_toplami, alinan):
    if malzemeli:
        return iscilik - alinan
    return iscilik + malzeme_toplami - alinan


def alinacaklari_getir():
    """
    isler.json içindeki TÜM işleri tarar, müşteri bazında
    'alınacak' tutarları toplar. Sadece pozitif (>0) olanları
    döndürür: [(musteri, tutar), ...]
    """
    isler = _oku(ISLER_DOSYASI)
    musteri_toplam = {}

    for is_ in isler:
        iscilik = _para(is_.get("iscilik", 0))
        alinan = _para(is_.get("gelir", 0))
        malzeme_toplami = _toplam_malzeme(is_)
        malzemeli = is_.get("malzemeli", True)

        alinacak = _alinacak_hesapla(
            malzemeli, iscilik, malzeme_toplami, alinan
        )

        if alinacak > 0:
            musteri = is_.get("musteri", "").strip() or "İsimsiz Müşteri"
            musteri_toplam[musteri] = (
                musteri_toplam.get(musteri, 0) + alinacak
            )

    return [
        (m, t) for m, t in musteri_toplam.items() if t > 0
    ]


_BILDIRIM_KANAL_ID = "istakip_hatirlatma"
_BILDIRIM_KANAL_ADI = "İş Takip Hatırlatmaları"


def _android_bildirim_gonder(baslik, mesaj):
    """
    Bildirimi doğrudan Android API'siyle (pyjnius üzerinden)
    gönderir. plyer'ın Android bildirim modülü YERİNE bu
    kullanılıyor çünkü plyer, ikonu bulmak için uygulamanın
    kendi "PaketAdi.R$drawable" sınıfını arıyor; bu projede
    custom drawable kaynağı / icon.filename tanımlı olmadığı
    için o sınıf üretilmiyor ve plyer
    "JavaException: Class not found" hatasıyla patlıyor -
    Ayarlar'daki "Test Bildirimi Gönder" tuşunda görülen hata
    tam olarak buydu.

    Bu fonksiyon bunun yerine:
      - Android 8+ (API 26+) için gerekli NotificationChannel'ı
        oluşturur (channel olmadan bildirim sessizce gitmez /
        hata verir),
      - İkon olarak uygulamanın HER ZAMAN var olan launcher
        ikonunu (ApplicationInfo.icon) kullanır, böylece hiçbir
        custom kaynağa bağımlı değildir.
    """
    from jnius import autoclass, cast
    from android import mActivity

    Context = autoclass("android.content.Context")
    Build = autoclass("android.os.Build")
    NotificationManager = autoclass("android.app.NotificationManager")
    NotificationChannel = autoclass("android.app.NotificationChannel")
    NotificationCompat = autoclass("androidx.core.app.NotificationCompat")
    NotificationCompatBuilder = autoclass(
        "androidx.core.app.NotificationCompat$Builder"
    )
    NotificationManagerCompat = autoclass(
        "androidx.core.app.NotificationManagerCompat"
    )
    PendingIntent = autoclass("android.app.PendingIntent")

    activity = mActivity
    context = activity.getApplicationContext()

    if Build.VERSION.SDK_INT >= 26:
        manager = cast(
            "android.app.NotificationManager",
            context.getSystemService(Context.NOTIFICATION_SERVICE)
        )
        mevcut_kanal = manager.getNotificationChannel(
            _BILDIRIM_KANAL_ID
        )
        if mevcut_kanal is None:
            kanal = NotificationChannel(
                _BILDIRIM_KANAL_ID,
                _BILDIRIM_KANAL_ADI,
                NotificationManager.IMPORTANCE_HIGH
            )
            kanal.setDescription(
                "Günlük hatırlatma ve alınacak ödeme bildirimleri"
            )
            manager.createNotificationChannel(kanal)

    # Uygulamanın kendi launcher ikonu - custom drawable
    # kaynağına ihtiyaç duymaz, her zaman mevcuttur.
    ikon_id = context.getApplicationInfo().icon
    if not ikon_id:
        AndroidRDrawable = autoclass("android.R$drawable")
        ikon_id = AndroidRDrawable.sym_def_app_icon

    builder = NotificationCompatBuilder(context, _BILDIRIM_KANAL_ID)
    builder.setContentTitle(baslik)
    builder.setContentText(mesaj)
    builder.setSmallIcon(ikon_id)
    builder.setAutoCancel(True)
    builder.setPriority(NotificationCompat.PRIORITY_HIGH)

    try:
        launch_intent = context.getPackageManager().getLaunchIntentForPackage(
            context.getPackageName()
        )
        if launch_intent is not None:
            flag_immutable = 0
            if Build.VERSION.SDK_INT >= 23:
                flag_immutable = PendingIntent.FLAG_IMMUTABLE
            pending = PendingIntent.getActivity(
                context,
                0,
                launch_intent,
                PendingIntent.FLAG_UPDATE_CURRENT | flag_immutable
            )
            builder.setContentIntent(pending)
    except Exception:
        pass

    bildirim = builder.build()

    # Her bildirim için farklı bir id: aynı id kullanılırsa
    # üst üste gelen bildirimler birbirinin yerine geçer (ör.
    # birden fazla müşteri için alınacak ödeme bildirimi).
    bildirim_id = int(time.time_ns() % 2147483647)

    notif_manager_compat = getattr(NotificationManagerCompat, "from")(
        context
    )
    notif_manager_compat.notify(bildirim_id, bildirim)


def bildirim_gonder(baslik, mesaj):
    """
    Anlık bildirim gönderir. Diğer özellikleri etkilememesi için
    hata yükseltilmez, ama artık YUTULMUYOR: çağırana (basarili,
    hata_metni) olarak dönüyor ki arayüzde gösterilebilsin.
    Önceden hata sadece konsola yazılıyordu ve APK'de konsol
    görünmediği için kullanıcı hiçbir şey görmüyordu; "gönderildi"
    mesajı hep başarı gibi görünüyordu.

    Android'de önce yerel (pyjnius) yol denenir - plyer'ın bilinen
    ikon sorunundan etkilenmez. Başarısız olursa ya da Android
    değilse plyer'a düşülür (masaüstünde bildirimler plyer ile
    çalışmaya devam eder).
    """
    if platform == "android":
        try:
            _android_bildirim_gonder(baslik, mesaj)
            return True, None
        except Exception as e:
            hata = str(e)
            print(f"[bildirim] Android bildirimi gönderilemedi: {hata}")
            # plyer'ı yedek olarak dene, olur da başka bir
            # cihazda farklı davranırsa diye.

    try:
        from plyer import notification
        notification.notify(
            title=baslik,
            message=mesaj,
            app_name="İş Takip",
            timeout=10
        )
        return True, None
    except Exception as e:
        hata = str(e)
        print(f"[bildirim] gönderilemedi: {hata}")
        return False, hata


def test_bildirimi_gonder():
    """
    Ayarlar ekranındaki 'Test Bildirimi Gönder' butonu tarafından
    çağrılır. Tüm işlerdeki alınacak tutarları müşteri bazında
    toplar; varsa her müşteri için ayrı bir bildirim gönderir.
    Dönüş: kullanıcıya ekranda gösterilecek durum metni (artık
    gerçek başarı/başarısızlık durumunu yansıtıyor).
    """
    alinacaklar = alinacaklari_getir()

    if not alinacaklar:

        basarili, hata = bildirim_gonder(
            "İş Takip - Test",
            "Şu an alınacak bir ödemeniz görünmüyor."
        )

        if basarili:
            return "🔔 Test bildirimi gönderildi (alınacak yok)."

        return _hata_metni(hata)

    basarisiz_sayisi = 0
    son_hata = None

    for musteri, tutar in alinacaklar:

        basarili, hata = bildirim_gonder(
            "💰 Alınacak Ödeme",
            f"{musteri} kişisinden {tutar:.2f} TL alınacak paranız var!"
        )

        if not basarili:
            basarisiz_sayisi += 1
            son_hata = hata

    if basarisiz_sayisi == len(alinacaklar):
        return _hata_metni(son_hata)

    toplam = sum(t for _, t in alinacaklar)

    ek = (
        f" ({basarisiz_sayisi} tanesi gönderilemedi)"
        if basarisiz_sayisi
        else ""
    )

    return (
        f"🔔 Test bildirimi gönderildi. "
        f"{len(alinacaklar)} müşteri, toplam {toplam:.2f} TL.{ek}"
    )


def _hata_metni(hata):

    return (
        "❌ Bildirim gönderilemedi: "
        + (hata or "bilinmeyen hata")
        + "\nTelefon Ayarları > Uygulamalar > İş Takip > "
        "Bildirimler açık mı kontrol edin."
    )


# =========================================================
# ANDROID ALARM PLANLAMA (uygulama kapalıyken de çalışır)
# =========================================================

_GUNLUK_SAAT = 10
_GUNLUK_DAKIKA = 0

_ALACAK_SAAT = 12
_ALACAK_DAKIKA = 0
_ALACAK_GUN_ARALIGI = 2


def _sonraki_zaman(saat, dakika, gun_araligi=1):
    simdi = datetime.now()
    hedef = simdi.replace(
        hour=saat, minute=dakika, second=0, microsecond=0
    )
    if hedef <= simdi:
        hedef += timedelta(days=gun_araligi)
    return hedef


def _alarm_kur(tetik_zamani, tur):
    """
    Android AlarmManager ile belirtilen zamanda arka plan
    servisini (service.py, buildozer.spec'te 'Hatirlatici'
    olarak tanımlı) uyandırır. tur: 'gunluk' veya 'alacak'.
    """
    if platform != "android":
        return

    try:
        from jnius import autoclass, cast
        from android import mActivity

        AlarmManager = autoclass("android.app.AlarmManager")
        Context = autoclass("android.content.Context")
        Intent = autoclass("android.content.Intent")
        PendingIntent = autoclass("android.app.PendingIntent")
        Build = autoclass("android.os.Build")

        activity = mActivity
        context = activity.getApplicationContext()
        package_name = context.getPackageName()

        # buildozer.spec -> services = Hatirlatici:service.py
        # satırı bu servis sınıfını (ServiceHatirlatici) üretir.
        service_intent = Intent()
        service_intent.setClassName(
            package_name,
            package_name + ".ServiceHatirlatici"
        )
        service_intent.putExtra("tur", tur)

        flag_immutable = 0
        if Build.VERSION.SDK_INT >= 23:
            flag_immutable = PendingIntent.FLAG_IMMUTABLE

        request_code = 1001 if tur == "gunluk" else 1002

        pending = PendingIntent.getService(
            context,
            request_code,
            service_intent,
            PendingIntent.FLAG_UPDATE_CURRENT | flag_immutable
        )

        alarm_manager = cast(
            "android.app.AlarmManager",
            context.getSystemService(Context.ALARM_SERVICE)
        )

        millis = int(tetik_zamani.timestamp() * 1000)

        if Build.VERSION.SDK_INT >= 23:
            alarm_manager.setExactAndAllowWhileIdle(
                AlarmManager.RTC_WAKEUP, millis, pending
            )
        else:
            alarm_manager.setExact(
                AlarmManager.RTC_WAKEUP, millis, pending
            )

    except Exception as e:
        print(f"[bildirim] alarm kurulamadı ({tur}): {e}")


def gunluk_hatirlatmayi_planla():
    hedef = _sonraki_zaman(_GUNLUK_SAAT, _GUNLUK_DAKIKA, gun_araligi=1)
    _alarm_kur(hedef, "gunluk")


def alacak_hatirlatmasini_planla():
    hedef = _sonraki_zaman(
        _ALACAK_SAAT, _ALACAK_DAKIKA, gun_araligi=_ALACAK_GUN_ARALIGI
    )
    _alarm_kur(hedef, "alacak")


def tum_hatirlatmalari_planla():
    """
    Uygulama açılışında (App.build) bir kez çağrılır. Sadece
    Android'de alarmları kurar; masaüstünde hiçbir şey yapmaz,
    mevcut özellikleri etkilemez.
    """
    if platform != "android":
        return
    try:
        gunluk_hatirlatmayi_planla()
        alacak_hatirlatmasini_planla()
    except Exception as e:
        print(f"[bildirim] planlama hatası: {e}")
