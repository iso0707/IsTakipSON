import json
import os
import shutil
import calendar
from datetime import datetime

import bildirimler
from fotograf import FotografSecici

from kivy.app import App
from kivy.core.window import Window
from kivy.core.audio import SoundLoader
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.metrics import dp
from kivy.uix.screenmanager import (
    ScreenManager,
    Screen,
    FadeTransition
)
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.uix.spinner import Spinner
from kivy.uix.progressbar import ProgressBar
from kivy.uix.widget import Widget
from kivy.graphics import Color, RoundedRectangle, Line

# Makbuz (PDF) oluşturma için fpdf2 kullanılır.
# buildozer.spec -> requirements kısmına
# "fpdf2" eklenmelidir.
try:
    from fpdf import FPDF
except Exception:
    FPDF = None

# Android paylaşım menüsünü açmak için plyer
# kullanılır. buildozer.spec -> requirements
# kısmına "plyer" eklenmelidir.
try:
    from plyer import share as _paylasim_servisi
except Exception:
    _paylasim_servisi = None


# =========================================================
# DOSYALAR
# =========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ISLER_DOSYASI = os.path.join(
    BASE_DIR,
    "isler.json"
)

YERLER_DOSYASI = os.path.join(
    BASE_DIR,
    "yerler.json"
)

YEDEK_KLASORU = os.path.join(
    BASE_DIR,
    "yedekler"
)

SES_DOSYASI = os.path.join(
    BASE_DIR,
    "acilis_sesi.mp3"
)

# İlk kurulumda kaydedilen Firma/Kişi adı
# ve telefon numarası burada saklanır.
AYAR_DOSYASI = os.path.join(
    BASE_DIR,
    "ayarlar.json"
)

# Oluşturulan PDF makbuzlar bu klasöre
# kaydedilir.
MAKBUZ_KLASORU = os.path.join(
    BASE_DIR,
    "makbuzlar"
)

# İsteğe bağlı firma logosu. Bu dosya adıyla
# (logo.png) uygulama klasörüne eklenirse
# makbuzlarda otomatik kullanılır.
LOGO_DOSYASI = os.path.join(
    BASE_DIR,
    "logo.png"
)


# =========================================================
# TEMA
# =========================================================

ARKA = (0.12, 0.13, 0.15, 1)
KART = (0.20, 0.21, 0.24, 1)

BUTON = (0.88, 0.89, 0.91, 1)
BUTON_BASILDI = (0.72, 0.74, 0.78, 1)
BUTON_METIN = (0.08, 0.09, 0.11, 1)

BEYAZ = (0.96, 0.97, 0.98, 1)
SOLUK = (0.70, 0.72, 0.76, 1)

GIRIS = (0.94, 0.95, 0.97, 1)
GIRIS_METIN = (0.08, 0.09, 0.11, 1)

YESIL = (0.20, 0.65, 0.30, 1)
KIRMIZI = (0.85, 0.20, 0.20, 1)
SARI = (0.96, 0.78, 0.10, 1)
SARI_METIN = (0.10, 0.08, 0.02, 1)

GIDER_IKONLARI = {
    "Yakıt": "⛽",
    "Malzeme Özel": "🧰",
    "Gıda": "🍔",
    "Yardımcı Eleman": "🧑‍🔧"
}


# =========================================================
# JSON
# =========================================================

def oku(dosya, varsayilan=None):

    if varsayilan is None:
        varsayilan = []

    if not os.path.exists(dosya):
        return varsayilan

    try:
        with open(
            dosya,
            "r",
            encoding="utf-8"
        ) as f:
            return json.load(f)

    except Exception:
        return varsayilan


def kaydet(dosya, veri):

    with open(
        dosya,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            veri,
            f,
            ensure_ascii=False,
            indent=4
        )


def para(deger):

    try:

        if isinstance(deger, str):
            deger = deger.replace(",", ".")

        return float(deger or 0)

    except Exception:
        return 0.0


# =========================================================
# AYARLAR (FİRMA / TELEFON)
# =========================================================

def ayarlari_oku():

    return oku(
        AYAR_DOSYASI,
        {}
    )


def ayarlari_kaydet(veri):

    kaydet(
        AYAR_DOSYASI,
        veri
    )


def telefon_formatla(ham):

    # Sadece rakamları al, en fazla 11
    # hane (0532 123 45 67).
    rakamlar = "".join(
        ch for ch in (ham or "")
        if ch.isdigit()
    )[:11]

    parcalar = []

    if len(rakamlar) > 0:
        parcalar.append(rakamlar[0:4])

    if len(rakamlar) > 4:
        parcalar.append(rakamlar[4:7])

    if len(rakamlar) > 7:
        parcalar.append(rakamlar[7:9])

    if len(rakamlar) > 9:
        parcalar.append(rakamlar[9:11])

    return " ".join(
        p for p in parcalar if p
    )


class TelefonInput(TextInput):

    # Telefon numarasını "0532 123 45 67" biçiminde
    # canlı olarak biçimlendiren giriş kutusu.
    #
    # NOT: Bu biçimlendirme kasıtlı olarak text=
    # property'sine bind() ile DEĞİL, insert_text /
    # do_backspace metodlarını override ederek yapılır.
    # TextInput.text'i bir "text değişti" callback'i
    # içinden değiştirmek Kivy'de imleç/satır durumunun
    # bozulmasına ve girişin belirli bir haneden sonra
    # tıkanmasına yol açar (bilinen bir Kivy davranışı).

    def __init__(
        self,
        hint="",
        **kwargs
    ):

        kwargs.setdefault(
            "multiline", False
        )

        kwargs.setdefault(
            "size_hint_y", None
        )

        kwargs.setdefault(
            "height", dp(58)
        )

        super().__init__(
            hint_text=hint,
            font_size=19,
            padding=[
                dp(13),
                dp(13)
            ],
            background_normal="",
            background_color=GIRIS,
            foreground_color=GIRIS_METIN,
            hint_text_color=(
                0.42,
                0.44,
                0.48,
                1
            ),
            cursor_color=GIRIS_METIN,
            **kwargs
        )

    def insert_text(
        self,
        substring,
        from_undo=False
    ):

        mevcut = "".join(
            ch for ch in self.text
            if ch.isdigit()
        )

        yeni = "".join(
            ch for ch in substring
            if ch.isdigit()
        )

        rakamlar = (mevcut + yeni)[:11]

        self.text = telefon_formatla(
            rakamlar
        )

        self.cursor = (
            len(self.text), 0
        )

    def do_backspace(
        self,
        from_undo=False,
        mode="bkspc"
    ):

        rakamlar = "".join(
            ch for ch in self.text
            if ch.isdigit()
        )[:-1]

        self.text = telefon_formatla(
            rakamlar
        )

        self.cursor = (
            len(self.text), 0
        )


def telefon_girisi(hint=""):

    return TelefonInput(hint=hint)


# =========================================================
# BUTON
# =========================================================

class YuvarlakButon(Button):

    def __init__(
        self,
        ozel_renk=None,
        **kwargs
    ):

        self.ozel_renk = ozel_renk

        kwargs.setdefault(
            "background_normal",
            ""
        )

        kwargs.setdefault(
            "background_color",
            (0, 0, 0, 0)
        )

        kwargs.setdefault(
            "color",
            BUTON_METIN
        )

        kwargs.setdefault(
            "halign",
            "center"
        )

        kwargs.setdefault(
            "valign",
            "middle"
        )

        super().__init__(**kwargs)

        with self.canvas.before:

            self._renk = Color(
                *(
                    self.ozel_renk
                    if self.ozel_renk
                    else BUTON
                )
            )

            self._arka = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[dp(14)]
            )

        self.bind(
            pos=self._guncelle,
            size=self._guncelle,
            state=self._durum
        )

    def _guncelle(self, *args):

        self._arka.pos = self.pos
        self._arka.size = self.size

    def _durum(self, *args):

        if self.state == "down":

            if self.ozel_renk:

                self._renk.rgba = tuple(
                    max(0, x * 0.8)
                    if i < 3
                    else x
                    for i, x
                    in enumerate(self.ozel_renk)
                )

            else:

                self._renk.rgba = (
                    BUTON_BASILDI
                )

        else:

            self._renk.rgba = (
                self.ozel_renk
                if self.ozel_renk
                else BUTON
            )

    def renk_degistir(self, yeni_renk):

        self.ozel_renk = yeni_renk

        self._renk.rgba = (
            yeni_renk
            if yeni_renk
            else BUTON
        )


def buton(
    yazi,
    renk=None,
    yukseklik=58,
    font=18
):

    return YuvarlakButon(
        text=yazi,
        size_hint_y=None,
        height=dp(yukseklik),
        font_size=font,
        ozel_renk=renk
    )


# =========================================================
# KIRMIZI KUTU
# =========================================================

class KirmiziKutu(Label):

    def __init__(
        self,
        **kwargs
    ):

        super().__init__(**kwargs)

        with self.canvas.before:

            self._renk = Color(*KIRMIZI)

            self._arka = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[dp(14)]
            )

        self.bind(
            pos=self._guncelle,
            size=self._guncelle
        )

    def _guncelle(self, *args):

        self._arka.pos = self.pos
        self._arka.size = self.size

    def renk_ayarla(self, renk):

        self._renk.rgba = renk


# =========================================================
# GİRİŞ
# =========================================================

def giris(
    hint="",
    multiline=False,
    height=58,
    input_filter=None
):

    return TextInput(
        hint_text=hint,
        multiline=multiline,
        input_filter=input_filter,
        size_hint_y=None,
        height=dp(height),
        font_size=19,
        padding=[
            dp(13),
            dp(13)
        ],
        background_normal="",
        background_color=GIRIS,
        foreground_color=GIRIS_METIN,
        hint_text_color=(
            0.42,
            0.44,
            0.48,
            1
        ),
        cursor_color=GIRIS_METIN
    )


def baslik(
    yazi,
    boyut=25
):

    return Label(
        text=yazi,
        font_size=boyut,
        bold=True,
        color=BEYAZ,
        size_hint_y=None,
        height=dp(52)
    )


def etiketli_alan(
    yazi,
    alan
):

    kutu = BoxLayout(
        orientation="vertical",
        spacing=dp(2),
        size_hint_y=None
    )

    kutu.bind(
        minimum_height=
        kutu.setter("height")
    )

    etiket = Label(
        text=yazi,
        font_size=14,
        color=SOLUK,
        bold=True,
        size_hint_y=None,
        height=dp(20),
        halign="left",
        valign="middle"
    )

    etiket.bind(
        size=lambda obj, val:
        setattr(
            obj,
            "text_size",
            val
        )
    )

    kutu.add_widget(etiket)
    kutu.add_widget(alan)

    return kutu


# =========================================================
# HESAPLAMA
# =========================================================

def toplam_malzeme(is_):

    toplam = 0

    for m in is_.get(
        "malzemeler",
        []
    ):

        toplam += para(
            m.get("fiyat", 0)
        )

    return toplam


def is_durumu(is_):

    return is_.get(
        "durum",
        "Devam ediyor"
    )


def alinacak_hesapla(
    malzemeli,
    iscilik,
    malzeme_toplami,
    alinan
):
    # Malzemeli işlerde malzeme tutarı zaten
    # işçilik rakamına dahil edilmiş kabul
    # edilir; bu yüzden alınacak tutara
    # tekrar eklenmez. Malzemesiz işlerde
    # malzeme tutarı ayrıca eklenir.

    if malzemeli:

        return iscilik - alinan

    return (
        iscilik
        + malzeme_toplami
        - alinan
    )


def bu_ay_mi(
    tarih,
    yil=None,
    ay=None
):

    try:

        tarih = datetime.strptime(
            tarih,
            "%d.%m.%Y %H:%M"
        )

        if yil is None or ay is None:

            simdi = datetime.now()

            yil = simdi.year
            ay = simdi.month

        return (
            tarih.month == ay
            and
            tarih.year == yil
        )

    except Exception:
        return False


def kayit_tarihi(baslangic_metni):

    try:

        secilen = datetime.strptime(
            baslangic_metni.strip(),
            "%d.%m.%Y"
        )

        saat = datetime.now().strftime(
            "%H:%M"
        )

        return (
            secilen.strftime("%d.%m.%Y")
            + " "
            + saat
        )

    except Exception:

        return datetime.now().strftime(
            "%d.%m.%Y %H:%M"
        )


def hesaplar(
    yil=None,
    ay=None
):

    isler = oku(
        ISLER_DOSYASI
    )

    ay_gelir = 0
    ay_gider = 0
    ay_malzeme = 0
    ay_malzeme_kar = 0
    ay_malzeme_alinacak = 0
    ay_iscilik = 0

    toplam_gelir = 0
    toplam_gider = 0
    toplam_malzeme_para = 0
    toplam_malzeme_kar = 0
    toplam_iscilik = 0

    for is_ in isler:

        gelir = para(
            is_.get("gelir", 0)
        )

        gider = para(
            is_.get("gider", 0)
        )

        malzeme = toplam_malzeme(
            is_
        )

        malzemeli = is_.get(
            "malzemeli",
            True
        )

        malzeme_kar = (
            malzeme
            if malzemeli
            else 0
        )

        # Malzemeli işlerde malzeme tutarı
        # zaten işçilik rakamına dahil
        # olduğundan alınacak tutara
        # tekrar eklenmez.
        malzeme_alinacak = (
            0
            if malzemeli
            else malzeme
        )

        iscilik = para(
            is_.get("iscilik", 0)
        )

        toplam_gelir += gelir
        toplam_gider += gider
        toplam_malzeme_para += malzeme
        toplam_malzeme_kar += malzeme_kar
        toplam_iscilik += iscilik

        if bu_ay_mi(
            is_.get("tarih", ""),
            yil,
            ay
        ):

            ay_gelir += gelir
            ay_gider += gider
            ay_malzeme += malzeme
            ay_malzeme_kar += malzeme_kar
            ay_malzeme_alinacak += malzeme_alinacak
            ay_iscilik += iscilik

    return {

        "ay_gelir": ay_gelir,

        "ay_gider": ay_gider,

        "ay_malzeme": ay_malzeme,

        "ay_iscilik": ay_iscilik,

        "ay_alinacak":
            ay_iscilik
            + ay_malzeme_alinacak
            - ay_gelir,

        "ay_net":
            ay_gelir
            - ay_gider
            - ay_malzeme_kar,

        "toplam_gelir":
            toplam_gelir,

        "toplam_gider":
            toplam_gider,

        "toplam_malzeme":
            toplam_malzeme_para,

        "toplam_iscilik":
            toplam_iscilik,

        "toplam_net":
            toplam_gelir
            - toplam_gider
            - toplam_malzeme_kar
    }


