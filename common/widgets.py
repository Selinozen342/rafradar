"""Sayfalar arasında ortak parçalar: üst bilgi, KPI kartları, tablolar, renk skalaları."""
import numpy as np
import pandas as pd
import streamlit as st
from common import analytics as an
from common import ui

GUN_ADI = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]
AY_AD = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
AY_KISA = ui.AYLAR
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def fk():
    """Önbellek anahtarı: yüklenen dosya + kategori/ürün/şehir filtreleri."""
    ss = st.session_state
    return (ss.get("dosya_adi", ""), len(ss["df"]), ss.get("f_kat"), ss.get("f_urun"), ss.get("f_sehir"))


@st.cache_data(show_spinner=False)
def ozet_c(_m, anahtar, a, b):
    return an.ozet(_m, a, b)


def pct(x):
    return ("▲ %" if x >= 0 else "▼ %") + ui.sayi(abs(x * 100), 1)


def rel(a, b):
    return a / b - 1 if b else 0


def chg(x, vurgu):
    sinif = "mute" if not vurgu else ("neg" if x < 0 else "pos")
    return f"<span class='chg {sinif}'>{pct(x)}</span>"


def chg_p(d, vurgu):
    return f"<span class='chg {'neu' if vurgu else 'mute'}'>{'▲ ' if d >= 0 else '▼ '}{ui.sayi(abs(d * 100), 1)} puan</span>"


def kart(baslik, nom, nom_c, gun_et, gun_v, gun_c, renk=None):
    st_ = f" style='border-top-color:{renk}'" if renk else ""
    return (f"<div class='kpi'{st_}><div class='kl'>{baslik}</div><div class='kv'>{nom}</div>{nom_c}"
            f"<div class='rule'></div><div class='kl'>{gun_et}</div><div class='kv2'>{gun_v}</div>{gun_c}</div>")


def ust_bilgi(S, C, a, b, ca, cb, karsilastirma=True):
    """Seçili ve karşılaştırma dönemi hapları."""
    et = ui.tarih_etiketi
    ayni = S["gun"] == C["gun"]
    s = f"<span class='pill g'>Seçili: {et(a, b)} · {S['gun']} gün</span>"
    if karsilastirma:
        s += (f"<span style='font-size:12px;color:#5b6475'>karşılaştırma</span> <span class='pill'>{et(ca, cb)} · {C['gun']} gün</span>"
              f"<span class='pill y'>{'Aralıklar eşit uzunlukta: vurgulu fark nominal değerlere göre' if ayni else 'Aralık uzunlukları farklı: toplamları değil günlük ortalamayı kıyasla'}</span>")
    return s


def kgrid(kartlar):
    st.markdown("<div class='kgrid'>" + "".join(kartlar) + "</div>", unsafe_allow_html=True)


def not_kutusu(metin):
    st.markdown(f"<div style='background:#f0ebe2;color:#5b6475;border-radius:10px;padding:8px 12px;font-size:12px'>{metin}</div>",
                unsafe_allow_html=True)


def tablo(basliklar, satirlar, sag=(), stil=None):
    h = "".join(f"<th class='{'r' if i in sag else ''}'>{b}</th>" for i, b in enumerate(basliklar))
    r = "".join("<tr" + (f" style='{stil[k]}'" if stil and stil[k] else "") + ">" +
                "".join(f"<td class='{'r' if i in sag else ''}'>{c}</td>" for i, c in enumerate(s)) + "</tr>"
                for k, s in enumerate(satirlar))
    return f"<table class='t'><thead><tr>{h}</tr></thead><tbody>{r}</tbody></table>"


def mix(a, b, t):
    pa = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    pb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "rgb(" + ",".join(str(round(x + (y - x) * t)) for x, y in zip(pa, pb)) + ")"


def isi_rengi(v, mx):
    t = 0 if mx <= 0 else min(1, v / mx)
    return f"background:{mix('#eee9df', '#1b5e4b', t ** 0.8)};color:{'#fff' if t > 0.55 else '#1f2a44'}"


def sapma_rengi(v):
    """100 = ortalama. Üstü turuncu, altı mavi."""
    if v >= 100:
        bg = mix("#ece8e0", "#e2733f", min(1, (v - 100) / 60))
    else:
        bg = mix("#ece8e0", "#5f8bd6", min(1, (100 - v) / 50))
    return f"background:{bg};color:{'#fff' if (v >= 145 or v <= 55) else '#1f2a44'}"


def sapma_tablo(satir_ad, sutun_ad, m):
    """Endeks ısı tablosu (satır x sütun, 100 = ortalama)."""
    h = "<table class='t'><thead><tr><th></th>" + "".join(f"<th style='text-align:center'>{c}</th>" for c in sutun_ad) + "</tr></thead><tbody>"
    for i, ad in enumerate(satir_ad):
        h += f"<tr><td style='text-align:left;font-size:13px'>{ad}</td>" + "".join(
            f"<td style='text-align:center;{sapma_rengi(v)}'>{ui.sayi(v, 0)}</td>" for v in m[i]) + "</tr>"
    h += "</tbody></table>"
    h += ("<div style='display:flex;align-items:center;gap:8px;font-size:11px;color:#5b6475;margin-top:6px'>az "
          "<span style='display:inline-block;width:160px;height:8px;border-radius:4px;background:linear-gradient(90deg,#5f8bd6,#ece8e0,#e2733f)'></span>"
          " çok · 100 = ortalama</div>")
    return h


def vurgu(metin):
    st.markdown(f"<div style='font-size:15px;font-weight:600;margin:4px 0 8px;line-height:1.4'>{metin}</div>", unsafe_allow_html=True)


def info(metin):
    metin = metin.replace("'", "’").replace('"', "”")
    return f"<span title='{metin}' style='display:inline-flex;width:14px;height:14px;border:1px solid #9aa3b2;border-radius:50%;font-size:10px;align-items:center;justify-content:center;color:#5b6475;margin-left:4px;cursor:help'>i</span>"


def musteri_baslangic(tum):
    return tum.groupby("CustomerID")["gun"].min()


@st.cache_data(show_spinner="Churn modeli eğitiliyor…")
def churn_c(_df, vid):
    return an.churn_modeli(_df)


@st.cache_data(show_spinner="Hesaplanıyor…")
def birlikte_c(_m, anahtar, a, b):
    x = an.araliga_kes(_m, a, b)
    return an.birlikte(x, 20) if not x.empty else []
