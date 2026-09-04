# =========================================================
# FOTOĞRAF (Kamera / Galeri)
# =========================================================
#
# İş eklerken veya iş detayında fotoğraf çekip ya da galeriden
# seçip işe eklemeyi sağlar. Seçilen/çekilen fotoğraf, uygulamanın
# kendi "fotograflar" klasörüne kopyalanır; işe sadece dosya adı
# kaydedilir (isler.json içinde "fotograflar": [...] listesi).
#
# ÖNEMLİ (buildozer.spec):
#   android.permissions içine CAMERA ve READ_MEDIA_IMAGES
#   (Android 13+) / READ_EXTERNAL_STORAGE (eski sürümler) eklenmeli.
#
# NOT: Masaüstünde (Windows/Linux/Mac) kamera/galeri butonları
# çalışmaz (plyer bu özellikleri sadece Android/iOS'ta destekler),
# ama hata vermez, uygulamanın diğer kısımlarını etkilemez.

import os
import shutil
import time

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.utils import platform
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.image import AsyncImage
from kivy.uix.label import Label
from kivy.uix.button import Button

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FOTO_KLASORU = os.path.join(BASE_DIR, "fotograflar")

_BUTON = (0.88, 0.89, 0.91, 1)
_BUTON_METIN = (0.08, 0.09, 0.11, 1)
_BEYAZ = (0.96, 0.97, 0.98, 1)
_SOLUK = (0.70, 0.72, 0.76, 1)
_KIRMIZI = (0.85, 0.20, 0.20, 1)


# ---------------------------------------------------------
# Dosya işlemleri
# ---------------------------------------------------------

def _klasoru_hazirla():
    os.makedirs(FOTO_KLASORU, exist_ok=True)


def yeni_dosya_adi(uzanti=".jpg"):
    _klasoru_hazirla()
    zaman = time.strftime("%Y%m%d_%H%M%S")
    milis = int((time.time() % 1) * 1000)
    return f"foto_{zaman}_{milis}{uzanti}"


def tam_yol(dosya_adi):
    return os.path.join(FOTO_KLASORU, dosya_adi)


def _galeriden_kopyala(kaynak_yol):
    _klasoru_hazirla()
    if not kaynak_yol or not os.path.exists(kaynak_yol):
        return None

    _, uzanti = os.path.splitext(kaynak_yol)
    if not uzanti:
        uzanti = ".jpg"

    hedef_ad = yeni_dosya_adi(uzanti)

    try:
        shutil.copy2(kaynak_yol, tam_yol(hedef_ad))
        return hedef_ad
    except Exception as e:
        print(f"[fotograf] kopyalama hatası: {e}")
        return None


# plyer'ın Android kamera modülü (camera.take_picture),
# çıktı dosyasını doğrudan bir "file://" yolu olarak
# kameraya vermeye çalışır. Android 7.0+ (API 24+) bunu
# güvenlik nedeniyle reddeder (FileUriExposedException) ve
# kamera uygulaması açılamaz / sessizce başarısız olur.
# Bu yüzden Android'de kamerayı doğrudan bir FileProvider
# (content://) URI'siyle, pyjnius üzerinden açıyoruz.
_KAMERA_ISTEK_KODU = 91001


def _android_kamerayi_ac(hedef, dosya_adi, on_tamamlandi):

    from jnius import autoclass
    from android import activity, mActivity

    Intent = autoclass("android.content.Intent")
    MediaStore = autoclass("android.provider.MediaStore")
    FileProviderCls = autoclass(
        "androidx.core.content.FileProvider"
    )
    JFile = autoclass("java.io.File")

    aktivite = mActivity
    context = aktivite.getApplicationContext()

    yetki_adi = context.getPackageName() + ".fileprovider"

    uri = FileProviderCls.getUriForFile(
        context, yetki_adi, JFile(hedef)
    )

    intent = Intent(MediaStore.ACTION_IMAGE_CAPTURE)
    intent.putExtra(MediaStore.EXTRA_OUTPUT, uri)
    intent.addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION)
    intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)

    def _sonuc_geldi(
        request_code, result_code, data=None
    ):

        if request_code != _KAMERA_ISTEK_KODU:
            return

        try:
            activity.unbind(
                on_activity_result=_sonuc_geldi
            )
        except Exception:
            pass

        RESULT_OK = -1

        basarili = (
            result_code == RESULT_OK
            and os.path.exists(hedef)
            and os.path.getsize(hedef) > 0
        )

        Clock.schedule_once(
            lambda dt: on_tamamlandi(
                dosya_adi if basarili else None
            )
        )

    activity.bind(
        on_activity_result=_sonuc_geldi
    )

    if intent.resolveActivity(
        context.getPackageManager()
    ) is None:

        # Cihazda ACTION_IMAGE_CAPTURE'ı karşılayacak bir
        # kamera uygulaması yok.
        activity.unbind(
            on_activity_result=_sonuc_geldi
        )
        on_tamamlandi(None)
        return

    aktivite.startActivityForResult(
        intent, _KAMERA_ISTEK_KODU
    )


def kamera_ile_cek(on_tamamlandi):
    """
    Yerleşik kamera uygulamasını açar. Çekilen fotoğraf
    fotograflar klasörüne kaydedilir.
    on_tamamlandi(dosya_adi) çağrılır (başarısız/iptal -> None).
    """
    _klasoru_hazirla()
    dosya_adi = yeni_dosya_adi(".jpg")
    hedef = tam_yol(dosya_adi)

    if platform == "android":

        try:
            _android_kamerayi_ac(
                hedef, dosya_adi, on_tamamlandi
            )
        except Exception as e:
            print(f"[fotograf] kamera açılamadı: {e}")
            on_tamamlandi(None)

        return

    # Masaüstü (Windows/Linux/Mac): plyer kamerayı
    # desteklemiyorsa hata vermeden iptal edilir.
    try:
        from plyer import camera

        def _bitince(*args):
            if os.path.exists(hedef):
                on_tamamlandi(dosya_adi)
            else:
                on_tamamlandi(None)

        camera.take_picture(
            filename=hedef,
            on_complete=_bitince
        )

    except Exception as e:
        print(f"[fotograf] kamera açılamadı: {e}")
        on_tamamlandi(None)