# =========================================================
# KLAVYE
# =========================================================

def klavye_uyumu(
    scroll,
    widget
):

    def odak(
        instance,
        value
    ):

        if value:

            Clock.schedule_once(
                lambda dt:
                scroll.scroll_to(
                    widget,
                    padding=dp(150)
                ),
                0.15
            )

    widget.bind(
        focus=odak
    )


# =========================================================
# ÜST BAŞLIK
# =========================================================

def ust_baslik(
    screen,
    yazi,
    geri_ekran
):

    satir = BoxLayout(
        size_hint_y=None,
        height=dp(62),
        spacing=dp(8)
    )

    geri = buton(
        "←",
        renk=KIRMIZI,
        yukseklik=56,
        font=30
    )

    geri.size_hint_x = None
    geri.width = dp(58)

    geri.bind(
        on_press=lambda *_:
        setattr(
            screen.manager,
            "current",
            geri_ekran
        )
    )

    bas = Label(
        text=yazi,
        font_size=25,
        bold=True,
        color=BEYAZ,
        halign="left",
        valign="middle"
    )

    bas.bind(
        size=lambda obj, val:
        setattr(
            obj,
            "text_size",
            val
        )
    )

    satir.add_widget(geri)
    satir.add_widget(bas)

    return satir


# =========================================================
# TAKVİM
# =========================================================

class TakvimPopup(Popup):

    AY_ISIMLERI = [
        "Ocak",
        "Şubat",
        "Mart",
        "Nisan",
        "Mayıs",
        "Haziran",
        "Temmuz",
        "Ağustos",
        "Eylül",
        "Ekim",
        "Kasım",
        "Aralık"
    ]

    HAFTA = [
        "Pzt",
        "Sal",
        "Çar",
        "Per",
        "Cum",
        "Cmt",
        "Paz"
    ]

    def __init__(
        self,
        hedef,
        **kwargs
    ):

        self.hedef = hedef

        bugun = datetime.now()

        self.yil = bugun.year
        self.ay = bugun.month

        try:

            mevcut = datetime.strptime(
                hedef.text.strip(),
                "%d.%m.%Y"
            )

            self.yil = mevcut.year
            self.ay = mevcut.month

        except Exception:
            pass

        super().__init__(
            title="Tarih Seç",
            size_hint=(0.94, 0.82),
            auto_dismiss=True,
            **kwargs
        )

        self.govde = BoxLayout(
            orientation="vertical",
            padding=dp(8),
            spacing=dp(6)
        )

        self.content = self.govde

        self.guncelle()

    def guncelle(self):

        self.govde.clear_widgets()

        ust = BoxLayout(
            size_hint_y=None,
            height=dp(56),
            spacing=dp(5)
        )

        onceki = buton(
            "‹",
            yukseklik=54,
            font=30
        )

        onceki.size_hint_x = .18

        onceki.bind(
            on_press=self.onceki_ay
        )

        ay_baslik = Label(
            text=(
                f"{self.AY_ISIMLERI[self.ay - 1]} "
                f"{self.yil}"
            ),
            font_size=20,
            bold=True,
            color=BEYAZ
        )

        sonraki = buton(
            "›",
            yukseklik=54,
            font=30
        )

        sonraki.size_hint_x = .18

        sonraki.bind(
            on_press=self.sonraki_ay
        )

        ust.add_widget(onceki)
        ust.add_widget(ay_baslik)
        ust.add_widget(sonraki)

        self.govde.add_widget(ust)

        hafta = GridLayout(
            cols=7,
            size_hint_y=None,
            height=dp(35)
        )

        for gun in self.HAFTA:

            hafta.add_widget(
                Label(
                    text=gun,
                    font_size=14,
                    bold=True,
                    color=BEYAZ
                )
            )

        self.govde.add_widget(hafta)

        grid = GridLayout(
            cols=7,
            spacing=dp(3),
            size_hint_y=None,
            height=dp(6 * 49)
        )

        ilk_gun, gun_sayisi = calendar.monthrange(
            self.yil,
            self.ay
        )

        for _ in range(ilk_gun):

            grid.add_widget(
                Label(text="")
            )

        for gun in range(
            1,
            gun_sayisi + 1
        ):

            b = buton(
                str(gun),
                yukseklik=46,
                font=16
            )

            b.bind(
                on_press=lambda _, g=gun:
                self.gun_sec(g)
            )

            grid.add_widget(b)

        kalan = 42 - (
            ilk_gun + gun_sayisi
        )

        for _ in range(kalan):

            grid.add_widget(
                Label(text="")
            )

        self.govde.add_widget(grid)

        kapat = buton(
            "KAPAT",
            yukseklik=50,
            font=17
        )

        kapat.bind(
            on_press=lambda *_:
            self.dismiss()
        )

        self.govde.add_widget(kapat)

    def onceki_ay(self, instance):

        self.ay -= 1

        if self.ay == 0:
            self.ay = 12
            self.yil -= 1

        self.guncelle()

    def sonraki_ay(self, instance):

        self.ay += 1

        if self.ay == 13:
            self.ay = 1
            self.yil += 1

        self.guncelle()

    def gun_sec(self, gun):

        self.hedef.text = (
            f"{gun:02d}."
            f"{self.ay:02d}."
            f"{self.yil}"
        )

        self.dismiss()


class TarihInput(TextInput):

    def __init__(
        self,
        on_tarih=None,
        **kwargs
    ):

        self.on_tarih = on_tarih

        super().__init__(
            readonly=True,
            multiline=False,
            **kwargs
        )

        self.font_size = 19

        self.padding = [
            dp(13),
            dp(13)
        ]

        self.background_normal = ""

        self.background_color = GIRIS

        self.foreground_color = GIRIS_METIN

        self.hint_text_color = (
            0.42,
            0.44,
            0.48,
            1
        )

    def on_touch_down(
        self,
        touch
    ):

        if self.collide_point(
            *touch.pos
        ):

            if self.on_tarih:
                self.on_tarih(self)

            return True

        return super().on_touch_down(touch)


# =========================================================
# AÇILIŞ EKRANI (SPLASH)
# =========================================================

class NabizHalkasi(Widget):

    def __init__(
        self,
        **kwargs
    ):

        super().__init__(**kwargs)

        with self.canvas:

            self._renk = Color(1, 1, 1, 0)

            self._cember = Line(
                circle=(0, 0, 0),
                width=dp(2)
            )

        self._devam_olay = None

        self.bind(
            pos=self._guncelle,
            size=self._guncelle
        )

    def _guncelle(self, *args):

        self._cember.circle = (
            self.center_x,
            self.center_y,
            self.width / 2
        )

    def baslat(self, gecikme=0):

        Clock.schedule_once(
            lambda dt: self._dongu(),
            gecikme
        )

    def _dongu(self):

        self.size = (dp(24), dp(24))
        self._renk.a = .55

        Animation(
            size=(dp(230), dp(230)),
            duration=1.7,
            t="out_quad"
        ).start(self)

        Animation(
            a=0,
            duration=1.7,
            t="out_quad"
        ).start(self._renk)

        self._devam_olay = Clock.schedule_once(
            lambda dt: self._dongu(),
            1.7
        )

    def durdur(self):

        if self._devam_olay:
            self._devam_olay.cancel()

        Animation.cancel_all(self)
        Animation.cancel_all(self._renk)


# =========================================================
# MAKBUZ (PDF) OLUŞTURMA
# =========================================================

# PDF'te Türkçe karakterlerin doğru
# görünmesi için cihazda bulunan bir
# unicode yazı tipi aranır. Bulunamazsa
# temel yazı tipine geri dönülür ve
# Türkçe karakterler en yakın ASCII
# karşılığına çevrilir.
_TURKCE_FONT_ADAYLARI = (
    (
        "/system/fonts/Roboto-Regular.ttf",
        "/system/fonts/Roboto-Bold.ttf"
    ),
    (
        "/system/fonts/NotoSans-Regular.ttf",
        "/system/fonts/NotoSans-Bold.ttf"
    ),
    (
        "/system/fonts/DroidSans.ttf",
        "/system/fonts/DroidSans-Bold.ttf"
    ),
    (
        "/usr/share/fonts/truetype/dejavu/"
        "DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/"
        "DejaVuSans-Bold.ttf"
    ),
    (
        "/usr/share/fonts/truetype/liberation/"
        "LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/liberation/"
        "LiberationSans-Bold.ttf"
    ),
    (
        os.path.join(
            BASE_DIR, "font", "DejaVuSans.ttf"
        ),
        os.path.join(
            BASE_DIR, "font", "DejaVuSans-Bold.ttf"
        )
    ),
)

_TURKCE_CEVIRI = str.maketrans({
    "ş": "s", "Ş": "S",
    "ğ": "g", "Ğ": "G",
    "ı": "i", "İ": "I",
    "ö": "o", "Ö": "O",
    "ü": "u", "Ü": "U",
    "ç": "c", "Ç": "C",
})


def _makbuz_font_hazirla(pdf):

    for normal, kalin in _TURKCE_FONT_ADAYLARI:

        try:

            if os.path.exists(normal):

                pdf.add_font(
                    "Govde", "", normal
                )

                pdf.add_font(
                    "Govde",
                    "B",
                    kalin
                    if os.path.exists(kalin)
                    else normal
                )

                return "Govde", True

        except Exception:
            continue

    return "helvetica", False


def _mt(metin, unicode_destekli):

    metin = str(
        metin
        if metin is not None
        else ""
    )

    if unicode_destekli:
        return metin

    return metin.translate(
        _TURKCE_CEVIRI
    )


def makbuz_no_uret():

    ayar = ayarlari_oku()

    son_no = int(
        ayar.get(
            "son_makbuz_no",
            0
        )
    ) + 1

    ayar["son_makbuz_no"] = son_no

    ayarlari_kaydet(ayar)

    return f"MK-{son_no:06d}"


