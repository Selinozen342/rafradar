"""Yönetici Özeti. HTML taslağındaki 5 bölümün aynısı, veriden canlı hesaplanır."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from common import analytics as an
from common import analytics2 as an2
from common import chat, data, ui
from common import widgets as w


@st.cache_data(show_spinner=False)
def c_dagilim(_tum, vid):
    return an2.metrik_dagilimi(_tum)


@st.cache_data(show_spinner="Tahmin hesaplanıyor…")
def c_baz(_tum, vid):
    return an2.baz_tahmin30(_tum)


@st.cache_data(show_spinner=False)
def c_yavas(_tum, vid):
    return an2.yavas_urunler(_tum)


tum = data.veri()
vid = (st.session_state.get("dosya_adi", ""), len(tum))
ui.baslik("Yönetici Özeti", "Seçtiğim dönem yılın neresinde ve önümüzdeki 30 günde ne yapmalıyız?")
m, a, b, ca, cb = ui.filtreler(tum)
K = w.fk()
et = ui.tarih_etiketi
bit = tum["gun"].max()
S = w.ozet_c(m, K, a, b)
yil_ort = an.ozet(tum, tum["gun"].min().date(), bit.date())
st.markdown(f"<span class='pill g'>Seçili: {et(a, b)} · {S['gun']} gün</span><span style='font-size:12px;color:#5b6475'>karşılaştırma</span> "
            f"<span class='pill'>veri ortalaması · günlük</span>", unsafe_allow_html=True)

# ---------- 1-2 ----------
p1, p2 = st.columns([1.9, 1])
yillar = sorted(set(tum["gun"].dt.year.unique().tolist()) | {tum["gun"].dt.year.min() - 1, tum["gun"].dt.year.max() + 1})
with p1, st.container(border=True):
    h1, h2 = st.columns([3, 1])
    with h1:
        ui.bolum(1, "Yıllık genel bakış", "Tarih filtresinden bağımsız · çubuk: aylık net ciro · çizgi: indirim oranı")
    with h2:
        yil = st.selectbox("Yıl", yillar, index=yillar.index(bit.year), key="yon_yil")
    ay = an2.aylik(tum, yil)
    if ay is None:
        st.markdown(f"<div style='padding:60px 16px;text-align:center;background:#faf7f2;border-radius:10px;font-size:13px;color:#5b6475'><b style='color:#1f2a44'>{yil} için veri yok.</b><br>Veri seti bu yılı kapsamıyor.</div>", unsafe_allow_html=True)
    else:
        mxm = ay["net"].max()
        pk = int(ay["net"].values.argmax())
        vl = int(ay.loc[ay["net"] > 0, "net"].values.argmin()) if (ay["net"] > 0).any() else 0
        renk = ["#1d6b58" if i == pk else ("#9fcfc2" if i == vl else "#3d9a84") for i in range(12)]
        fig = go.Figure()
        fig.add_bar(x=ui.AYLAR, y=ay["net"] / 1e6, marker_color=renk, name="Net ciro", customdata=np.c_[ay["net"] / 1e6, ay["disc"] * 100],
                    hovertemplate="%{x}<br>Net ciro %{customdata[0]:.2f} M ₺<br>İndirim oranı %%{customdata[1]:.1f}<extra></extra>")
        fig.add_scatter(x=ui.AYLAR, y=ay["disc"] * 100, yaxis="y2", mode="lines+markers", line=dict(color="#e0a526", width=2), name="İndirim %",
                        hovertemplate="%{x}<br>İndirim %{y:.1f}%<extra></extra>")
        fig.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0), plot_bgcolor="white", showlegend=False,
                          yaxis=dict(title="M ₺", rangemode="tozero"),
                          yaxis2=dict(overlaying="y", side="right", range=[35, 44], showgrid=False, ticksuffix="%"))
        fig.add_annotation(x=ui.AYLAR[pk], y=mxm / 1e6, text=f"zirve {ui.sayi(mxm / 1e6, 2)}", showarrow=False, yshift=12, font=dict(size=11))
        st.plotly_chart(fig, use_container_width=True)
        tot = ay["net"].sum()
        gross = ay["gross"].sum()
        st.markdown(f"<span class='pill g'>Yıllık net ciro {ui.sayi(tot / 1e6, 2)} M ₺</span><span class='pill y'>İndirim oranı %{ui.sayi((1 - tot / gross) * 100, 1)}</span>"
                    "<span class='pill'>Aya gel: ciro ve indirim oranı görünür</span>", unsafe_allow_html=True)

pm = an.pareto(m, "CustomerID")
pu = an.pareto(m, "Description")
with p2, st.container(border=True):
    ui.bolum(2, "Portföy yapısı", "Müşteri ve ürünler ciro payına göre A (%80) · B (%15) · C (%5)")

    def seritler(p, ad, birim):
        n = len(p)
        c = {k: int((p["seg"] == k).sum()) for k in "ABC"}
        renk = {"A": "#3d9a84", "B": "#e0a526", "C": "#d9622b"}
        bar = "".join(f"<div style='flex:{max(c[k], 0.001)} 1 0;background:{renk[k]};color:#fff;font-size:12px;font-weight:700;text-align:center;padding:5px 0'>{k}</div>" for k in "ABC")
        return (f"<div style='font-weight:600;font-size:13px;margin-top:6px'>{ad} · {ui.sayi(n)}</div><div style='display:flex;border-radius:6px;overflow:hidden;margin:4px 0'>{bar}</div>"
                f"<div style='font-size:11px;color:#5b6475'>A {ui.sayi(c['A'])} · B {ui.sayi(c['B'])} · C {ui.sayi(c['C'])} {birim}</div>"), c, n
    t1, c1, n1 = seritler(pm, "Müşteriler", "müşteri")
    t2, c2, n2 = seritler(pu, "Ürünler", "ürün")
    st.markdown(t1 + t2, unsafe_allow_html=True)
    st.markdown(f"<div style='background:#faf7f2;border-radius:10px;padding:8px 12px;font-size:12px;margin-top:10px'>Müşterilerin %{ui.sayi(c1['A'] / n1 * 100, 1)}’i, ürünlerin %{ui.sayi(c2['A'] / n2 * 100, 0)}’i cironun %80’ini getiriyor.</div>", unsafe_allow_html=True)

# ---------- 3. Dönem özeti ----------
dag = c_dagilim(tum, vid)
tanim = [("dnet", "Günlük net ciro", "Satış", "#3d9a84", lambda v: ui.sayi(v / 1000, 1) + " bin ₺", 1),
         ("dord", "Günlük sipariş", "Satış", "#3d9a84", lambda v: ui.sayi(v), 1),
         ("basket", "Ortalama sepet tutarı", "Satış", "#3d9a84", lambda v: ui.sayi(v) + " ₺", 1),
         ("disc", "İndirim oranı", "Fiyat", "#e0a526", lambda v: "%" + ui.sayi(v * 100, 1), -1),
         ("dcust", "Günlük aktif müşteri", "Pazarlama", "#d9622b", lambda v: ui.sayi(v), 1),
         ("dq", "Günlük satılan adet", "Tedarik", "#3b6fd1", lambda v: ui.sayi(v) + " adet", 1)]


def serit(vals, v, yv, renk):
    lo, hi = min(min(vals), v), max(max(vals), v)
    X = lambda x: 8 + (x - lo) / (hi - lo if hi > lo else 1) * 284
    nokta = "".join(f"<circle cx='{X(x):.1f}' cy='14' r='4' fill='#b9b3a6'/>" for x in vals)
    return (f"<svg viewBox='0 0 300 28' width='100%' height='28'><line x1='8' x2='292' y1='14' y2='14' stroke='#ece7dd' stroke-width='8' stroke-linecap='round'/>"
            f"{nokta}<line x1='{X(yv):.1f}' x2='{X(yv):.1f}' y1='3' y2='25' stroke='#1f2a44' stroke-width='2.5'/><circle cx='{X(v):.1f}' cy='14' r='8' fill='{renk}'/></svg>"), lo, hi


satirlar = ""
rel0 = w.rel(S["dnet"], yil_ort["dnet"]) * 100
daha_yuksek = sum(1 for x in dag["dnet"] if x > S["dnet"])
dd = S["disc"] - yil_ort["disc"]
basl = (f"Günlük ciro yıl ortalamasının %{ui.sayi(abs(rel0), 0)} {'üstünde' if rel0 >= 0 else 'altında'} ({len(dag['dnet'])} ay içinde {daha_yuksek + 1}. sırada); "
        f"indirim yıl ortalamasından {ui.sayi(abs(dd) * 100, 1)} puan {'düşük' if dd <= 0 else 'yüksek'}.")
for k, ad, dep, renk, f, iyi in tanim:
    v, yv = S[k], yil_ort[k]
    svg, lo, hi = serit(dag[k], v, yv, renk)
    rl = (v - yv) * 100 if k == "disc" else (v / yv - 1) * 100 if yv else 0
    kucuk = abs(rl) < (0.3 if k == "disc" else 1.5)
    iyi_mi = iyi * rl > 0
    delta = (f"{'▲ ' if rl >= 0 else '▼ '}{ui.sayi(abs(rl), 1)} puan" if k == "disc" else f"{'▲ %' if rl >= 0 else '▼ %'}{ui.sayi(abs(rl), 1)}") + " yıl ort."
    sinif = "mute" if kucuk else ("pos" if iyi_mi else "neg")
    satirlar += (f"<div style='display:grid;grid-template-columns:minmax(120px,1fr) minmax(200px,2.6fr) minmax(90px,1fr);gap:12px;align-items:center;padding:8px 0;border-bottom:1px solid #eee9df'>"
                 f"<div><span style='display:inline-block;width:8px;height:8px;border-radius:50%;background:{renk};margin-right:6px'></span><b style='font-size:13px'>{ad}</b>"
                 f"<div style='font-size:11px;color:#5b6475'>{dep}</div></div>"
                 f"<div>{svg}<div style='display:flex;justify-content:space-between;font-size:11px;color:#5b6475'><span>{f(lo)}</span><span>{f(hi)}</span></div></div>"
                 f"<div style='text-align:right'><div style='font-family:Poppins;font-weight:700;font-size:16px'>{f(v)}</div><span class='chg {sinif}'>{delta}</span></div></div>")
with st.container(border=True):
    ui.bolum(3, "Dönem özeti", basl)
    st.markdown(satirlar + "<div style='font-size:11px;color:#5b6475;margin-top:6px'><span style='color:#3d9a84'>●</span> seçili dönem · <span style='color:#b9b3a6'>●</span> aylık günlük ortalamalar · "
                "<b style='color:#1f2a44'>|</b> tüm verinin günlük ortalaması</div>", unsafe_allow_html=True)

# ---------- 4. Departmanlar arası çıkarımlar ----------
churn, auc = w.churn_c(tum, vid)
pc = an.pareto(an.araliga_kes(tum, tum["gun"].min().date(), bit.date()), "CustomerID")
son = tum.groupby("CustomerID")["gun"].max()
cpas = ((bit - son.reindex(pc.index[pc["seg"] == "C"])).dt.days > 90).mean() * 100
dow = tum.groupby("dow")["net"].sum()
pzt = dow.get(0, 0) / dow.sum() * 100
yavas = c_yavas(tum, vid)
with st.container(border=True):
    ui.bolum(4, "Cross-functional insights · departmanlar arası çıkarımlar", "Tek departmana bakınca görünmeyen üç şey")
    kt = [("Satış", "Pazarlama", "#d6ece5", "#fbe0d3", f"%{ui.sayi(cpas, 0)} sessiz", f"Küçük müşterilerin (C) yaklaşık %{ui.sayi(cpas, 0)}’i 3 aydır sipariş vermemiş. Ciro düşüşünün sebebi fiyat değilse sipariş sayısına bak."),
          ("Satış", "Tedarik", "#d6ece5", "#dbe5f8", f"%{ui.sayi(pzt, 0)} pazartesi", "Satışın büyük kısmı pazartesi geliyor. Cuma gününe küçük bir indirim koyarsak depo yükü haftaya yayılır."),
          ("Tedarik", "Satış", "#dbe5f8", "#d6ece5", f"{ui.sayi(len(yavas))} yavaş ürün", f"Son 90 günde satışı bir önceki 90 güne göre %70 ve üzeri düşen {ui.sayi(len(yavas))} ürün var. Yanında sık alınan bir ürünle paket yapıp satabiliriz.")]
    for kol, (d1, d2, b1, b2, buyuk, txt) in zip(st.columns(3), kt):
        kol.markdown(f"<div style='background:#faf7f2;border:1px solid #e4dfd6;border-radius:12px;padding:12px 14px;height:100%'><span class='pill' style='background:{b1}'>{d1}</span>"
                     f"<span class='pill' style='background:{b2}'>{d2}</span><div style='font-family:Poppins;font-weight:700;font-size:20px;margin:6px 0'>{buyuk}</div>"
                     f"<div style='font-size:12px;line-height:1.5'>{txt}</div></div>", unsafe_allow_html=True)

# ---------- 5. Aksiyon planı ----------
baz, wape = c_baz(tum, vid)
yavas = c_yavas(tum, vid)
cm = an.pareto(tum, "CustomerID").join(churn[["p", "risk", "m30"]])
hiAB = cm[(cm["seg"].isin(["A", "B"])) & (cm["risk"] == "Yüksek")]
cOK = cm[(cm["seg"] == "C") & (cm["risk"].isin(["Orta", "Yüksek"]))]
fiyat = tum["net"].sum() / tum["Quantity"].sum()
wk_q = tum.groupby("gun")["Quantity"].sum().reindex(pd.date_range(tum["gun"].min(), bit), fill_value=0)
haf_q = wk_q.values[: len(wk_q) // 7 * 7].reshape(-1, 7).sum(axis=1)
base_u = float(haf_q[-8:].mean())
kapasite = float(haf_q.max())
bitis30 = bit + pd.Timedelta(days=30)
with st.container(border=True):
    ui.bolum(5, "Önümüzdeki 30 gün için aksiyon planı",
             f"Aksiyonları aç/kapat, oranları değiştir. Tahmin {et(bit + pd.Timedelta(days=1), bitis30)} için (veri {et(bit, bit)} tarihinde bitiyor)")
    k1, k2, k3 = st.columns(3)
    with k1.container(border=True):
        st.markdown("<span class='pill' style='background:#d9622b;color:#fff'>Pazarlama</span><span class='pill' style='background:#1f2a44;color:#fff'>Satış</span>", unsafe_allow_html=True)
        st.markdown("**Büyük müşterileri ara**")
        st.caption(f"Bırakma riski yüksek {len(hiAB)} büyük müşteriyi satış temsilcisi arasın. Bırakırlarsa gelecek ay yaklaşık {ui.tl(hiAB['m30'].sum())} kaybederiz.")
        sa = st.slider("Geri dönen müşteri oranı (%)", 0, 60, 25, key="ak_a")
        gA = hiAB["m30"].sum() * sa / 100
        onA = st.toggle("Planda", value=True, key="ak_a_on")
        st.markdown(f"<div style='font-family:Poppins;font-weight:700;font-size:20px'>+{ui.tl(gA)}</div>", unsafe_allow_html=True)
    with k2.container(border=True):
        st.markdown("<span class='pill' style='background:#3d9a84;color:#fff'>Satış</span><span class='pill' style='background:#1f2a44;color:#fff'>Tedarik</span>", unsafe_allow_html=True)
        st.markdown("**Yavaş ürünleri paketle**")
        st.caption(f"Satışı düşen {len(yavas)} ürünü, yanında sık alınan hızlı ürünle paket yap ve ek indirim ver. Satışın ne kadar artacağı bir varsayımdır.")
        sb = st.slider("Pakete ek indirim (puan)", 0, 20, 8, key="ak_b")
        oran = (1 - yavas["d"] - sb / 100) / (1 - yavas["d"])
        qa = yavas["q90"] * (oran ** -2.2 - 1)
        gB = float((qa * yavas["pr"] * oran).sum()) / 3
        uB = float(qa.sum()) / 3
        onB = st.toggle("Planda", value=True, key="ak_b_on")
        st.markdown(f"<div style='font-family:Poppins;font-weight:700;font-size:20px'>+{ui.tl(gB)}</div>", unsafe_allow_html=True)
    with k3.container(border=True):
        st.markdown("<span class='pill' style='background:#e0a526'>Pazarlama</span><span class='pill' style='background:#1f2a44;color:#fff'>Tedarik</span>", unsafe_allow_html=True)
        st.markdown("**Küçük müşterilere kupon gönder**")
        st.caption(f"Bırakma riski olan {len(cOK)} küçük müşteriye otomatik kupon gönder. Artan talebe stok yeter mi, aşağıda görülür.")
        sc = st.slider("Kuponu kullanan oranı (%)", 0, 40, 15, key="ak_c")
        gC = cOK["m30"].sum() * sc / 100
        onC = st.toggle("Planda", value=True, key="ak_c_on")
        st.markdown(f"<div style='font-family:Poppins;font-weight:700;font-size:20px'>+{ui.tl(gC)}</div>", unsafe_allow_html=True)
    tot = (gA if onA else 0) + (gB if onB else 0) + (gC if onC else 0)
    WK = 30 / 7
    ek_u = ((gA / fiyat if onA else 0) + (uB if onB else 0) + (gC / fiyat if onC else 0)) / WK
    util = (base_u + ek_u) / kapasite * 100
    fig = go.Figure()
    fig.add_bar(y=["Tahmin"], x=[baz / 1e6], orientation="h", marker_color="#d4cdbf", name="Bir şey yapmazsak", text=[f"Bir şey yapmazsak {ui.sayi(baz / 1e6, 2)} M ₺"], textposition="inside")
    for ad, g, on, rn in (("Büyük müşterileri ara", gA, onA, "#d9622b"), ("Yavaş ürünleri paketle", gB, onB, "#3d9a84"), ("Kupon", gC, onC, "#e0a526")):
        if on:
            fig.add_bar(y=["Tahmin"], x=[g / 1e6], orientation="h", marker_color=rn, name=ad, hovertemplate=f"{ad}: +%{{x:.3f}} M ₺<extra></extra>")
    fig.add_vrect(x0=baz * (1 - wape) / 1e6, x1=baz * (1 + wape) / 1e6, fillcolor="rgba(31,42,68,.08)", line_width=0, layer="below")
    fig.update_layout(barmode="stack", height=130, margin=dict(l=0, r=0, t=6, b=0), showlegend=False, plot_bgcolor="white",
                      xaxis=dict(range=[0, baz * 1.32 / 1e6], title=f"tahmin ±%{ui.sayi(wape * 100, 0)} oynayabilir (gölge alan) · M ₺"), yaxis=dict(showticklabels=False))
    r1, r2 = st.columns([2, 1])
    with r1:
        st.plotly_chart(fig, use_container_width=True)
    with r2:
        st.markdown(f"<div class='out'><div class='t'>Üç aksiyondan beklenen ek ciro</div><div class='v'>+{ui.tl(tot)} "
                    f"<span class='chg {'pos' if tot > 0 else 'mute'}' style='font-size:11px'>+%{ui.sayi(tot / baz * 100, 1)}</span></div></div>"
                    f"<div style='margin-top:6px'><span class='pill' style='background:{'#fbe3e0' if util > 100 else ('#fdf0cf' if util > 90 else '#d6ece5')}'>Stok kapasitesi %{ui.sayi(util, 0)} dolu</span></div>"
                    f"<div style='font-size:11px;color:#5b6475;margin-top:4px'>Kapasite varsayımı: verideki en yoğun haftanın adedi.</div>", unsafe_allow_html=True)
    st.markdown(f"<div style='font-size:12px;color:#5b6475'>Bir şey yapmazsak <b>{ui.tl(baz)}</b> · Aksiyonlarla <b>{ui.tl(baz + tot)}</b>. " +
                (f"Bu ek ciro küçük: tahminin kendisi zaten ±{ui.tl(baz * wape)} oynayabilir. Gerçek etkiyi görmek için aksiyonu müşterilerin yarısına uygula, diğer yarısıyla karşılaştır." if tot > 0 else "Plana en az bir aksiyon ekle.") + "</div>", unsafe_allow_html=True)

# ---------- RafBot ----------
aksiyon = sorted([("Büyük müşterileri ara", gA if onA else 0), ("Yavaş ürünleri paketle", gB if onB else 0), ("Küçük müşterilere kupon gönder", gC if onC else 0)], key=lambda x: -x[1])[0]
bilgi = {
    "ciro": f"Önümüzdeki 30 gün için baz tahmin ≈ {ui.tl(baz)}. Geriye dönük testte ortalama hata ≈ %{ui.sayi(wape * 100, 0)}, yani tahmin ±{ui.tl(baz * wape)} aralığında okunmalı.",
    "kopru": basl,
    "churn": f"{ui.sayi(len(hiAB))} büyük müşteri yüksek riskli; bırakırlarsa gelecek ay ≈ {ui.tl(hiAB['m30'].sum())} kaybederiz. Önce bunları ara.",
    "segment": f"Müşterilerin %{ui.sayi(c1['A'] / n1 * 100, 1)}’i, ürünlerin %{ui.sayi(c2['A'] / n2 * 100, 0)}’i cironun %80’ini getiriyor.",
    "indirim": f"Şu anki ayarlarla en çok getiren aksiyon “{aksiyon[0]}” (+{ui.tl(aksiyon[1])}). Üçünün toplamı +{ui.tl(tot)}, yani tahminin %{ui.sayi(tot / baz * 100, 1)}’i. Bu küçük bir fark.",
    "gun": f"Cironun %{ui.sayi(pzt, 0)}’i pazartesi geliyor.", "birlikte": None,
}
chat.rafbot(bilgi)
