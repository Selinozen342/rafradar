"""Ortak görünüm: stil, sayı biçimi, filtreler, Excel çıktısı."""
import io
import pandas as pd
import streamlit as st

RENK = {"lacivert": "#1f2a44", "yesil": "#3d9a84", "sari": "#e0a526",
        "kirmizi": "#d0574f", "gri": "#9aa3b2"}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', system-ui, sans-serif; }
.block-container { padding-top: 1.6rem; max-width: 1280px; }
h1, h2, h3 { font-family: 'Poppins', sans-serif !important; color: #1f2a44; }
[data-testid="stSidebar"] { background: #f1ede4; }
[data-testid="stVerticalBlockBorderWrapper"] { border-radius: 14px; border-color: #e4dfd6; background: #fff; }
.pill { display:inline-block; padding:3px 10px; border-radius:999px; font-size:12px; background:#ece7dd; color:#1f2a44; margin-right:6px; }
.pill.g { background:#d6ece5; color:#14513f } .pill.y { background:#fdf0cf; color:#7a5600 }
.pill.r { background:#fbe3e0; color:#8f2a24 }
.kgrid { display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:12px; margin:10px 0 6px }
.kpi { background:#fff; border:1px solid #e4dfd6; border-top:4px solid #3d9a84; border-radius:14px; padding:12px 14px }
.kpi.y { border-top-color:#e0a526 }
.kpi .kl { font-size:12px; color:#5b6475 } .kpi .kv { font-family:Poppins,sans-serif; font-weight:700; font-size:24px; color:#1f2a44 }
.kpi .kv2 { font-family:Poppins,sans-serif; font-weight:700; font-size:18px; color:#1f2a44 }
.kpi .rule { border-top:1px dashed #d8d2c6; margin:8px 0 }
.chg { display:inline-block; font-size:12px; padding:1px 8px; border-radius:6px; background:#ece7dd; color:#5b6475 }
.chg.pos { background:#d6ece5; color:#14513f } .chg.neg { background:#fbe3e0; color:#8f2a24 }
.chg.neu { background:#e6ebf5; color:#2a3a63 }
.hd { font-family:Poppins,sans-serif !important; font-weight:700 !important; font-size:18px !important; line-height:1.3 !important; color:#1f2a44; margin:0 !important; padding:0 !important }
.num { display:inline-flex; width:22px; height:22px; border-radius:50%; background:#1f2a44; color:#fff; font-size:12px; align-items:center; justify-content:center; margin-right:8px; font-family:Inter,sans-serif }
.sub { color:#5b6475 !important; font-size:13px !important; margin:2px 0 8px !important }
.lst { font-size:13px; line-height:1.45; margin:0; padding-left:18px } .lst li { margin-bottom:8px } .lst small { color:#5b6475 }
.out { background:#f1f7f5; border-radius:10px; padding:8px 12px } .out .t { font-size:12px; color:#5b6475 } .out .v { font-family:Poppins,sans-serif; font-weight:700; font-size:20px; color:#1f2a44 }
table.t { width:100%; border-collapse:collapse; font-size:13px } table.t th { text-align:left; font-size:12px; color:#5b6475; font-weight:500; padding:6px 8px; border-bottom:1px solid #e4dfd6 }
table.t td { padding:7px 8px; border-bottom:1px solid #eee9df } table.t td.r, table.t th.r { text-align:right }
.st-key-rafbot { position:fixed; right:24px; bottom:24px; z-index:1000; width:auto !important; }
.st-key-rafbot [data-testid="stPopoverButton"] { width:56px; height:56px; border-radius:50%; background:#3d9a84; color:#fff; border:none; font-size:22px; box-shadow:0 4px 14px rgba(0,0,0,.25) }
</style>
"""


def stil():
    st.markdown(CSS, unsafe_allow_html=True)


def sayi(x, ondalik=0):
    s = f"{x:,.{ondalik}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def isaret(x, ondalik=1):
    return ("+" if x >= 0 else "−") + sayi(abs(x), ondalik)


def tl(x):
    if abs(x) >= 1e6:
        return sayi(x / 1e6, 2) + " M ₺"
    if abs(x) >= 1e3:
        return sayi(x / 1e3, 1) + " bin ₺"
    return sayi(x, 0) + " ₺"


def yuzde(x, ondalik=1):
    return "%" + sayi(x * 100, ondalik)


AYLAR = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]


def tarih_etiketi(a, b):
    a, b = pd.Timestamp(a), pd.Timestamp(b)
    if a == b:
        return f"{a.day} {AYLAR[a.month - 1]} {a.year}"
    if a.month == b.month and a.year == b.year:
        return f"{a.day} – {b.day} {AYLAR[b.month - 1]} {b.year}"
    if a.year == b.year:
        return f"{a.day} {AYLAR[a.month - 1]} – {b.day} {AYLAR[b.month - 1]} {b.year}"
    return f"{a.day} {AYLAR[a.month - 1]} {a.year} – {b.day} {AYLAR[b.month - 1]} {b.year}"


def baslik(ad: str, alt: str = ""):
    stil()
    st.markdown(f"<h1 style='margin:0 0 2px'>{ad}</h1>", unsafe_allow_html=True)
    if alt:
        st.markdown(f"<p class='sub' style='font-style:italic;font-size:15px'>{alt}</p>", unsafe_allow_html=True)


def bolum(no, ad, alt=""):
    st.markdown(f"<h3 class='hd'><span class='num'>{no}</span>{ad}</h3>" +
                (f"<p class='sub'>{alt}</p>" if alt else ""), unsafe_allow_html=True)


def xlsx(df: pd.DataFrame, sayfa="Liste") -> bytes:
    b = io.BytesIO()
    with pd.ExcelWriter(b, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name=sayfa)
    return b.getvalue()


def filtreler(df):
    """Kenar çubuğu: tarih, karşılaştırma, kategori, ürün, şehir. Süzülmüş veriyi ve tarihleri döndürür."""
    mn, mx = df["gun"].min().date(), df["gun"].max().date()
    ss = st.session_state
    if "a" not in ss:
        b0 = mx
        a0 = max(mn, mx - pd.Timedelta(days=44))
        ss["a"], ss["b"] = a0, b0
        gun0 = (b0 - a0).days + 1
        ss["cb"] = (pd.Timestamp(a0) - pd.Timedelta(days=1)).date()
        ss["ca"] = (pd.Timestamp(ss["cb"]) - pd.Timedelta(days=gun0 - 1)).date()
    with st.sidebar:
        st.markdown("<b style='font-family:Poppins;font-size:20px'>RafRadar</b>", unsafe_allow_html=True)
        st.markdown("**FİLTRELER**")
        r = st.date_input("Tarih aralığı", value=(ss["a"], ss["b"]), min_value=mn, max_value=mx,
                          format="DD.MM.YYYY")
        if isinstance(r, (tuple, list)) and len(r) == 2:
            ss["a"], ss["b"] = r
        a, b = ss["a"], ss["b"]
        gun = (b - a).days + 1
        c = st.date_input("Karşılaştırma aralığı", value=(ss["ca"], ss["cb"]),
                          min_value=min(mn, ss["ca"]), max_value=mx, format="DD.MM.YYYY")
        if isinstance(c, (tuple, list)) and len(c) == 2:
            ss["ca"], ss["cb"] = c
        if st.button("Önceki dönemi al"):
            cb0 = pd.Timestamp(a) - pd.Timedelta(days=1)
            ss["cb"] = cb0.date()
            ss["ca"] = (cb0 - pd.Timedelta(days=gun - 1)).date()
            st.rerun()
        kat = st.selectbox("Kategori", ["Tümü"] + sorted(df["Category"].dropna().unique().tolist()), key="f_kat")
        urun_secenek = df if kat == "Tümü" else df[df["Category"] == kat]
        urun = st.selectbox("Ürün", ["Tümü"] + urun_secenek.groupby("Description")["net"].sum()
                            .sort_values(ascending=False).head(300).index.tolist(), key="f_urun")
        sehir = st.selectbox("Şehir", ["Tümü"] + sorted(df["City"].dropna().unique().tolist()), key="f_sehir")
    m = df
    if kat != "Tümü":
        m = m[m["Category"] == kat]
    if urun != "Tümü":
        m = m[m["Description"] == urun]
    if sehir != "Tümü":
        m = m[m["City"] == sehir]
    return m, ss["a"], ss["b"], ss["ca"], ss["cb"]