def makbuz_pdf_olustur(is_):

    if FPDF is None:
        raise RuntimeError(
            "PDF oluşturmak için 'fpdf2' "
            "kütüphanesi kurulu değil."
        )

    ayar = ayarlari_oku()

    firma_adi = ayar.get(
        "firma_adi", ""
    )

    firma_telefon = ayar.get(
        "telefon", ""
    )

    iscilik = para(
        is_.get("iscilik", 0)
    )

    malzeme_toplami = toplam_malzeme(
        is_
    )

    malzemeli = is_.get(
        "malzemeli", True
    )

    alinan = para(
        is_.get("gelir", 0)
    )

    toplam = (
        iscilik
        if malzemeli
        else iscilik + malzeme_toplami
    )

    kalan = alinacak_hesapla(
        malzemeli,
        iscilik,
        malzeme_toplami,
        alinan
    )

    if kalan <= 0.009:
        odeme_durumu = "TAMAMI ÖDENDİ"
        durum_renk = (30, 140, 60)
    elif alinan > 0:
        odeme_durumu = "KISMİ ÖDENDİ"
        durum_renk = (200, 140, 10)
    else:
        odeme_durumu = "ÖDENME BEKLİYOR"
        durum_renk = (190, 40, 40)

    makbuz_numarasi = makbuz_no_uret()

    tarih = datetime.now().strftime(
        "%d.%m.%Y %H:%M"
    )

    pdf = FPDF(
        orientation="P",
        unit="mm",
        format="A4"
    )

    pdf.set_auto_page_break(
        auto=True, margin=18
    )

    pdf.add_page()

    yazi_tipi, unicode_destekli = (
        _makbuz_font_hazirla(pdf)
    )

    def T(metin):
        return _mt(
            metin, unicode_destekli
        )

    sol = 15
    sag = 195

    # ---- Üst bilgi (logo + firma) ----
    logo_yolu = ayar.get(
        "logo_yolu", LOGO_DOSYASI
    )

    metin_x = sol

    if logo_yolu and os.path.exists(
        logo_yolu
    ):

        try:

            pdf.image(
                logo_yolu,
                x=sol,
                y=12,
                w=26
            )

            metin_x = sol + 32

        except Exception:
            metin_x = sol

    pdf.set_xy(metin_x, 14)
    pdf.set_font(yazi_tipi, "B", 18)
    pdf.set_text_color(25, 25, 30)
    pdf.cell(
        0, 8,
        T(firma_adi or "Firma / Kişi Adı"),
        ln=1
    )

    if firma_telefon:

        pdf.set_x(metin_x)
        pdf.set_font(yazi_tipi, "", 11)
        pdf.set_text_color(90, 90, 95)
        pdf.cell(
            0, 6,
            T("Tel: " + firma_telefon),
            ln=1
        )

    # ---- MAKBUZ başlığı + no/tarih ----
    pdf.set_xy(sol, 34)
    pdf.set_draw_color(220, 220, 224)
    pdf.line(sol, 33, sag, 33)

    pdf.set_font(yazi_tipi, "B", 22)
    pdf.set_text_color(20, 20, 24)
    pdf.set_xy(sol, 37)
    pdf.cell(0, 10, T("MAKBUZ"), ln=1)

    pdf.set_font(yazi_tipi, "", 11)
    pdf.set_text_color(90, 90, 95)
    pdf.set_xy(sol, 48)
    pdf.cell(
        0, 6,
        T(f"Makbuz No: {makbuz_numarasi}"),
        ln=1
    )
    pdf.set_x(sol)
    pdf.cell(
        0, 6, T(f"Tarih: {tarih}"), ln=1
    )

    # ---- Müşteri bilgileri ----
    y = 64
    pdf.set_fill_color(244, 245, 247)
    pdf.rect(sol, y, sag - sol, 26, "F")

    pdf.set_xy(sol + 4, y + 3)
    pdf.set_font(yazi_tipi, "B", 12)
    pdf.set_text_color(30, 30, 34)
    pdf.cell(
        0, 6, T("MÜŞTERİ BİLGİLERİ"), ln=1
    )

    pdf.set_x(sol + 4)
    pdf.set_font(yazi_tipi, "", 11)
    pdf.set_text_color(60, 60, 65)
    pdf.cell(
        0, 6,
        T(
            "Müşteri: "
            + (is_.get("musteri") or "-")
        ),
        ln=1
    )

    pdf.set_x(sol + 4)
    pdf.cell(
        0, 6,
        T(
            "Telefon: "
            + (is_.get("telefon") or "-")
        ),
        ln=1
    )

    # ---- İş açıklaması ----
    y = 96
    pdf.set_xy(sol, y)
    pdf.set_font(yazi_tipi, "B", 12)
    pdf.set_text_color(30, 30, 34)
    pdf.cell(0, 6, T("İŞ AÇIKLAMASI"), ln=1)

    pdf.set_x(sol)
    pdf.set_font(yazi_tipi, "", 11)
    pdf.set_text_color(60, 60, 65)

    aciklama_metni = (
        is_.get("is_adi", "")
        + (
            "\n" + is_.get("aciklama", "")
            if is_.get("aciklama")
            else ""
        )
    )

    pdf.multi_cell(
        sag - sol, 6, T(aciklama_metni)
    )

    # ---- Tutar tablosu ----
    y = max(pdf.get_y() + 8, 130)

    satirlar = [
        ("İşçilik Ücreti", iscilik)
    ]

    if not malzemeli:
        satirlar.append(
            ("Malzeme", malzeme_toplami)
        )

    pdf.set_xy(sol, y)
    pdf.set_draw_color(220, 220, 224)

    for etiket, tutar in satirlar:

        pdf.set_font(yazi_tipi, "", 12)
        pdf.set_text_color(60, 60, 65)
        pdf.set_x(sol)
        pdf.cell(
            (sag - sol) * 0.6, 8, T(etiket)
        )
        pdf.cell(
            (sag - sol) * 0.4,
            8,
            T(f"{tutar:,.2f} TL"),
            align="R",
            ln=1
        )

        pdf.set_x(sol)
        pdf.cell(
            sag - sol, 0, "",
            border="T", ln=1
        )

    pdf.set_font(yazi_tipi, "B", 13)
    pdf.set_text_color(20, 20, 24)
    pdf.set_x(sol)
    pdf.cell(
        (sag - sol) * 0.6, 10, T("TOPLAM")
    )
    pdf.cell(
        (sag - sol) * 0.4,
        10,
        T(f"{toplam:,.2f} TL"),
        align="R",
        ln=1
    )

    pdf.set_font(yazi_tipi, "", 12)
    pdf.set_text_color(60, 60, 65)
    pdf.set_x(sol)
    pdf.cell(
        (sag - sol) * 0.6, 8, T("Ödenen")
    )
    pdf.cell(
        (sag - sol) * 0.4,
        8,
        T(f"{alinan:,.2f} TL"),
        align="R",
        ln=1
    )

    pdf.set_x(sol)
    pdf.cell(
        (sag - sol) * 0.6, 8, T("Kalan")
    )
    pdf.cell(
        (sag - sol) * 0.4,
        8,
        T(f"{max(kalan, 0):,.2f} TL"),
        align="R",
        ln=1
    )

    # ---- Ödeme durumu rozeti ----
    y = pdf.get_y() + 6
    pdf.set_fill_color(*durum_renk)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font(yazi_tipi, "B", 13)
    pdf.set_xy(sol, y)
    pdf.cell(
        sag - sol, 11, T(odeme_durumu),
        align="C", fill=True, ln=1
    )

    # ---- Alt bilgi ----
    pdf.set_y(-25)
    pdf.set_font(yazi_tipi, "", 9)
    pdf.set_text_color(150, 150, 155)
    pdf.cell(
        0, 6,
        T(
            "Bu makbuz otomatik olarak "
            "oluşturulmuştur."
        ),
        align="C"
    )

    os.makedirs(
        MAKBUZ_KLASORU, exist_ok=True
    )

    dosya_adi = (
        makbuz_numarasi
        + "_"
        + datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )
        + ".pdf"
    )

    dosya_yolu = os.path.join(
        MAKBUZ_KLASORU, dosya_adi
    )

    pdf.output(dosya_yolu)

    return dosya_yolu


def makbuz_paylas(dosya_yolu):

    if _paylasim_servisi is None:
        return False

    try:

        _paylasim_servisi.share(
            title="Makbuzu Paylaş",
            filepath=dosya_yolu
        )

        return True

    except Exception as e:

        print(f"[paylaşım] hata: {e}")
        return False


class AcilisEkrani(Screen):

    def __init__(
        self,
        **kwargs
    ):

        super().__init__(**kwargs)

        self.kok = FloatLayout()

        with self.kok.canvas.before:

            Color(*ARKA)

            self._zemin = RoundedRectangle(
                pos=self.kok.pos,
                size=self.kok.size,
                radius=[0]
            )

        self.kok.bind(
            pos=self._zemin_guncelle,
            size=self._zemin_guncelle
        )

        merkez = {
            "center_x": .5,
            "center_y": .60
        }

        self.halka1 = NabizHalkasi(
            size_hint=(None, None),
            size=(0, 0),
            pos_hint=merkez
        )

        self.halka2 = NabizHalkasi(
            size_hint=(None, None),
            size=(0, 0),
            pos_hint=merkez
        )

        self.baslik_kutu = BoxLayout(
            orientation="horizontal",
            size_hint=(None, None),
            height=dp(46),
            pos_hint={
                "center_x": .5,
                "center_y": .43
            }
        )

        self.baslik_harfleri = []

        for harf_yazi in "İŞ TAKİP PRO":

            genislik = (
                dp(14)
                if harf_yazi == " "
                else dp(23)
            )

            harf = Label(
                text=harf_yazi,
                font_size=30,
                bold=True,
                color=BEYAZ,
                size_hint=(None, None),
                size=(genislik, dp(46)),
                opacity=0
            )

            self.baslik_harfleri.append(harf)

            self.baslik_kutu.add_widget(harf)

        self.baslik_kutu.bind(
            minimum_width=
            self.baslik_kutu.setter("width")
        )

        self.alt_yazi = Label(
            text="ŞANTİYE • İŞ • PARA • MALZEME",
            font_size=13,
            color=SOLUK,
            size_hint=(None, None),
            size=(dp(320), dp(24)),
            pos_hint={
                "center_x": .5,
                "center_y": .375
            },
            opacity=0
        )

        self.bar = ProgressBar(
            max=100,
            value=0,
            size_hint=(None, None),
            size=(dp(230), dp(8)),
            pos_hint={
                "center_x": .5,
                "center_y": .30
            },
            opacity=0
        )

        self.durum_yazi = Label(
            text="Yükleniyor",
            font_size=16,
            color=SOLUK,
            size_hint=(None, None),
            size=(dp(320), dp(28)),
            pos_hint={
                "center_x": .5,
                "center_y": .25
            },
            opacity=0
        )

        self.kok.add_widget(self.halka1)
        self.kok.add_widget(self.halka2)
        self.kok.add_widget(self.baslik_kutu)
        self.kok.add_widget(self.alt_yazi)
        self.kok.add_widget(self.bar)
        self.kok.add_widget(self.durum_yazi)

        self.add_widget(self.kok)

        self._nokta_sayaci = 0
        self._nokta_olay = None
        self._ses = None

    def _zemin_guncelle(self, *args):

        self._zemin.pos = self.kok.pos
        self._zemin.size = self.kok.size

    def on_enter(self):

        self._sesi_calmayi_dene()

        # Arkada yayılan radar
        # halkaları
        self.halka1.baslat(0)
        self.halka2.baslat(.85)

        # Başlık harfleri tek tek,
        # sırayla beliriyor
        for i, harf in enumerate(
            self.baslik_harfleri
        ):

            Clock.schedule_once(
                lambda dt, w=harf:
                Animation(
                    opacity=1,
                    duration=.35,
                    t="out_quad"
                ).start(w),
                .25 + i * .045
            )

        Animation(
            opacity=1,
            duration=.7,
            t="out_quad"
        ).start(self.alt_yazi)

        Animation(
            opacity=1,
            duration=.7,
            t="out_quad"
        ).start(self.bar)

        Animation(
            opacity=1,
            duration=.7,
            t="out_quad"
        ).start(self.durum_yazi)

        # İlerleme çubuğu doluşu
        Animation(
            value=100,
            duration=2.1,
            t="out_quad"
        ).start(self.bar)

        # "Yükleniyor..." noktalarının
        # akması
        self._nokta_olay = Clock.schedule_interval(
            self._noktalari_guncelle,
            .4
        )

        Clock.schedule_once(
            self._devam_et,
            2.4
        )

    def _noktalari_guncelle(self, dt):

        self._nokta_sayaci = (
            self._nokta_sayaci + 1
        ) % 4

        self.durum_yazi.text = (
            "Yükleniyor"
            + "." * self._nokta_sayaci
        )

    def _sesi_calmayi_dene(self):

        try:

            if os.path.exists(
                SES_DOSYASI
            ):

                self._ses = SoundLoader.load(
                    SES_DOSYASI
                )

                if self._ses:

                    self._ses.volume = 0.6
                    self._ses.play()

        except Exception:
            pass

    def _devam_et(self, dt):

        if self._nokta_olay:
            self._nokta_olay.cancel()

        self.halka1.durdur()
        self.halka2.durdur()

        if self.manager:

            self.manager.transition = (
                FadeTransition(
                    duration=.35
                )
            )

            self._kurulum_kontrol()

    def _kurulum_kontrol(self):

        ayar = ayarlari_oku()

        hedef = (
            "ana"
            if ayar.get(
                "kurulum_tamam", False
            )
            else "kurulum"
        )

        self.manager.current = hedef


# =========================================================
# İLK KURULUM
# =========================================================

class IlkKurulum(Screen):

    def __init__(
        self,
        **kwargs
    ):

        super().__init__(**kwargs)

        ana = BoxLayout(
            orientation="vertical",
            padding=dp(22),
            spacing=dp(14)
        )

        ana.add_widget(
            Label(
                text="👋 HOŞ GELDİNİZ",
                font_size=28,
                bold=True,
                color=BEYAZ,
                size_hint_y=None,
                height=dp(50)
            )
        )

        ana.add_widget(
            Label(
                text=(
                    "Başlamadan önce birkaç "
                    "bilgiye ihtiyacımız var. "
                    "Bu bilgiler makbuzlarda "
                    "otomatik kullanılacak."
                ),
                font_size=16,
                color=SOLUK,
                size_hint_y=None,
                height=dp(70)
            )
        )

        self.firma_adi = giris(
            "Firma Adı / Kişi Adı"
        )

        self.telefon = telefon_girisi(
            "Telefon Numarası"
        )

        ana.add_widget(
            etiketli_alan(
                "Firma Adı / Kişi Adı",
                self.firma_adi
            )
        )

        ana.add_widget(
            etiketli_alan(
                "Telefon Numarası",
                self.telefon
            )
        )

        self.uyari = Label(
            text="",
            font_size=14,
            color=KIRMIZI,
            size_hint_y=None,
            height=dp(24)
        )

        ana.add_widget(self.uyari)

        ana.add_widget(Widget())

        devam = buton(
            "DEVAM ET",
            renk=YESIL,
            yukseklik=64,
            font=20
        )

        devam.bind(
            on_press=self.devam_et
        )

        ana.add_widget(devam)

        self.add_widget(ana)

    def devam_et(self, instance):

        firma_adi = (
            self.firma_adi.text.strip()
        )

        telefon = self.telefon.text.strip()

        if not firma_adi:

            self.uyari.text = (
                "Lütfen Firma Adı / Kişi "
                "Adı girin."
            )

            return

        if not telefon:

            self.uyari.text = (
                "Lütfen Telefon Numarası "
                "girin."
            )

            return

        self.uyari.text = ""

        ayarlari_kaydet({
            "firma_adi": firma_adi,
            "telefon": telefon,
            "kurulum_tamam": True,
            "son_makbuz_no": 0
        })

        self.manager.current = "ana"


# =========================================================
# ANA SAYFA
# =========================================================

