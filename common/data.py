"""Ortak veri okuma ve temizleme. Tüm sayfalar veriyi buradan alır."""
import io
import pandas as pd
import streamlit as st

ZORUNLU = ["InvoiceNo", "CustomerID", "InvoiceDate", "Description",
           "Category", "City", "Quantity", "UnitPrice", "NetPrice"]


def oku(dosya) -> pd.DataFrame:
    """CSV, Excel veya Parquet dosyasını DataFrame'e çevirir."""
    ad = dosya.name.lower()
    if ad.endswith(".parquet"):
        return pd.read_parquet(dosya)
    if ad.endswith(".xlsx"):
        return pd.read_excel(dosya)
    ham = dosya.getvalue() if hasattr(dosya, "getvalue") else dosya.read()
    ornek = ham[:2000].decode("utf-8-sig", errors="ignore")
    ayrac = ";" if ornek.count(";") > ornek.count(",") else ","
    ondalik = "," if ayrac == ";" else "."
    return pd.read_csv(io.BytesIO(ham), sep=ayrac, decimal=ondalik,
                       encoding="utf-8-sig", dtype={"StockCode": str})


def kontrol(df: pd.DataFrame) -> list[str]:
    """Hata mesajlarını döndürür. Liste boşsa dosya uygundur."""
    hatalar = []
    eksik = [c for c in ZORUNLU if c not in df.columns]
    if eksik:
        hatalar.append("Eksik sütun: " + ", ".join(eksik) +
                       ". Sütun adlarını kontrol edip yeniden yükle.")
        return hatalar
    tarih = pd.to_datetime(df["InvoiceDate"], errors="coerce")
    bozuk = int(tarih.isna().sum())
    if bozuk:
        hatalar.append(f"InvoiceDate sütununda {bozuk:,} satır tarih olarak okunamadı.".replace(",", "."))
    return hatalar


def temizle(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Eksik ve geçersiz satırları çıkarır, brüt/net/indirim hesaplar."""
    d = df.copy()
    d["InvoiceDate"] = pd.to_datetime(d["InvoiceDate"], errors="coerce")
    for c in ["Quantity", "UnitPrice", "NetPrice"]:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    ilk = len(d)
    d = d.dropna(subset=["InvoiceDate", "CustomerID", "Quantity", "UnitPrice", "NetPrice"])
    d = d[(d["Quantity"] > 0) & (d["UnitPrice"] > 0) & (d["NetPrice"] > 0)].copy()
    d["CustomerID"] = d["CustomerID"].astype(str)
    d["gross"] = d["Quantity"] * d["UnitPrice"]
    d["net"] = d["Quantity"] * d["NetPrice"]
    d["disc"] = 1 - d["net"] / d["gross"]
    return d, ilk - len(d)


@st.cache_data(show_spinner=False)
def hazirla(dosya_adi: str, icerik: bytes):
    """Dosyayı okur, kontrol eder, temizler. Aynı dosya için bir kez çalışır."""
    class _F(io.BytesIO):
        name = dosya_adi
        def getvalue(self_):  # noqa: N805
            return icerik
    ham = oku(_F(icerik))
    hatalar = kontrol(ham)
    if hatalar:
        return None, 0, hatalar
    temiz, atilan = temizle(ham)
    return temiz, atilan, []


def veri() -> pd.DataFrame:
    return st.session_state["df"]
