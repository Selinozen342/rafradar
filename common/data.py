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
    ham = dosya.getvalue()
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
    d["gun"] = d["InvoiceDate"].dt.normalize()
    d["dow"] = d["gun"].dt.dayofweek
    for c in ["Category", "City", "Description"]:
        d[c] = d[c].astype("string")
    d["City"] = d["City"].str.title()
    d.loc[d["City"] == "Istanbul", "City"] = "İstanbul"
    return d, ilk - len(d)


def kalite_ozeti(ham: pd.DataFrame, temiz: pd.DataFrame, atilan: int) -> dict:
    """Veri Kalitesi sayfası için ham dosyadan sayımlar."""
    alanlar = [c for c in ZORUNLU + ["StockCode"] if c in ham.columns]
    bos = {c: int(ham[c].isna().sum()) for c in alanlar}
    bil = 0
    if "StockCode" in ham.columns:
        bil = int(ham["StockCode"].astype(str).str.contains(r"E\+\d+", regex=True, na=False).sum())
    return dict(ham_satir=len(ham), ham_sutun=ham.shape[1], temiz_satir=len(temiz), atilan=atilan,
                yeni_sutun=temiz.shape[1] - ham.shape[1], bos=bos, tekrar=int(ham.duplicated().sum()), bilimsel=bil)


@st.cache_data(show_spinner=False)
def hazirla(dosya_adi: str, icerik: bytes):
    """Dosyayı okur, kontrol eder, temizler. Aynı dosya için bir kez çalışır."""
    class _F(io.BytesIO):
        name = dosya_adi
    ham = oku(_F(icerik))
    hatalar = kontrol(ham)
    if hatalar:
        return None, 0, hatalar, {}
    temiz, atilan = temizle(ham)
    return temiz, atilan, [], kalite_ozeti(ham, temiz, atilan)


def veri() -> pd.DataFrame:
    return st.session_state["df"]