class AnaSayfa(Screen):

    def __init__(
        self,
        **kwargs
    ):

        super().__init__(**kwargs)

        ana = BoxLayout(
            orientation="vertical",
            padding=dp(16),
            spacing=dp(9)
        )

        ana.add_widget(
            Label(
                text="🔨 İŞ TAKİP PRO",
                font_size=32,
                bold=True,
                color=BEYAZ,
                size_hint_y=None,
                height=dp(62)
            )
        )

        ana.add_widget(
            Label(
                text="ŞANTİYE • İŞ • PARA • MALZEME",
                font_size=15,
                color=SOLUK,
                size_hint_y=None,
                height=dp(28)
            )
        )

        self.durum_kutu = KirmiziKutu(
            text="",
            font_size=19,
            bold=True,
            color=BEYAZ,
            halign="center",
            valign="middle",
            size_hint_y=None,
            height=dp(90)
        )

        self.durum_kutu.bind(
            size=lambda obj, val:
            setattr(
                obj,
                "text_size",
                val
            )
        )

        ana.add_widget(
            self.durum_kutu
        )

        menuler = [

            (
                "＋ YENİ İŞ",
                "yeni",
                62
            ),

            (
                "▣ GEÇMİŞ İŞLER",
                "gecmis",
                60
            ),

            (
                "₺ GELİR / GİDER",
                "gelir",
                60
            ),

            (
                "📦 MALZEME / ÖDEMELER",
                "malzeme",
                60
            ),

            (
                "📊 RAPORLAR / GRAFİKLER",
                "rapor",
                60
            ),

            (
                "⚙ YEDEKLEME / AYARLAR",
                "ayar",
                58
            )
        ]

        for (
            yazi,
            ekran,
            yukseklik
        ) in menuler:

            b = buton(
                yazi,
                yukseklik=yukseklik,
                font=19
            )

            b.bind(
                on_press=lambda _, s=ekran:
                setattr(
                    self.manager,
                    "current",
                    s
                )
            )

            ana.add_widget(b)

        cikis_btn = buton(
            "💾 KAYDET VE ÇIK",
            renk=KIRMIZI,
            yukseklik=60,
            font=19
        )

        cikis_btn.bind(
            on_press=self.kaydet_ve_cik
        )

        ana.add_widget(cikis_btn)

        ana.add_widget(
            Label(
                text="Veriler otomatik olarak saklanır.",
                font_size=14,
                color=SOLUK
            )
        )

        self.add_widget(ana)

    def kaydet_ve_cik(
        self,
        instance
    ):

        try:

            os.makedirs(
                YEDEK_KLASORU,
                exist_ok=True
            )

            zaman = datetime.now().strftime(
                "%Y%m%d_%H%M%S"
            )

            if os.path.exists(
                ISLER_DOSYASI
            ):

                shutil.copy2(
                    ISLER_DOSYASI,
                    os.path.join(
                        YEDEK_KLASORU,
                        f"isler_{zaman}.json"
                    )
                )

            if os.path.exists(
                YERLER_DOSYASI
            ):

                shutil.copy2(
                    YERLER_DOSYASI,
                    os.path.join(
                        YEDEK_KLASORU,
                        f"yerler_{zaman}.json"
                    )
                )

        except Exception:
            pass

        App.get_running_app().stop()

    def on_enter(self):

        isler = oku(
            ISLER_DOSYASI
        )

        toplam_alinacak = 0
        toplam_iscilik = 0
        toplam_diger_gider = 0
        toplam_malzeme_kar = 0

        for is_ in isler:

            iscilik = para(
                is_.get("iscilik", 0)
            )

            alinan = para(
                is_.get("gelir", 0)
            )

            malzeme_toplami = toplam_malzeme(
                is_
            )

            alinacak = alinacak_hesapla(
                is_.get("malzemeli", True),
                iscilik,
                malzeme_toplami,
                alinan
            )

            if alinacak > 0:
                toplam_alinacak += alinacak

            toplam_iscilik += iscilik

            toplam_diger_gider += para(
                is_.get("gider", 0)
            )

            if is_.get("malzemeli", True):

                toplam_malzeme_kar += (
                    malzeme_toplami
                )

        karim = (
            toplam_iscilik
            - toplam_diger_gider
            - toplam_malzeme_kar
        )

        if toplam_alinacak > 0:

            self.durum_kutu.renk_ayarla(
                KIRMIZI
            )

            self.durum_kutu.text = (
                "🔴 TOPLAM ALINACAK\n"
                f"{toplam_alinacak:.2f} TL"
            )

        else:

            self.durum_kutu.renk_ayarla(
                YESIL
            )

            self.durum_kutu.text = (
                "✅ KÂRIM (İşçilik - Diğer Gider)\n"
                f"{karim:.2f} TL"
            )


# =========================================================
# YENİ İŞ
# =========================================================

class YeniIs(Screen):

    def __init__(
        self,
        **kwargs
    ):

        super().__init__(**kwargs)

        self.malzemeler = []
        self.secili_yer = ""

        ana = BoxLayout(
            orientation="vertical",
            padding=dp(10),
            spacing=dp(7)
        )

        ana.add_widget(
            ust_baslik(
                self,
                "＋ YENİ İŞ",
                "ana"
            )
        )

        scroll = ScrollView()

        self.scroll = scroll

        form = BoxLayout(
            orientation="vertical",
            spacing=dp(9),
            size_hint_y=None
        )

        form.bind(
            minimum_height=
            form.setter("height")
        )

        self.is_adi = giris(
            "İş / proje adı"
        )

        self.musteri = giris(
            "Müşteri / iş sahibi"
        )

        self.telefon = giris(
            "Telefon (isteğe bağlı)"
        )

        form.add_widget(self.is_adi)
        form.add_widget(self.musteri)
        form.add_widget(self.telefon)

        yer_satir = BoxLayout(
            size_hint_y=None,
            height=dp(58),
            spacing=dp(7)
        )

        yer_btn = buton(
            "📍 İŞ YERİ SEÇ",
            yukseklik=58,
            font=17
        )

        yer_btn.bind(
            on_press=self.yer_sec
        )

        self.yer_label = Label(
            text="Yer: seçilmedi",
            font_size=17,
            color=SOLUK
        )

        yer_satir.add_widget(yer_btn)
        yer_satir.add_widget(
            self.yer_label
        )

        form.add_widget(yer_satir)

        durum_satir = BoxLayout(
            size_hint_y=None,
            height=dp(58),
            spacing=dp(7)
        )

        durum_satir.add_widget(
            Label(
                text="Durum:",
                font_size=18,
                color=BEYAZ
            )
        )

        self.durum = Spinner(
            text="Devam ediyor",
            values=(
                "Devam ediyor",
                "Bitti",
                "Beklemede"
            ),
            size_hint_y=None,
            height=dp(58),
            font_size=18,
            background_normal="",
            background_color=GIRIS,
            color=GIRIS_METIN
        )

        durum_satir.add_widget(
            self.durum
        )

        form.add_widget(
            durum_satir
        )

        self.aciklama = giris(
            "İş açıklaması / notlar",
            multiline=True,
            height=125
        )

        self.baslangic = TarihInput(
            hint_text="📅 Başlangıç tarihi - dokun ve seç",
            size_hint_y=None,
            height=dp(58),
            on_tarih=self.tarih_sec
        )

        self.bitis = TarihInput(
            hint_text="📅 Bitiş tarihi - dokun ve seç",
            size_hint_y=None,
            height=dp(58),
            on_tarih=self.tarih_sec
        )

        self.gelir = giris(
            "Alınan (TL)",
            input_filter="float"
        )

        self.iscilik = giris(
            "İşçilik (TL)",
            input_filter="float"
        )

        form.add_widget(self.aciklama)
        form.add_widget(self.baslangic)
        form.add_widget(self.bitis)

        self.foto_secici = FotografSecici()
        form.add_widget(self.foto_secici)

        self.malzemeli = True

        malzeme_secim_satir = BoxLayout(
            size_hint_y=None,
            height=dp(58),
            spacing=dp(8)
        )

        self.malzemeli_btn = buton(
            "📦 MALZEMELİ İŞ",
            renk=YESIL,
            yukseklik=56,
            font=16
        )

        self.malzemesiz_btn = buton(
            "🚫 MALZEMESİZ İŞ",
            yukseklik=56,
            font=16
        )

        self.malzemeli_btn.bind(
            on_press=lambda *_:
            self.malzeme_secim(True)
        )

        self.malzemesiz_btn.bind(
            on_press=lambda *_:
            self.malzeme_secim(False)
        )

        malzeme_secim_satir.add_widget(
            self.malzemeli_btn
        )

        malzeme_secim_satir.add_widget(
            self.malzemesiz_btn
        )

        form.add_widget(
            malzeme_secim_satir
        )

        form.add_widget(
            etiketli_alan(
                "Alınan",
                self.gelir
            )
        )

        form.add_widget(
            etiketli_alan(
                "İşçilik",
                self.iscilik
            )
        )

        form.add_widget(
            Label(
                text="💸 DİĞER GİDERLER",
                font_size=22,
                bold=True,
                color=BEYAZ,
                size_hint_y=None,
                height=dp(42)
            )
        )

        self.gider_kutusu = BoxLayout(
            orientation="vertical",
            spacing=dp(7),
            size_hint_y=None
        )

        self.gider_kutusu.bind(
            minimum_height=
            self.gider_kutusu.setter("height")
        )

        form.add_widget(
            self.gider_kutusu
        )

        self.gider_satirlari = []

        self.gider_satiri_ekle()

        form.add_widget(
            Label(
                text="📦 MALZEMELER",
                font_size=22,
                bold=True,
                color=BEYAZ,
                size_hint_y=None,
                height=dp(42)
            )
        )

        malzeme_satir = BoxLayout(
            size_hint_y=None,
            height=dp(58),
            spacing=dp(5)
        )

        self.malzeme_adi = giris(
            "Malzeme"
        )

        self.malzeme_adet = giris(
            "Miktar",
            input_filter="int"
        )

        self.malzeme_adet.size_hint_x = .20

        self.malzeme_birim = Spinner(
            text="Adet",
            values=(
                "Adet",
                "LT",
                "M",
                "KG",
                "Kutu",
                "Çuval"
            ),
            size_hint_x=.23,
            size_hint_y=None,
            height=dp(58),
            font_size=16,
            background_normal="",
            background_color=GIRIS,
            color=GIRIS_METIN
        )

        self.malzeme_fiyat = giris(
            "Fiyat",
            input_filter="float"
        )

        self.malzeme_fiyat.size_hint_x = .27

        ekle = buton(
            "+",
            yukseklik=58,
            font=27
        )

        ekle.size_hint_x = .16

        ekle.bind(
            on_press=self.malzeme_ekle
        )

        malzeme_satir.add_widget(
            self.malzeme_adi
        )

        malzeme_satir.add_widget(
            self.malzeme_adet
        )

        malzeme_satir.add_widget(
            self.malzeme_birim
        )

        malzeme_satir.add_widget(
            self.malzeme_fiyat
        )

        malzeme_satir.add_widget(ekle)

        form.add_widget(
            malzeme_satir
        )

        self.malzeme_listesi = Label(
            text="Henüz malzeme yok.",
            font_size=17,
            color=SOLUK,
            size_hint_y=None,
            height=dp(130)
        )

        form.add_widget(
            self.malzeme_listesi
        )

        self.alinacak_kutu = KirmiziKutu(
            text="ALINACAK TUTAR: 0.00 TL",
            font_size=20,
            bold=True,
            color=BEYAZ,
            halign="center",
            valign="middle",
            size_hint_y=None,
            height=dp(64)
        )

        self.alinacak_kutu.bind(
            size=lambda obj, val:
            setattr(
                obj,
                "text_size",
                val
            )
        )

        form.add_widget(
            self.alinacak_kutu
        )

        kaydet_btn = buton(
            "💾 İŞİ KAYDET",
            renk=YESIL,
            yukseklik=66,
            font=20
        )

        kaydet_btn.bind(
            on_press=self.kaydet
        )

        form.add_widget(
            kaydet_btn
        )

        scroll.add_widget(form)

        ana.add_widget(scroll)

        self.add_widget(ana)

        for widget in (
            self.is_adi,
            self.musteri,
            self.telefon,
            self.aciklama,
            self.gelir,
            self.iscilik,
            self.malzeme_adi,
            self.malzeme_adet,
            self.malzeme_fiyat
        ):

            klavye_uyumu(
                scroll,
                widget
            )

        self.gelir.bind(
            text=self._alinacak_guncelle
        )

        self.iscilik.bind(
            text=self._alinacak_guncelle
        )

        self._alinacak_guncelle()

    def _alinacak_guncelle(self, *args):

        iscilik = para(
            self.iscilik.text
        )

        malzeme_toplami = sum(
            para(m.get("fiyat", 0))
            for m in self.malzemeler
        )

        alinan = para(
            self.gelir.text
        )

        alinacak = alinacak_hesapla(
            self.malzemeli,
            iscilik,
            malzeme_toplami,
            alinan
        )

        self.alinacak_kutu.text = (
            "ALINACAK TUTAR: "
            f"{alinacak:.2f} TL"
        )

    def tarih_sec(
        self,
        widget
    ):

        TakvimPopup(widget).open()

    def yer_sec(
        self,
        instance
    ):

        varsayilan = [
            "Mavikent",
            "Karaöz",
            "Kumluca",
            "Hasyurt",
            "Finike"
        ]

        yerler = oku(
            YERLER_DOSYASI,
            varsayilan
        )

        if not yerler:

            yerler = varsayilan

            kaydet(
                YERLER_DOSYASI,
                yerler
            )

        kutu = BoxLayout(
            orientation="vertical",
            padding=dp(8),
            spacing=dp(7)
        )

        popup = Popup(
            title="İş Yeri Seç",
            content=kutu,
            size_hint=(.90, .84)
        )

        for yer in yerler:

            b = buton(
                "📍 " + yer,
                yukseklik=52,
                font=17
            )

            b.bind(
                on_press=lambda x, y=yer:
                self.yer_secildi(
                    y,
                    popup
                )
            )

            kutu.add_widget(b)

        yeni = buton(
            "＋ YENİ YER EKLE",
            yukseklik=54,
            font=17
        )

        yeni.bind(
            on_press=lambda x:
            self.yeni_yer(popup)
        )

        kutu.add_widget(yeni)

        popup.open()

    def yer_secildi(
        self,
        yer,
        popup
    ):

        self.secili_yer = yer

        self.yer_label.text = (
            "Yer: " + yer
        )

        popup.dismiss()

    def yeni_yer(
        self,
        ana_popup
    ):

        kutu = BoxLayout(
            orientation="vertical",
            padding=dp(10),
            spacing=dp(9)
        )

        isim = giris(
            "Yeni yer adı"
        )

        ekle = buton(
            "EKLE",
            yukseklik=54,
            font=18
        )

        kutu.add_widget(isim)
        kutu.add_widget(ekle)

        popup = Popup(
            title="Yeni İş Yeri",
            content=kutu,
            size_hint=(.86, .40)
        )

        def ekle_yer(instance):

            yer = isim.text.strip()

            if not yer:
                return

            yerler = oku(
                YERLER_DOSYASI,
                [
                    "Mavikent",
                    "Karaöz",
                    "Kumluca",
                    "Hasyurt",
                    "Finike"
                ]
            )

            if yer not in yerler:

                yerler.append(yer)

                kaydet(
                    YERLER_DOSYASI,
                    yerler
                )

            popup.dismiss()
            ana_popup.dismiss()

            self.secili_yer = yer

            self.yer_label.text = (
                "Yer: " + yer
            )

        ekle.bind(
            on_press=ekle_yer
        )

        popup.open()

    GIDER_KATEGORILERI = (
        "Yakıt",
        "Gıda",
        "Malzeme Özel",
        "Yardımcı Eleman"
    )

    def gider_satiri_ekle(self):

        satir = BoxLayout(
            size_hint_y=None,
            height=dp(58),
            spacing=dp(7)
        )

        kategori = Spinner(
            text="Yakıt",
            values=self.GIDER_KATEGORILERI,
            size_hint_x=.42,
            size_hint_y=None,
            height=dp(58),
            font_size=16,
            background_normal="",
            background_color=GIRIS,
            color=GIRIS_METIN
        )

        tutar = giris(
            "Tutar (TL)",
            input_filter="float"
        )

        satir.add_widget(kategori)
        satir.add_widget(tutar)

        self.gider_kutusu.add_widget(satir)

        kayit = {
            "satir": satir,
            "kategori": kategori,
            "tutar": tutar
        }

        self.gider_satirlari.append(kayit)

        klavye_uyumu(
            self.scroll,
            tutar
        )

        tutar.bind(
            text=lambda instance, deger, kayit=kayit:
            self._gider_yazildi(kayit, deger)
        )

    def _gider_yazildi(
        self,
        kayit,
        deger
    ):

        if (
            deger.strip()
            and kayit is self.gider_satirlari[-1]
        ):
            self.gider_satiri_ekle()

    def malzeme_secim(self, malzemeli):

        self.malzemeli = malzemeli

        if malzemeli:

            self.malzemeli_btn.renk_degistir(
                YESIL
            )

            self.malzemesiz_btn.renk_degistir(
                None
            )

        else:

            self.malzemeli_btn.renk_degistir(
                None
            )

            self.malzemesiz_btn.renk_degistir(
                KIRMIZI
            )

    def malzeme_ekle(
        self,
        instance
    ):

        ad = (
            self.malzeme_adi.text
            .strip()
        )

        if not ad:
            return

        try:
            adet = int(
                self.malzeme_adet.text or 1
            )
        except Exception:
            adet = 1

        try:
            birim = float(
                self.malzeme_fiyat.text or 0
            )
        except Exception:
            birim = 0

        birim_turu = (
            self.malzeme_birim.text
            or "Adet"
        )

        self.malzemeler.append({

            "ad": ad,

            "adet": adet,

            "birim": birim_turu,

            "birim_fiyat": birim,

            "fiyat": adet * birim,

            "odendi": False
        })

        self.malzeme_adi.text = ""
        self.malzeme_adet.text = ""
        self.malzeme_fiyat.text = ""

        self.malzeme_birim.text = "Adet"

        self.malzemeleri_goster()

    def malzemeleri_goster(self):

        if not self.malzemeler:

            self.malzeme_listesi.text = (
                "Henüz malzeme yok."
            )

            self._alinacak_guncelle()

            return

        toplam = 0
        metin = ""

        for i, m in enumerate(
            self.malzemeler,
            1
        ):

            fiyat = para(
                m.get("fiyat", 0)
            )

            toplam += fiyat

            birim = m.get(
                "birim",
                "Adet"
            )

            metin += (
                f"{i}. {m.get('ad', '')} "
                f"{m.get('adet', 1)} "
                f"{birim} → "
                f"{fiyat:.2f} TL\n"
            )

        metin += (
            f"\nTOPLAM: "
            f"{toplam:.2f} TL"
        )

        self.malzeme_listesi.text = metin

        self._alinacak_guncelle()

    def kaydet(
        self,
        instance
    ):

        try:
            gelir = float(
                self.gelir.text or 0
            )
        except Exception:
            gelir = 0

        try:
            iscilik = float(
                self.iscilik.text or 0
            )
        except Exception:
            iscilik = 0

        diger_giderler = []
        gider = 0

        for kayit in self.gider_satirlari:

            tutar = para(
                kayit["tutar"].text
            )

            if tutar > 0:

                gider += tutar

                diger_giderler.append({
                    "kategori":
                        kayit["kategori"].text,
                    "tutar":
                        tutar
                })

        veri = {

            "is_adi":
                self.is_adi.text.strip()
                or "İsimsiz İş",

            "yer":
                self.secili_yer,

            "musteri":
                self.musteri.text.strip(),

            "telefon":
                self.telefon.text.strip(),

            "aciklama":
                self.aciklama.text.strip(),

            "durum":
                self.durum.text,

            "baslangic":
                self.baslangic.text.strip(),

            "bitis":
                self.bitis.text.strip(),

            "gelir":
                gelir,

            "iscilik":
                iscilik,

            "gider":
                gider,

            "diger_giderler":
                diger_giderler,

            "malzemeli":
                self.malzemeli,

            "malzemeler":
                self.malzemeler,

            "fotograflar":
                self.foto_secici.dosyalar,

            "tarih":
                kayit_tarihi(
                    self.baslangic.text
                )
        }

        isler = oku(
            ISLER_DOSYASI
        )

        isler.append(veri)

        kaydet(
            ISLER_DOSYASI,
            isler
        )

        self.temizle()

        self.manager.current = "ana"

    def temizle(self):

        kutular = [
            self.is_adi,
            self.musteri,
            self.telefon,
            self.aciklama,
            self.baslangic,
            self.bitis,
            self.gelir,
            self.iscilik,
            self.malzeme_adi,
            self.malzeme_adet,
            self.malzeme_fiyat
        ]

        for kutu in kutular:
            kutu.text = ""

        self.secili_yer = ""

        self.yer_label.text = (
            "Yer: seçilmedi"
        )

        self.durum.text = (
            "Devam ediyor"
        )

        self.gider_kutusu.clear_widgets()

        self.gider_satirlari = []

        self.gider_satiri_ekle()

        self.malzemeler = []

        self.malzeme_birim.text = "Adet"

        self.malzemeleri_goster()

        self.foto_secici.yukle([])