def galeriden_sec(on_tamamlandi):
    """
    Galeri / dosya seçiciyi açar. Seçilen görsel fotograflar
    klasörüne kopyalanır. on_tamamlandi(dosya_adi) çağrılır.
    """
    try:
        from plyer import filechooser

        def _secildi(secim):
            if not secim:
                on_tamamlandi(None)
                return

            dosya_adi = _galeriden_kopyala(secim[0])
            on_tamamlandi(dosya_adi)

        filechooser.open_file(
            on_selection=_secildi,
            filters=[
                (
                    "Görseller",
                    "*.jpg",
                    "*.jpeg",
                    "*.png"
                )
            ]
        )

    except Exception as e:
        print(f"[fotograf] galeri açılamadı: {e}")
        on_tamamlandi(None)


# ---------------------------------------------------------
# Yeniden kullanılabilir widget: kamera/galeri butonları +
# küçük resim (thumbnail) listesi
# ---------------------------------------------------------

class FotografSecici(BoxLayout):

    def __init__(self, **kwargs):

        kwargs.setdefault("orientation", "vertical")
        kwargs.setdefault("spacing", dp(7))
        kwargs.setdefault("size_hint_y", None)

        super().__init__(**kwargs)

        self.dosyalar = []

        self.bind(
            minimum_height=self.setter("height")
        )

        baslik = Label(
            text="📷 Fotoğraflar",
            font_size=14,
            bold=True,
            color=_SOLUK,
            size_hint_y=None,
            height=dp(20),
            halign="left",
            valign="middle"
        )

        baslik.bind(
            size=lambda o, v: setattr(o, "text_size", v)
        )

        self.add_widget(baslik)

        buton_satir = BoxLayout(
            size_hint_y=None,
            height=dp(54),
            spacing=dp(7)
        )

        kamera_btn = Button(
            text="📷 KAMERA",
            background_normal="",
            background_color=_BUTON,
            color=_BUTON_METIN,
            font_size=15
        )
        kamera_btn.bind(on_press=self._kamera_ac)

        galeri_btn = Button(
            text="🖼 GALERİDEN SEÇ",
            background_normal="",
            background_color=_BUTON,
            color=_BUTON_METIN,
            font_size=15
        )
        galeri_btn.bind(on_press=self._galeri_ac)

        buton_satir.add_widget(kamera_btn)
        buton_satir.add_widget(galeri_btn)

        self.add_widget(buton_satir)

        self.thumb_scroll = ScrollView(
            size_hint_y=None,
            height=dp(100),
            do_scroll_y=False,
            do_scroll_x=True
        )

        self.thumb_kutu = BoxLayout(
            orientation="horizontal",
            spacing=dp(7),
            size_hint_x=None,
            size_hint_y=1
        )

        self.thumb_kutu.bind(
            minimum_width=self.thumb_kutu.setter("width")
        )

        self.thumb_scroll.add_widget(self.thumb_kutu)
        self.add_widget(self.thumb_scroll)

        self.durum_label = Label(
            text="",
            font_size=13,
            color=_SOLUK,
            size_hint_y=None,
            height=dp(18)
        )
        self.add_widget(self.durum_label)

    def yukle(self, dosyalar):
        self.dosyalar = list(dosyalar or [])
        self._listeyi_yenile()

    def _kamera_ac(self, *args):
        self.durum_label.text = "Kamera açılıyor..."
        kamera_ile_cek(self._eklendi)

    def _galeri_ac(self, *args):
        self.durum_label.text = "Galeri açılıyor..."
        galeriden_sec(self._eklendi)

    def _eklendi(self, dosya_adi):
        # Kamera/galeri sonucu farklı bir thread'den gelebilir,
        # Kivy arayüzünü ana thread'de güncelle.
        Clock.schedule_once(
            lambda dt: self._eklendi_ana(dosya_adi)
        )

    def _eklendi_ana(self, dosya_adi):
        if dosya_adi:
            self.dosyalar.append(dosya_adi)
            self.durum_label.text = "✅ Fotoğraf eklendi."
        else:
            self.durum_label.text = (
                "İşlem iptal edildi ya da başarısız."
            )
        self._listeyi_yenile()

    def _sil(self, dosya_adi, *args):
        if dosya_adi in self.dosyalar:
            self.dosyalar.remove(dosya_adi)
        self._listeyi_yenile()

    def _listeyi_yenile(self):
        self.thumb_kutu.clear_widgets()

        for dosya_adi in self.dosyalar:

            kutu = FloatLayout(
                size_hint=(None, None),
                size=(dp(90), dp(90))
            )

            img = AsyncImage(
                source=tam_yol(dosya_adi),
                size=(dp(90), dp(90)),
                size_hint=(None, None),
                pos=(0, 0)
            )

            sil_btn = Button(
                text="✕",
                size_hint=(None, None),
                size=(dp(26), dp(26)),
                pos=(dp(64), dp(64)),
                background_normal="",
                background_color=_KIRMIZI,
                color=_BEYAZ,
                font_size=14
            )

            sil_btn.bind(
                on_press=lambda inst, d=dosya_adi: self._sil(d)
            )

            kutu.add_widget(img)
            kutu.add_widget(sil_btn)

            self.thumb_kutu.add_widget(kutu)
