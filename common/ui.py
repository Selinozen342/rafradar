"""Ortak görünüm: renkler, sayı biçimi, üst bilgi."""
import streamlit as st

RENK = {"lacivert": "#1f2a44", "yesil": "#3d9a84", "sari": "#e0a526",
        "kirmizi": "#c8503f", "gri": "#9aa3b2"}


def sayi(x, ondalik=0):
    s = f"{x:,.{ondalik}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def tl(x):
    if abs(x) >= 1e6:
        return sayi(x / 1e6, 2) + " M ₺"
    if abs(x) >= 1e3:
        return sayi(x / 1e3, 0) + " B ₺"
    return sayi(x, 0) + " ₺"


def yuzde(x, ondalik=1):
    return "%" + sayi(x * 100, ondalik)


def baslik(ad: str, alt: str = ""):
    st.title(ad)
    if alt:
        st.caption(alt)


def tarih_filtresi(df):
    """Kenar çubuğundaki ortak tarih aralığı. Seçili aralıktaki veriyi döndürür."""
    mn, mx = df["InvoiceDate"].min().date(), df["InvoiceDate"].max().date()
    with st.sidebar:
        st.subheader("Tarih aralığı")
        aralik = st.date_input("Dönem", value=(mn, mx), min_value=mn, max_value=mx,
                               format="DD.MM.YYYY", key="tarih")
    if isinstance(aralik, tuple) and len(aralik) == 2:
        a, b = aralik
    else:
        a, b = mn, mx
    m = (df["InvoiceDate"].dt.date >= a) & (df["InvoiceDate"].dt.date <= b)
    return df[m], a, b