# =========================================================
# GEÇMİŞ İŞLER
# =========================================================

class Gecmis(Screen):

    def __init__(
        self,
        **kwargs
    ):

        super().__init__(**kwargs)

        ana = BoxLayout(
            orientation="vertical",
            padding=dp(10),
            spacing=dp(8)
        )

        ana.add_widget(
            ust_baslik(
                self,
                "📚 GEÇMİŞ İŞLER",
                "ana"
            )
        )

        filtre = BoxLayout(
            size_hint_y=None,
            height=dp(58),
            spacing=dp(6)
        )

        self.arama = giris(
            "🔎 İş / müşteri / yer ara"
        )

        self.filtre_durum = Spinner(
            text="Tümü",
            values=(
                "Tümü",
                "Devam ediyor",
                "Bitti",
                "Beklemede"
            ),
            font_size=17,
            background_normal="",
            background_color=GIRIS,
            color=GIRIS_METIN
        )

        filtre.add_widget(
            self.arama
        )

        filtre.add_widget(
            self.filtre_durum
        )

        self.arama.bind(
            text=lambda *_:
            self.yenile()
        )

        self.filtre_durum.bind(
            text=lambda *_:
            self.yenile()
        )

        ana.add_widget(filtre)

        scroll = ScrollView()

        self.liste = BoxLayout(
            orientation="vertical",
            spacing=dp(11),
            size_hint_y=None
        )

        self.liste.bind(
            minimum_height=
            self.liste.setter("height")
        )

        scroll.add_widget(
            self.liste
        )

        ana.add_widget(scroll)

        self.add_widget(ana)

        klavye_uyumu(
            scroll,
            self.arama
        )

    def on_enter(self):

        self.yenile()

    def yenile(self):

        self.liste.clear_widgets()

        isler = oku(
            ISLER_DOSYASI
        )

        arama = (
            self.arama.text
            .lower()
            .strip()
        )

        for index in range(
            len(isler) - 1,
            -1,
            -1
        ):

            is_ = isler[index]

            durum = is_durumu(
                is_
            )

            arama_metni = (
                f"{is_.get('is_adi', '')} "
                f"{is_.get('musteri', '')} "
                f"{is_.get('yer', '')}"
            ).lower()

            if (
                arama
                and
                arama not in arama_metni
            ):
                continue

            if (
                self.filtre_durum.text
                != "Tümü"
                and
                durum
                != self.filtre_durum.text
            ):
                continue

            is_adi = is_.get(
                "is_adi",
                "İsimsiz İş"
            )

            musteri = is_.get(
                "musteri",
                "Belirtilmemiş"
            )

            yer = is_.get(
                "yer",
                "Yer belirtilmemiş"
            )

            kart = BoxLayout(
                orientation="vertical",
                size_hint_y=None,
                height=dp(155),
                spacing=dp(7)
            )

            if durum == "Bitti":
                is_renk = KIRMIZI
            elif durum == "Beklemede":
                is_renk = YESIL
            else:
                is_renk = BEYAZ

            detay_btn = buton(
                f"🔨  {is_adi}\n\n"
                f"👤  {musteri}\n"
                f"📍  {yer}",
                renk=is_renk,
                yukseklik=110,
                font=20
            )

            detay_btn.halign = "left"
            detay_btn.valign = "middle"

            detay_btn.bind(
                width=lambda obj, val:
                setattr(
                    obj,
                    "text_size",
                    (
                        val - dp(28),
                        None
                    )
                )
            )

            detay_btn.bind(
                on_press=lambda _, i=index:
                self.detay_ac(i)
            )

            kart.add_widget(
                detay_btn
            )

            sil = buton(
                "🗑 BU İŞİ SİL",
                yukseklik=42,
                font=16
            )

            sil.bind(
                on_press=lambda _, i=index:
                self.sil(i)
            )

            kart.add_widget(sil)

            self.liste.add_widget(
                kart
            )

        if not self.liste.children:

            self.liste.add_widget(
                Label(
                    text="Kayıt bulunamadı.",
                    font_size=20,
                    color=SOLUK,
                    size_hint_y=None,
                    height=dp(70)
                )
            )

    def detay_ac(
        self,
        index
    ):

        detay = self.manager.get_screen(
            "detay"
        )

        detay.is_index = index

        detay.yukle()

        self.manager.current = "detay"

    def sil(
        self,
        index
    ):

        isler = oku(
            ISLER_DOSYASI
        )

        if 0 <= index < len(isler):

            del isler[index]

            kaydet(
                ISLER_DOSYASI,
                isler
            )

            self.yenile()


# =========================================================
# İŞ DETAY
# =========================================================

