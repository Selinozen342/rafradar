"""Veri yükle sayfası: dashboard'dan önce dosya yüklemek zorunludur."""
import streamlit as st
from common import data, ui

ui.baslik("Veri setini yükle", "Dashboard, yüklediğin veriden hesaplanır. Önce dosyayı seç.")

sol, sag = st.columns([1.2, 1])
with sol:
    dosya = st.file_uploader("Dosyayı buraya sürükle ya da seç",
                             type=["xlsx", "csv", "parquet"],
                             help="Excel (.xlsx), CSV veya Parquet · en fazla 200 MB")
with sag:
    st.markdown("**Dosyada olması gerekenler**")
    st.dataframe({
        "Sütun adı": data.ZORUNLU,
        "Ne için": ["siparişi tanımlar", "segment ve churn", "tarih filtreleri",
                    "ürün analizleri", "kategori kırılımı", "il bazlı panel",
                    "satış ve stok", "brüt ciro", "indirim ve net ciro"],
    }, hide_index=True, use_container_width=True)

if dosya is not None:
    with st.status("Veri işleniyor…", expanded=True) as durum:
        st.write("Dosya okunuyor ve kontrol ediliyor")
        df, atilan, hatalar = data.hazirla(dosya.name, dosya.getvalue())
        if hatalar:
            durum.update(label="Dosya uygun değil", state="error")
            for h in hatalar:
                st.error(h)
        else:
            st.write("Temizlendi, brüt/net/indirim hesaplandı")
            durum.update(label="Veri hazır", state="complete", expanded=False)
            st.session_state["df"] = df
            st.session_state["atilan"] = atilan
            st.session_state["dosya_adi"] = dosya.name

if "df" in st.session_state:
    d = st.session_state["df"]
    st.success("Veri hazır")
    c = st.columns(5)
    c[0].metric("Kullanılan satır", ui.sayi(len(d)))
    c[1].metric("Müşteri", ui.sayi(d["CustomerID"].nunique()))
    c[2].metric("Ürün", ui.sayi(d["Description"].nunique()))
    c[3].metric("İlk tarih", f'{d["InvoiceDate"].min():%d.%m.%Y}')
    c[4].metric("Son tarih", f'{d["InvoiceDate"].max():%d.%m.%Y}')
    st.caption(f'{ui.sayi(st.session_state["atilan"])} satır temizlikte çıkarıldı.')
    if st.button("Dashboard'a geç", type="primary"):
        st.switch_page("views/yonetici.py")
