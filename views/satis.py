"""Satış & Fiyat sayfası (Selin)."""
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
from common import data, ui

ui.baslik("Satış & Fiyat", "Seçili dönemde ciro, indirim ve ürün performansı")
df, a, b = ui.tarih_filtresi(data.veri())

if df.empty:
    st.warning("Seçilen tarih aralığında satış yok.")
    st.stop()

gun = max((b - a).days + 1, 1)

# --- Üst metrikler: toplam + günlük ortalama
net, brut = df["net"].sum(), df["gross"].sum()
siparis = df["InvoiceNo"].nunique()
musteri = df["CustomerID"].nunique()
adet = df["Quantity"].sum()
ind = 1 - net / brut

satir = [("Net ciro", net, ui.tl), ("Brüt ciro", brut, ui.tl),
         ("Satılan adet", adet, ui.sayi), ("Sipariş adedi", siparis, ui.sayi),
         ("Aktif müşteri", musteri, ui.sayi)]
cols = st.columns(len(satir) + 1)
for c, (ad, v, f) in zip(cols, satir):
    c.metric(ad, f(v))
    c.caption(f"Günlük ort. {f(v / gun)}")
cols[-1].metric("Ortalama indirim", ui.yuzde(ind))
cols[-1].caption("Brüt cirodan net cironun farkı")

# --- 1. Günlük / haftalık net ciro ve indirim
st.subheader("Net ciro ve indirim oranı")
periyot = st.radio("Görünüm", ["Günlük", "Haftalık", "Aylık"], horizontal=True, index=1)
kural = {"Günlük": "D", "Haftalık": "W", "Aylık": "MS"}[periyot]
z = (df.set_index("InvoiceDate")[["net", "gross"]].resample(kural).sum())
z["ind"] = 1 - z["net"] / z["gross"]
fig = go.Figure()
fig.add_bar(x=z.index, y=z["net"], name="Net ciro", marker_color=ui.RENK["yesil"])
fig.add_scatter(x=z.index, y=z["ind"] * 100, name="İndirim %", yaxis="y2",
                line=dict(color=ui.RENK["sari"], width=2),
                hovertemplate="%{x|%d.%m.%Y}<br>İndirim %{y:.1f}%<extra></extra>")
fig.update_layout(yaxis2=dict(overlaying="y", side="right", ticksuffix="%", showgrid=False),
                  margin=dict(l=0, r=0, t=10, b=0), height=340,
                  legend=dict(orientation="h", y=1.1))
st.plotly_chart(fig, use_container_width=True)

# --- 2. Kategori kırılımı
st.subheader("Kategoriye göre net ciro ve indirim")
k = (df.groupby("Category").agg(net=("net", "sum"), gross=("gross", "sum"), adet=("Quantity", "sum"))
       .assign(ind=lambda x: 1 - x["net"] / x["gross"]).sort_values("net", ascending=False))
sol, sag = st.columns(2)
with sol:
    f1 = px.bar(k.head(12).iloc[::-1], x="net", y=k.head(12).iloc[::-1].index, orientation="h",
                labels={"net": "Net ciro (₺)", "y": ""}, color_discrete_sequence=[ui.RENK["yesil"]])
    f1.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=380)
    st.plotly_chart(f1, use_container_width=True)
with sag:
    gorunum = k.head(12).copy()
    gorunum.columns = ["Net ciro", "Brüt ciro", "Adet", "İndirim"]
    gorunum["İndirim"] = (gorunum["İndirim"] * 100).round(1)
    st.dataframe(gorunum, use_container_width=True, height=380,
                 column_config={"İndirim": st.column_config.NumberColumn(format="%.1f %%"),
                                "Net ciro": st.column_config.NumberColumn(format="%.0f"),
                                "Brüt ciro": st.column_config.NumberColumn(format="%.0f"),
                                "Adet": st.column_config.NumberColumn(format="%.0f")})

# --- 3. Ciro köprüsü: önceki eşit uzunluktaki dönem -> bu dönem
st.subheader("Ciro köprüsü: önceki döneme göre")
onc_b = pd.Timestamp(a) - pd.Timedelta(days=1)
onc_a = onc_b - pd.Timedelta(days=gun - 1)
tum = data.veri()
onc = tum[(tum["InvoiceDate"] >= onc_a) & (tum["InvoiceDate"] <= onc_b)]
if onc.empty:
    st.info("Önceki dönem için veri yok, köprü hesaplanamadı.")
else:
    def parca(x):
        o = x["InvoiceNo"].nunique()
        s = x["Quantity"].sum()
        return o, s / o, x["gross"].sum() / s, 1 - x["net"].sum() / x["gross"].sum()
    o0, b0, l0, d0 = parca(onc)
    o1, b1, l1, d1 = parca(df)
    n0 = o0 * b0 * l0 * (1 - d0)
    n1 = o1 * b1 * l1 * (1 - d1)
    # Sırayla değiştirerek etki ayrıştırma: sipariş -> sepet -> liste fiyatı -> indirim
    s1 = o1 * b0 * l0 * (1 - d0)
    s2 = o1 * b1 * l0 * (1 - d0)
    s3 = o1 * b1 * l1 * (1 - d0)
    adimlar = [("Önceki dönem", n0, "absolute"), ("Sipariş sayısı", s1 - n0, "relative"),
               ("Sepet büyüklüğü", s2 - s1, "relative"), ("Liste fiyatı", s3 - s2, "relative"),
               ("İndirim", n1 - s3, "relative"), ("Bu dönem", n1, "total")]
    kopru = go.Figure(go.Waterfall(
        x=[x[0] for x in adimlar], y=[x[1] for x in adimlar], measure=[x[2] for x in adimlar],
        increasing=dict(marker_color=ui.RENK["yesil"]),
        decreasing=dict(marker_color=ui.RENK["kirmizi"]),
        totals=dict(marker_color=ui.RENK["lacivert"])))
    kopru.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=320, showlegend=False)
    st.plotly_chart(kopru, use_container_width=True)
    st.caption(f"Önceki dönem: {onc_a:%d.%m.%Y} – {onc_b:%d.%m.%Y}")

# --- 4. En çok ciro getiren ürünler + indirimli satışlar
st.subheader("En çok ciro getiren ürünler")
u = (df.groupby("Description").agg(net=("net", "sum"), gross=("gross", "sum"), adet=("Quantity", "sum"))
       .assign(ind=lambda x: (1 - x["net"] / x["gross"]) * 100)
       .sort_values("net", ascending=False).head(20).reset_index())
u.columns = ["Ürün", "Net ciro", "Brüt ciro", "Adet", "İndirim %"]
st.dataframe(u, hide_index=True, use_container_width=True,
             column_config={"İndirim %": st.column_config.NumberColumn(format="%.1f %%"),
                            "Net ciro": st.column_config.NumberColumn(format="%.0f"),
                            "Brüt ciro": st.column_config.NumberColumn(format="%.0f")})
st.download_button("Excel/CSV olarak indir", u.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
                   file_name="top_urunler.csv", mime="text/csv")