class IsDetay(Screen):

    def __init__(
        self,
        **kwargs
    ):

        super().__init__(**kwargs)

        self.is_index = None
        self.malzemeler = []

        ana = BoxLayout(
            orientation="vertical",
            padding=dp(10),
            spacing=dp(7)
        )

        ana.add_widget(
            ust_baslik(
                self,
                "🔨 İŞ DETAYI",
                "gecmis"
            )
        )

        makbuz_btn = buton(
            "🧾 GEÇMİŞTEN MAKBUZ ÇIKAR",
            renk=SARI,
            yukseklik=58,
            font=17
        )

        makbuz_btn.color = SARI_METIN

        makbuz_btn.bind(
            on_press=self.makbuz_olustur
        )

        ana.add_widget(makbuz_btn)

        scroll = ScrollView()

        self.scroll = scroll

        form = BoxLayout(
            orientation="vertical",
            spacing=dp(9),
            size_hint_y=None
        )

        form.bind(
            minimum_height=
            form.setter("height")
        )

        self.is_adi = giris(
            "İş / proje adı"
        )

        self.musteri = giris(
            "Müşteri / iş sahibi"
        )

        self.telefon = giris(
            "Telefon"
        )

        self.yer = giris(
            "Yer"
        )

        self.aciklama = giris(
            "Açıklama / notlar",
            multiline=True,
            height=125
        )

        self.baslangic = giris(
            "Başlangıç tarihi"
        )

        self.bitis = giris(
            "Bitiş tarihi"
        )

        self.gelir = giris(
            "Gelir",
            input_filter="float"
        )

        self.iscilik = giris(
            "İşçilik",
            input_filter="float"
        )

        self.durum = Spinner(
            text="Devam ediyor",
            values=(
                "Devam ediyor",
                "Bitti",
                "Beklemede"
            ),
            size_hint_y=None,
            height=dp(58),
            font_size=18,
            background_normal="",
            background_color=GIRIS,
            color=GIRIS_METIN
        )

        form.add_widget(self.is_adi)
        form.add_widget(self.musteri)
        form.add_widget(self.telefon)
        form.add_widget(self.yer)
        form.add_widget(self.durum)
        form.add_widget(self.aciklama)
        form.add_widget(self.baslangic)
        form.add_widget(self.bitis)

        self.foto_secici = FotografSecici()
        form.add_widget(self.foto_secici)

        form.add_widget(
            etiketli_alan(
                "Alınan",
                self.gelir
            )
        )

        form.add_widget(
            etiketli_alan(
                "İşçilik",
                self.iscilik
            )
        )

        form.add_widget(
            Label(
                text="💸 DİĞER GİDERLER",
                font_size=22,
                bold=True,
                color=BEYAZ,
                size_hint_y=None,
                height=dp(42)
            )
        )

        self.gider_kutusu = BoxLayout(
            orientation="vertical",
            spacing=dp(7),
            size_hint_y=None
        )

        self.gider_kutusu.bind(
            minimum_height=
            self.gider_kutusu.setter("height")
        )

        form.add_widget(
            self.gider_kutusu
        )

        self.gider_satirlari = []

        self.malzemeli = True

        malzeme_secim_satir = BoxLayout(
            size_hint_y=None,
            height=dp(58),
            spacing=dp(8)
        )

        self.malzemeli_btn = buton(
            "📦 MALZEMELİ İŞ",
            renk=YESIL,
            yukseklik=56,
            font=16
        )

        self.malzemesiz_btn = buton(
            "🚫 MALZEMESİZ İŞ",
            yukseklik=56,
            font=16
        )

        self.malzemeli_btn.bind(
            on_press=lambda *_:
            self.malzeme_secim(True)
        )

        self.malzemesiz_btn.bind(
            on_press=lambda *_:
            self.malzeme_secim(False)
        )

        malzeme_secim_satir.add_widget(
            self.malzemeli_btn
        )

        malzeme_secim_satir.add_widget(
            self.malzemesiz_btn
        )

        form.add_widget(
            malzeme_secim_satir
        )

        form.add_widget(
            Label(
                text="📦 MALZEMELER",
                font_size=22,
                bold=True,
                color=BEYAZ,
                size_hint_y=None,
                height=dp(42)
            )
        )

        self.malzeme_listesi = BoxLayout(
            orientation="vertical",
            spacing=dp(7),
            size_hint_y=None
        )

        self.malzeme_listesi.bind(
            minimum_height=
            self.malzeme_listesi.setter(
                "height"
            )
        )

        form.add_widget(
            self.malzeme_listesi
        )

        yeni_malzeme = buton(
            "＋ MALZEME EKLE",
            yukseklik=58,
            font=18
        )

        yeni_malzeme.bind(
            on_press=self.yeni_malzeme_ekle
        )

        form.add_widget(
            yeni_malzeme
        )

        self.alinacak_kutu = KirmiziKutu(
            text="ALINACAK TUTAR: 0.00 TL",
            font_size=20,
            bold=True,
            color=BEYAZ,
            halign="center",
            valign="middle",
            size_hint_y=None,
            height=dp(64)
        )

        self.alinacak_kutu.bind(
            size=lambda obj, val:
            setattr(
                obj,
                "text_size",
                val
            )
        )

        form.add_widget(
            self.alinacak_kutu
        )

        kaydet_btn = buton(
            "💾 DEĞİŞİKLİKLERİ KAYDET",
            renk=YESIL,
            yukseklik=66,
            font=20
        )

        kaydet_btn.bind(
            on_press=self.kaydet
        )

        form.add_widget(
            kaydet_btn
        )

        scroll.add_widget(form)

        ana.add_widget(scroll)

        self.add_widget(ana)

        self.gelir.bind(
            text=self._alinacak_guncelle
        )

        self.iscilik.bind(
            text=self._alinacak_guncelle
        )

        self._alinacak_guncelle()

    def _alinacak_guncelle(self, *args):

        iscilik = para(
            self.iscilik.text
        )

        malzeme_toplami = sum(
            para(m.get("fiyat", 0))
            for m in self.malzemeler
        )

        alinan = para(
            self.gelir.text
        )

        alinacak = alinacak_hesapla(
            self.malzemeli,
            iscilik,
            malzeme_toplami,
            alinan
        )

        self.alinacak_kutu.text = (
            "ALINACAK TUTAR: "
            f"{alinacak:.2f} TL"
        )

    GIDER_KATEGORILERI = (
        "Yakıt",
        "Gıda",
        "Malzeme Özel",
        "Yardımcı Eleman"
    )

    def gider_satiri_ekle(
        self,
        kategori_sec="Yakıt",
        tutar_deger=""
    ):

        satir = BoxLayout(
            size_hint_y=None,
            height=dp(58),
            spacing=dp(7)
        )

        kategori = Spinner(
            text=kategori_sec,
            values=self.GIDER_KATEGORILERI,
            size_hint_x=.42,
            size_hint_y=None,
            height=dp(58),
            font_size=16,
            background_normal="",
            background_color=GIRIS,
            color=GIRIS_METIN
        )

        tutar = giris(
            "Tutar (TL)",
            input_filter="float"
        )

        tutar.text = tutar_deger

        satir.add_widget(kategori)
        satir.add_widget(tutar)

        self.gider_kutusu.add_widget(satir)

        kayit = {
            "satir": satir,
            "kategori": kategori,
            "tutar": tutar
        }

        self.gider_satirlari.append(kayit)

        klavye_uyumu(
            self.scroll,
            tutar
        )

        tutar.bind(
            text=lambda instance, deger, kayit=kayit:
            self._gider_yazildi(kayit, deger)
        )

    def _gider_yazildi(
        self,
        kayit,
        deger
    ):

        if (
            deger.strip()
            and kayit is self.gider_satirlari[-1]
        ):
            self.gider_satiri_ekle()

    def malzeme_secim(self, malzemeli):

        self.malzemeli = malzemeli

        if malzemeli:

            self.malzemeli_btn.renk_degistir(
                YESIL
            )

            self.malzemesiz_btn.renk_degistir(
                None
            )

        else:

            self.malzemeli_btn.renk_degistir(
                None
            )

            self.malzemesiz_btn.renk_degistir(
                KIRMIZI
            )

        # Malzemeli/malzemesiz değiştirilse
        # bile malzeme listesi ekrandan
        # kaybolmasın, her zaman güncel
        # listeyle tekrar çizilsin.
        if hasattr(
            self,
            "malzeme_listesi"
        ):
            self.malzemeleri_goster()

    def on_enter(self):

        if self.is_index is not None:
            self.yukle()

    def yukle(self):

        isler = oku(
            ISLER_DOSYASI
        )

        if not (
            0 <= self.is_index < len(isler)
        ):
            return

        is_ = isler[self.is_index]

        self.is_adi.text = is_.get(
            "is_adi",
            ""
        )

        self.musteri.text = is_.get(
            "musteri",
            ""
        )

        self.telefon.text = is_.get(
            "telefon",
            ""
        )

        self.yer.text = is_.get(
            "yer",
            ""
        )

        self.durum.text = is_.get(
            "durum",
            "Devam ediyor"
        )

        self.aciklama.text = is_.get(
            "aciklama",
            ""
        )

        self.baslangic.text = is_.get(
            "baslangic",
            ""
        )

        self.bitis.text = is_.get(
            "bitis",
            ""
        )

        self.gelir.text = str(
            is_.get(
                "gelir",
                0
            )
        )

        self.iscilik.text = str(
            is_.get(
                "iscilik",
                0
            )
        )

        self.gider_kutusu.clear_widgets()
        self.gider_satirlari = []

        diger_giderler = is_.get(
            "diger_giderler",
            []
        )

        if diger_giderler:

            for dg in diger_giderler:

                self.gider_satiri_ekle(
                    kategori_sec=dg.get(
                        "kategori",
                        "Yakıt"
                    ),
                    tutar_deger=str(
                        para(dg.get("tutar", 0))
                    )
                )

        elif para(is_.get("gider", 0)) > 0:

            self.gider_satiri_ekle(
                kategori_sec="Yakıt",
                tutar_deger=str(
                    para(is_.get("gider", 0))
                )
            )

        self.gider_satiri_ekle()

        self.malzemeler = list(
            is_.get(
                "malzemeler",
                []
            )
        )

        self.malzeme_secim(
            is_.get("malzemeli", True)
        )

        self.malzemeleri_goster()

        self.foto_secici.yukle(
            is_.get("fotograflar", [])
        )

    def malzemeleri_goster(self):

        self.malzeme_listesi.clear_widgets()

        if not self.malzemeler:

            self.malzeme_listesi.add_widget(
                Label(
                    text="Malzeme yok.",
                    font_size=17,
                    color=SOLUK,
                    size_hint_y=None,
                    height=dp(45)
                )
            )

            self._alinacak_guncelle()

            return

        for i, m in enumerate(
            self.malzemeler
        ):

            odendi = m.get(
                "odendi",
                False
            )

            durum = (
                "✅ ÖDENDİ"
                if odendi
                else "⏳ ÖDENECEK"
            )

            birim = m.get(
                "birim",
                "Adet"
            )

            b = buton(
                f"{m.get('ad', '')}  "
                f"{m.get('adet', 1)} "
                f"{birim} • "
                f"{para(m.get('fiyat', 0)):.2f} TL\n"
                f"{durum}",
                yukseklik=65,
                font=16
            )

            b.bind(
                on_press=lambda _, x=i:
                self.odeme_degistir(x)
            )

            self.malzeme_listesi.add_widget(
                b
            )

            sil = buton(
                "🗑 MALZEMEYİ SİL",
                yukseklik=38,
                font=14
            )

            sil.bind(
                on_press=lambda _, x=i:
                self.malzeme_sil(x)
            )

            self.malzeme_listesi.add_widget(
                sil
            )

        self._alinacak_guncelle()

    def odeme_degistir(
        self,
        index
    ):

        if 0 <= index < len(
            self.malzemeler
        ):

            self.malzemeler[index][
                "odendi"
            ] = not self.malzemeler[index].get(
                "odendi",
                False
            )

            self.malzemeleri_goster()

    def malzeme_sil(
        self,
        index
    ):

        if not (
            0 <= index < len(
                self.malzemeler
            )
        ):
            return

        malzeme = self.malzemeler[index]

        kutu = BoxLayout(
            orientation="vertical",
            padding=dp(14),
            spacing=dp(12)
        )

        kutu.add_widget(
            Label(
                text=(
                    "🗑 "
                    f"{malzeme.get('ad', '')} "
                    "silinsin mi?\n"
                    "Emin misiniz?"
                ),
                font_size=18,
                color=BEYAZ,
                halign="center"
            )
        )

        butonlar = BoxLayout(
            size_hint_y=None,
            height=dp(56),
            spacing=dp(8)
        )

        vazgec = buton(
            "VAZGEÇ",
            yukseklik=54,
            font=17
        )

        evet = buton(
            "EVET, SİL",
            renk=KIRMIZI,
            yukseklik=54,
            font=17
        )

        butonlar.add_widget(vazgec)
        butonlar.add_widget(evet)

        kutu.add_widget(butonlar)

        popup = Popup(
            title="Malzemeyi Sil",
            content=kutu,
            size_hint=(.86, .40)
        )

        vazgec.bind(
            on_press=lambda *_:
            popup.dismiss()
        )

        def sil_onayla(instance):

            del self.malzemeler[index]

            popup.dismiss()

            self.malzemeleri_goster()

        evet.bind(
            on_press=sil_onayla
        )

        popup.open()

    def yeni_malzeme_ekle(
        self,
        instance
    ):

        kutu = BoxLayout(
            orientation="vertical",
            padding=dp(10),
            spacing=dp(8)
        )

        ad = giris(
            "Malzeme adı"
        )

        adet = giris(
            "Miktar",
            input_filter="int"
        )

        birim = Spinner(
            text="Adet",
            values=(
                "Adet",
                "LT",
                "M",
                "KG",
                "Kutu",
                "Çuval"
            ),
            size_hint_y=None,
            height=dp(58),
            font_size=17,
            background_normal="",
            background_color=GIRIS,
            color=GIRIS_METIN
        )

        fiyat = giris(
            "Fiyat",
            input_filter="float"
        )

        ekle = buton(
            "EKLE",
            yukseklik=56,
            font=18
        )

        kutu.add_widget(ad)
        kutu.add_widget(adet)
        kutu.add_widget(birim)
        kutu.add_widget(fiyat)
        kutu.add_widget(ekle)

        popup = Popup(
            title="Malzeme Ekle",
            content=kutu,
            size_hint=(.90, .72)
        )

        def ekle_malzeme(instance):

            ad_ = ad.text.strip()

            if not ad_:
                return

            try:
                adet_ = int(
                    adet.text or 1
                )
            except Exception:
                adet_ = 1

            try:
                fiyat_ = float(
                    fiyat.text or 0
                )
            except Exception:
                fiyat_ = 0

            self.malzemeler.append({

                "ad": ad_,

                "adet": adet_,

                "birim": birim.text,

                "birim_fiyat": fiyat_,

                "fiyat":
                    adet_ * fiyat_,

                "odendi": False
            })

            popup.dismiss()

            self.malzemeleri_goster()

        ekle.bind(
            on_press=ekle_malzeme
        )

        popup.open()

    def kaydet(
        self,
        instance
    ):

        isler = oku(
            ISLER_DOSYASI
        )

        if not (
            0 <= self.is_index < len(isler)
        ):
            return

        is_ = isler[
            self.is_index
        ]

        is_["is_adi"] = (
            self.is_adi.text.strip()
        )

        is_["musteri"] = (
            self.musteri.text.strip()
        )

        is_["telefon"] = (
            self.telefon.text.strip()
        )

        is_["yer"] = (
            self.yer.text.strip()
        )

        is_["durum"] = (
            self.durum.text
        )

        is_["aciklama"] = (
            self.aciklama.text.strip()
        )

        is_["baslangic"] = (
            self.baslangic.text.strip()
        )

        is_["bitis"] = (
            self.bitis.text.strip()
        )

        is_["gelir"] = para(
            self.gelir.text
        )

        is_["iscilik"] = para(
            self.iscilik.text
        )

        diger_giderler = []
        gider = 0

        for kayit in self.gider_satirlari:

            tutar = para(
                kayit["tutar"].text
            )

            if tutar > 0:

                gider += tutar

                diger_giderler.append({
                    "kategori":
                        kayit["kategori"].text,
                    "tutar":
                        tutar
                })

        is_["gider"] = gider

        is_["diger_giderler"] = (
            diger_giderler
        )

        is_["malzemeli"] = (
            self.malzemeli
        )

        is_["malzemeler"] = (
            self.malzemeler
        )

        is_["fotograflar"] = (
            self.foto_secici.dosyalar
        )

        # Rapor/ay filtresi başlangıç
        # tarihine göre güncellensin.
        if self.baslangic.text.strip():

            is_["tarih"] = kayit_tarihi(
                self.baslangic.text
            )

        elif "tarih" not in is_:

            is_["tarih"] = (
                datetime.now().strftime(
                    "%d.%m.%Y %H:%M"
                )
            )

        kaydet(
            ISLER_DOSYASI,
            isler
        )

        self.manager.current = "gecmis"

    def makbuz_olustur(
        self,
        instance
    ):

        isler = oku(
            ISLER_DOSYASI
        )

        if not (
            0 <= self.is_index < len(isler)
        ):
            return

        is_ = isler[self.is_index]

        try:

            dosya_yolu = makbuz_pdf_olustur(
                is_
            )

        except Exception as e:

            self._makbuz_hata_goster(
                str(e)
            )

            return

        self._makbuz_hazir_popup(
            dosya_yolu
        )

    def _makbuz_hata_goster(self, mesaj):

        kutu = BoxLayout(
            orientation="vertical",
            padding=dp(14),
            spacing=dp(10)
        )

        kutu.add_widget(
            Label(
                text=(
                    "Makbuz oluşturulamadı:\n"
                    + mesaj
                ),
                font_size=15,
                color=BUTON_METIN
            )
        )

        kapat = buton(
            "KAPAT",
            yukseklik=52,
            font=16
        )

        kutu.add_widget(kapat)

        popup = Popup(
            title="Hata",
            content=kutu,
            size_hint=(.88, .45)
        )

        kapat.bind(
            on_press=lambda *_:
            popup.dismiss()
        )

        popup.open()

    def _makbuz_hazir_popup(
        self,
        dosya_yolu
    ):

        kutu = BoxLayout(
            orientation="vertical",
            padding=dp(14),
            spacing=dp(12)
        )

        kutu.add_widget(
            Label(
                text=(
                    "✅ Makbuz oluşturuldu.\n"
                    + os.path.basename(
                        dosya_yolu
                    )
                ),
                font_size=16,
                color=BUTON_METIN,
                halign="center"
            )
        )

        paylas = buton(
            "📤 PAYLAŞ",
            renk=YESIL,
            yukseklik=58,
            font=18
        )

        kapat = buton(
            "KAPAT",
            yukseklik=52,
            font=16
        )

        kutu.add_widget(paylas)
        kutu.add_widget(kapat)

        popup = Popup(
            title="Makbuz",
            content=kutu,
            size_hint=(.88, .50)
        )

        def paylas_yap(*_):

            basarili = makbuz_paylas(
                dosya_yolu
            )

            if not basarili:

                kutu.add_widget(
                    Label(
                        text=(
                            "Paylaşım açılamadı. "
                            "Dosya kaydedildi:\n"
                            + dosya_yolu
                        ),
                        font_size=13,
                        color=SOLUK
                    )
                )

        paylas.bind(
            on_press=paylas_yap
        )

        kapat.bind(
            on_press=lambda *_:
            popup.dismiss()
        )

        popup.open()


# =========================================================
# GELİR / GİDER
# =========================================================

class GelirGider(Screen):

    def __init__(
        self,
        **kwargs
    ):

        super().__init__(**kwargs)

        simdi = datetime.now()

        self.secili_yil = simdi.year
        self.secili_ay = simdi.month

        ana = BoxLayout(
            orientation="vertical",
            padding=dp(10),
            spacing=dp(8)
        )

        ana.add_widget(
            ust_baslik(
                self,
                "₺ GELİR / GİDER",
                "ana"
            )
        )

        ay_satir = BoxLayout(
            size_hint_y=None,
            height=dp(58),
            spacing=dp(7)
        )

        onceki = buton(
            "‹",
            yukseklik=56,
            font=30
        )

        onceki.size_hint_x = .18

        onceki.bind(
            on_press=self.onceki_ay
        )

        self.ay_baslik = Label(
            text="",
            font_size=20,
            bold=True,
            color=BEYAZ
        )

        sonraki = buton(
            "›",
            yukseklik=56,
            font=30
        )

        sonraki.size_hint_x = .18

        sonraki.bind(
            on_press=self.sonraki_ay
        )

        ay_satir.add_widget(onceki)
        ay_satir.add_widget(self.ay_baslik)
        ay_satir.add_widget(sonraki)

        ana.add_widget(ay_satir)

        self.ozet = Label(
            text="",
            font_size=21,
            bold=True,
            color=BEYAZ,
            size_hint_y=None,
            height=dp(260)
        )

        ana.add_widget(
            self.ozet
        )

        self.durum_kutu = KirmiziKutu(
            text="",
            font_size=20,
            bold=True,
            color=BEYAZ,
            halign="center",
            valign="middle",
            size_hint_y=None,
            height=dp(90)
        )

        self.durum_kutu.bind(
            size=lambda obj, val:
            setattr(
                obj,
                "text_size",
                val
            )
        )

        ana.add_widget(
            self.durum_kutu
        )

        self.add_widget(ana)

    def onceki_ay(
        self,
        instance
    ):

        self.secili_ay -= 1

        if self.secili_ay == 0:
            self.secili_ay = 12
            self.secili_yil -= 1

        self.yenile()

    def sonraki_ay(
        self,
        instance
    ):

        self.secili_ay += 1

        if self.secili_ay == 13:
            self.secili_ay = 1
            self.secili_yil += 1

        self.yenile()

    def on_enter(self):

        self.yenile()

    def yenile(self):

        h = hesaplar(
            self.secili_yil,
            self.secili_ay
        )

        self.ay_baslik.text = (
            f"{TakvimPopup.AY_ISIMLERI[self.secili_ay - 1]} "
            f"{self.secili_yil}"
        )

        self.ozet.text = (

            f"💰 Alınan: "
            f"{h['ay_gelir']:.2f} TL\n"

            f"💸 Diğer gider: "
            f"{h['ay_gider']:.2f} TL\n"

            f"📦 Malzeme: "
            f"{h['ay_malzeme']:.2f} TL\n"

            f"👷 İŞÇİLİK: "
            f"{h['ay_iscilik']:.2f} TL"
        )

        ay_alinacak = h["ay_alinacak"]

        if ay_alinacak > 0:

            self.durum_kutu.renk_ayarla(
                KIRMIZI
            )

            self.durum_kutu.text = (
                f"👷 İşçilik: {h['ay_iscilik']:.2f} TL\n"
                f"📦 Malzeme: {h['ay_malzeme']:.2f} TL"
            )

        else:

            kar = h["ay_net"]

            self.durum_kutu.renk_ayarla(
                YESIL
            )

            self.durum_kutu.text = (
                "✅ KÂR: "
                f"{kar:.2f} TL"
            )


# =========================================================
# MALZEME / ÖDEMELER
# =========================================================

class Malzemeler(Screen):

    def __init__(
        self,
        **kwargs
    ):

        super().__init__(**kwargs)

        ana = BoxLayout(
            orientation="vertical",
            padding=dp(10),
            spacing=dp(8)
        )

        ana.add_widget(
            ust_baslik(
                self,
                "📦 MALZEME / ÖDEMELER",
                "ana"
            )
        )

        self.ozet = Label(
            text="",
            font_size=21,
            bold=True,
            color=BEYAZ,
            size_hint_y=None,
            height=dp(100)
        )

        ana.add_widget(
            self.ozet
        )

        scroll = ScrollView()

        self.liste = BoxLayout(
            orientation="vertical",
            spacing=dp(8),
            size_hint_y=None
        )

        self.liste.bind(
            minimum_height=
            self.liste.setter("height")
        )

        scroll.add_widget(
            self.liste
        )

        ana.add_widget(scroll)

        self.add_widget(ana)

    def on_enter(self):

        self.yenile()

    def yenile(self):

        self.liste.clear_widgets()

        isler = oku(
            ISLER_DOSYASI
        )

        toplam = 0
        odenecek = 0

        for is_ in isler:

            for m in is_.get(
                "malzemeler",
                []
            ):

                fiyat = para(
                    m.get(
                        "fiyat",
                        0
                    )
                )

                toplam += fiyat

                if not m.get(
                    "odendi",
                    False
                ):

                    odenecek += fiyat

        self.ozet.text = (
            f"📦 TOPLAM: "
            f"{toplam:.2f} TL\n"
            f"⏳ ÖDENECEK: "
            f"{odenecek:.2f} TL"
        )

        for i, is_ in enumerate(
            isler
        ):

            malzemeler = is_.get(
                "malzemeler",
                []
            )

            if not malzemeler:
                continue

            bekleyen_malzemeler = [

                m for m in malzemeler

                if not m.get(
                    "odendi",
                    False
                )
            ]

            if not bekleyen_malzemeler:
                continue

            self.liste.add_widget(
                Label(
                    text=(
                        f"🔨 "
                        f"{is_.get('is_adi', '')}"
                    ),
                    bold=True,
                    font_size=20,
                    color=BEYAZ,
                    size_hint_y=None,
                    height=dp(42)
                )
            )

            for j, m in enumerate(
                malzemeler
            ):

                # ÖDENENLER ARTIK
                # BU EKRANDA GÖSTERİLMEYECEK

                if m.get(
                    "odendi",
                    False
                ):
                    continue

                durum = (
                    "⏳ ÖDENECEK"
                )

                birim = m.get(
                    "birim",
                    "Adet"
                )

                b = buton(

                    f"{m.get('ad', '')} "
                    f"{m.get('adet', 1)} "
                    f"{birim} • "

                    f"{para(m.get('fiyat', 0)):.2f} TL • "

                    f"{durum}",

                    yukseklik=58,
                    font=16
                )

                b.bind(
                    on_press=lambda _, a=i, bidx=j:
                    self.odeme_degistir(
                        a,
                        bidx
                    )
                )

                self.liste.add_widget(b)

        if not self.liste.children:

            self.liste.add_widget(
                Label(
                    text=(
                        "Bekleyen malzeme "
                        "ödemesi yok."
                    ),
                    font_size=19,
                    color=SOLUK,
                    size_hint_y=None,
                    height=dp(70)
                )
            )

    def odeme_degistir(
        self,
        is_index,
        malzeme_index
    ):

        isler = oku(
            ISLER_DOSYASI
        )

        try:

            malzeme = (
                isler[is_index]
                ["malzemeler"]
                [malzeme_index]
            )

            malzeme["odendi"] = not (
                malzeme.get(
                    "odendi",
                    False
                )
            )

            kaydet(
                ISLER_DOSYASI,
                isler
            )

            self.yenile()

        except Exception:
            pass


# =========================================================
# RAPORLAR
# =========================================================

class Raporlar(Screen):

    def __init__(
        self,
        **kwargs
    ):

        super().__init__(**kwargs)

        simdi = datetime.now()

        self.secili_yil = simdi.year
        self.secili_ay = simdi.month
        self.hepsi_mi = True

        ana = BoxLayout(
            orientation="vertical",
            padding=dp(10),
            spacing=dp(8)
        )

        ana.add_widget(
            ust_baslik(
                self,
                "📊 RAPORLAR / GRAFİKLER",
                "ana"
            )
        )

        filtre_satir = BoxLayout(
            size_hint_y=None,
            height=dp(58),
            spacing=dp(7)
        )

        onceki = buton(
            "‹",
            yukseklik=56,
            font=30
        )

        onceki.size_hint_x = .16

        onceki.bind(
            on_press=self.onceki_ay
        )

        self.filtre_baslik = Label(
            text="TÜMÜ",
            font_size=19,
            bold=True,
            color=BEYAZ
        )

        sonraki = buton(
            "›",
            yukseklik=56,
            font=30
        )

        sonraki.size_hint_x = .16

        sonraki.bind(
            on_press=self.sonraki_ay
        )

        self.hepsi_buton = buton(
            "TÜMÜ",
            yukseklik=56,
            font=15
        )

        self.hepsi_buton.size_hint_x = .30

        self.hepsi_buton.bind(
            on_press=self.hepsini_goster
        )

        filtre_satir.add_widget(onceki)
        filtre_satir.add_widget(self.filtre_baslik)
        filtre_satir.add_widget(sonraki)
        filtre_satir.add_widget(self.hepsi_buton)

        ana.add_widget(filtre_satir)

        scroll = ScrollView()

        self.icerik = BoxLayout(
            orientation="vertical",
            spacing=dp(10),
            size_hint_y=None
        )

        self.icerik.bind(
            minimum_height=
            self.icerik.setter("height")
        )

        scroll.add_widget(
            self.icerik
        )

        ana.add_widget(scroll)

        self.add_widget(ana)

    def onceki_ay(
        self,
        instance
    ):

        self.hepsi_mi = False

        self.secili_ay -= 1

        if self.secili_ay == 0:
            self.secili_ay = 12
            self.secili_yil -= 1

        self.yenile()

    def sonraki_ay(
        self,
        instance
    ):

        self.hepsi_mi = False

        self.secili_ay += 1

        if self.secili_ay == 13:
            self.secili_ay = 1
            self.secili_yil += 1

        self.yenile()

    def hepsini_goster(
        self,
        instance
    ):

        self.hepsi_mi = True

        self.yenile()

    def on_enter(self):

        self.yenile()

    def yenile(self):

        self.icerik.clear_widgets()

        if self.hepsi_mi:

            self.filtre_baslik.text = "TÜMÜ"

        else:

            self.filtre_baslik.text = (
                f"{TakvimPopup.AY_ISIMLERI[self.secili_ay - 1]} "
                f"{self.secili_yil}"
            )

        tum_isler = oku(
            ISLER_DOSYASI
        )

        if self.hepsi_mi:

            isler_indeksli = list(
                enumerate(tum_isler)
            )

        else:

            isler_indeksli = [
                (i, is_)
                for i, is_ in enumerate(tum_isler)
                if bu_ay_mi(
                    is_.get("tarih", ""),
                    self.secili_yil,
                    self.secili_ay
                )
            ]

        isler = [
            is_
            for _, is_ in isler_indeksli
        ]

        devam = 0
        bitti = 0
        beklemede = 0

        for is_ in isler:

            durum = is_durumu(
                is_
            )

            if durum == "Bitti":
                bitti += 1

            elif durum == "Beklemede":
                beklemede += 1

            else:
                devam += 1

        self.icerik.add_widget(
            Label(
                text=(
                    "📋 İŞ DURUMLARI\n\n"
                    f"🟢 Devam eden: "
                    f"{devam}\n\n"
                    f"✅ Biten: "
                    f"{bitti}\n\n"
                    f"⏳ Beklemede: "
                    f"{beklemede}"
                ),
                font_size=20,
                color=BEYAZ,
                size_hint_y=None,
                height=dp(230)
            )
        )

        self.icerik.add_widget(
            Label(
                text="📑 İŞ BAZLI DÖKÜM",
                font_size=22,
                bold=True,
                color=BEYAZ,
                size_hint_y=None,
                height=dp(42)
            )
        )

        if not isler:

            self.icerik.add_widget(
                Label(
                    text="Henüz iş kaydı yok.",
                    font_size=18,
                    color=SOLUK,
                    size_hint_y=None,
                    height=dp(50)
                )
            )

        for sira in range(
            len(isler_indeksli) - 1,
            -1,
            -1
        ):

            index, is_ = isler_indeksli[sira]

            is_adi = is_.get(
                "is_adi",
                "İsimsiz İş"
            )

            tarih = is_.get(
                "tarih",
                "Tarih yok"
            )

            iscilik = para(
                is_.get("iscilik", 0)
            )

            alinan = para(
                is_.get("gelir", 0)
            )

            malzeme_toplami = toplam_malzeme(
                is_
            )

            alinacak = alinacak_hesapla(
                is_.get("malzemeli", True),
                iscilik,
                malzeme_toplami,
                alinan
            )

            satirlar = [
                f"[b]🔨 {is_adi}[/b]",
                f"📅 {tarih}",
                f"👷 İşçilik: {iscilik:.2f} TL",
                f"💰 Alınan: {alinan:.2f} TL",
                f"📦 Malzeme: {malzeme_toplami:.2f} TL"
            ]

            diger_giderler = is_.get(
                "diger_giderler",
                []
            )

            if diger_giderler:

                for dg in diger_giderler:

                    kategori = dg.get(
                        "kategori",
                        "Diğer"
                    )

                    ikon = GIDER_IKONLARI.get(
                        kategori,
                        "💸"
                    )

                    satirlar.append(
                        f"{ikon} {kategori}: "
                        f"{para(dg.get('tutar', 0)):.2f} TL"
                    )

            elif para(is_.get("gider", 0)) > 0:

                satirlar.append(
                    f"💸 Diğer gider: "
                    f"{para(is_.get('gider', 0)):.2f} TL"
                )

            if alinacak > 0:

                satirlar.append(
                    "[color=D93333][b]🔴 Alınacak: "
                    f"{alinacak:.2f} TL[/b][/color]"
                )

            else:

                kar_is = (
                    alinan
                    - para(is_.get("gider", 0))
                )

                if is_.get("malzemeli", True):

                    kar_is -= malzeme_toplami

                satirlar.append(
                    "[color=33A64D][b]✅ Kâr: "
                    f"{kar_is:.2f} TL[/b][/color]"
                )

            metin = "\n".join(satirlar)

            kart_btn = buton(
                metin,
                yukseklik=40,
                font=17
            )

            kart_btn.markup = True
            kart_btn.halign = "left"
            kart_btn.valign = "top"
            kart_btn.padding = (
                dp(16),
                dp(16)
            )

            kart_btn.bind(
                width=lambda obj, val:
                setattr(
                    obj,
                    "text_size",
                    (val - dp(32), None)
                )
            )

            kart_btn.bind(
                texture_size=lambda obj, val:
                setattr(
                    obj,
                    "height",
                    val[1] + dp(32)
                )
            )

            kart_btn.bind(
                on_press=lambda _, i=index:
                self.detay_ac(i)
            )

            self.icerik.add_widget(
                kart_btn
            )

    def detay_ac(
        self,
        index
    ):

        detay = self.manager.get_screen(
            "detay"
        )

        detay.is_index = index

        detay.yukle()

        self.manager.current = "detay"


# =========================================================
# AYARLAR / YEDEKLEME
# =========================================================

class Ayarlar(Screen):

    def __init__(
        self,
        **kwargs
    ):

        super().__init__(**kwargs)

        ana = BoxLayout(
            orientation="vertical",
            padding=dp(10),
            spacing=dp(9)
        )

        ana.add_widget(
            ust_baslik(
                self,
                "⚙ YEDEKLEME / AYARLAR",
                "ana"
            )
        )

        ana.add_widget(
            Label(
                text=(
                    "Veriler telefon veya "
                    "bilgisayarda JSON olarak "
                    "saklanır."
                ),
                font_size=18,
                color=BEYAZ,
                size_hint_y=None,
                height=dp(90)
            )
        )

        yedek = buton(
            "💾 YEDEK OLUŞTUR",
            yukseklik=62,
            font=19
        )

        yedek.bind(
            on_press=self.yedek_olustur
        )

        ana.add_widget(yedek)

        yerler = buton(
            "📍 YERLERİ YÖNET",
            yukseklik=62,
            font=19
        )

        yerler.bind(
            on_press=self.yerleri_goster
        )

        ana.add_widget(yerler)

        test_bildirim = buton(
            "🔔 TEST BİLDİRİMİ GÖNDER",
            yukseklik=62,
            font=17
        )

        test_bildirim.bind(
            on_press=self.test_bildirimi_gonder
        )

        ana.add_widget(test_bildirim)

        self.durum = Label(
            text="",
            font_size=16,
            color=SOLUK
        )

        ana.add_widget(
            self.durum
        )

        self.add_widget(ana)

    def yedek_olustur(
        self,
        instance
    ):

        try:

            os.makedirs(
                YEDEK_KLASORU,
                exist_ok=True
            )

            zaman = datetime.now().strftime(
                "%Y%m%d_%H%M%S"
            )

            kaynak = ISLER_DOSYASI

            if os.path.exists(kaynak):

                hedef = os.path.join(
                    YEDEK_KLASORU,
                    f"isler_{zaman}.json"
                )

                shutil.copy2(
                    kaynak,
                    hedef
                )

            kaynak_yer = YERLER_DOSYASI

            if os.path.exists(
                kaynak_yer
            ):

                hedef_yer = os.path.join(
                    YEDEK_KLASORU,
                    f"yerler_{zaman}.json"
                )

                shutil.copy2(
                    kaynak_yer,
                    hedef_yer
                )

            self.durum.text = (
                "✅ Yedek oluşturuldu."
            )

        except Exception as e:

            self.durum.text = (
                f"Yedekleme hatası: {e}"
            )

    def test_bildirimi_gonder(
        self,
        instance
    ):

        try:
            self.durum.text = (
                bildirimler.test_bildirimi_gonder()
            )
        except Exception as e:
            self.durum.text = (
                f"Bildirim hatası: {e}"
            )

    def yerleri_goster(
        self,
        instance
    ):

        yerler = oku(
            YERLER_DOSYASI,
            [
                "Mavikent",
                "Karaöz",
                "Kumluca",
                "Hasyurt",
                "Finike"
            ]
        )

        kutu = BoxLayout(
            orientation="vertical",
            padding=dp(10),
            spacing=dp(7)
        )

        scroll = ScrollView()

        liste = BoxLayout(
            orientation="vertical",
            spacing=dp(7),
            size_hint_y=None
        )

        liste.bind(
            minimum_height=
            liste.setter("height")
        )

        for i, yer in enumerate(
            yerler
        ):

            satir = BoxLayout(
                size_hint_y=None,
                height=dp(55),
                spacing=dp(5)
            )

            satir.add_widget(
                Label(
                    text="📍 " + yer,
                    font_size=17,
                    color=BUTON_METIN
                )
            )

            sil = buton(
                "SİL",
                yukseklik=50,
                font=14
            )

            sil.size_hint_x = .25

            sil.bind(
                on_press=lambda _, x=i:
                self.yer_sil(
                    x,
                    popup
                )
            )

            satir.add_widget(sil)

            liste.add_widget(satir)

        scroll.add_widget(liste)

        kutu.add_widget(scroll)

        kapat = buton(
            "KAPAT",
            yukseklik=54,
            font=17
        )

        kutu.add_widget(kapat)

        popup = Popup(
            title="Kayıtlı Yerler",
            content=kutu,
            size_hint=(.90, .80)
        )

        kapat.bind(
            on_press=lambda *_:
            popup.dismiss()
        )

        popup.open()

    def yer_sil(
        self,
        index,
        popup
    ):

        yerler = oku(
            YERLER_DOSYASI
        )

        if 0 <= index < len(
            yerler
        ):

            del yerler[index]

            kaydet(
                YERLER_DOSYASI,
                yerler
            )

            popup.dismiss()

            self.yerleri_goster(
                None
            )


# =========================================================
# UYGULAMA
# =========================================================

class IsTakipApp(App):

    def build(self):

        Window.clearcolor = ARKA

        self._android_izinlerini_iste()

        try:

            Window.softinput_mode = (
                "below_target"
            )

        except Exception:
            pass

        ekranlar = ScreenManager()

        ekranlar.add_widget(
            AcilisEkrani(
                name="acilis"
            )
        )

        ekranlar.add_widget(
            IlkKurulum(
                name="kurulum"
            )
        )

        ekranlar.add_widget(
            AnaSayfa(
                name="ana"
            )
        )

        ekranlar.add_widget(
            YeniIs(
                name="yeni"
            )
        )

        ekranlar.add_widget(
            Gecmis(
                name="gecmis"
            )
        )

        ekranlar.add_widget(
            IsDetay(
                name="detay"
            )
        )

        ekranlar.add_widget(
            GelirGider(
                name="gelir"
            )
        )

        ekranlar.add_widget(
            Malzemeler(
                name="malzeme"
            )
        )

        ekranlar.add_widget(
            Raporlar(
                name="rapor"
            )
        )

        ekranlar.add_widget(
            Ayarlar(
                name="ayar"
            )
        )

        ekranlar.current = "acilis"

        try:
            bildirimler.tum_hatirlatmalari_planla()
        except Exception as e:
            print(f"[bildirim] planlama başlatılamadı: {e}")

        return ekranlar

    def _android_izinlerini_iste(self):

        # Android 6+ (API 23+) 'tehlikeli' izinleri sadece
        # buildozer.spec -> android.permissions listesine
        # yazmak YETMEZ; kullanıcıya sistem izin penceresinin
        # açılıp onaylanması gerekir. Bu çağrı olmadan
        # bildirimler ve kamera sessizce çalışmaz.

        try:

            from kivy.utils import platform

            if platform != "android":
                return

            from android.permissions import (
                request_permissions,
                Permission
            )

            istenecekler = [
                Permission.CAMERA,
                Permission.WRITE_EXTERNAL_STORAGE,
                Permission.READ_EXTERNAL_STORAGE
            ]

            # POST_NOTIFICATIONS sadece Android 13+ (API 33+)
            # içinde var; eski sürümlerde bu isim bulunmaz.
            if hasattr(
                Permission, "POST_NOTIFICATIONS"
            ):

                istenecekler.append(
                    Permission.POST_NOTIFICATIONS
                )

            # READ_MEDIA_IMAGES Android 13+'ta galeri
            # erişimi için READ_EXTERNAL_STORAGE'ın yerini
            # aldı.
            if hasattr(
                Permission, "READ_MEDIA_IMAGES"
            ):

                istenecekler.append(
                    Permission.READ_MEDIA_IMAGES
                )

            request_permissions(istenecekler)

        except Exception as e:

            print(
                f"[izin] istenemedi: {e}"
            )


# =========================================================
# BAŞLAT
# =========================================================

if __name__ == "__main__":

    IsTakipApp().run()
