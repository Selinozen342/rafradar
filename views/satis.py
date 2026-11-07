"""Satış & Fiyat sayfası (Selin). HTML taslağındaki 9 bölümün aynısı, veriden canlı hesaplanır."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from common import analytics as an
from common import chat, data, ui

GUNLER = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]
KAMPANYA = {
    "musteri": {
        "A": ("Sadık hesap:", "hesap yöneticisi + hacim kademeli indirim. Haftanın en yoğun gününü azaltmak için ek indirim denenebilir."),
        "B": ("A'ya yükselt:", "sepet tutarı hedefi koyup eşiği geçen siparişe sonraki siparişte indirim ver."),
        "C": ("Aktifleştir, ucuza:", "\"birlikte al\" önerisi + tekrar sipariş kuponu; riskli olanlara otomatik e-posta/SMS. Yüksek maliyetli aksiyon değmez."),
    },
    "urun": {
        "A": ("Yıldız ürün:", "stoktan eksik etme, indirimi artırma. \"Birlikte al\" önerisinde ana ürün olarak kullan."),
        "B": ("A'ya taşı:", "yıldız ürünlerle paket yap, kategori kampanyalarında öne çıkar."),
        "C": ("Uzun kuyruk:", "satılmayanları hızlı bir ürünle paketleyip erit; bu ürünlerde yeni stok alma."),
    },
}
SEG_AD = {"A": "A · cironun %80'i", "B": "B · sonraki %15", "C": "C · son %5"}
SEG_RENK = {"A": ("#d6ece5", "#14513f"), "B": ("#fdf0cf", "#7a5600"), "C": ("#fbe0d3", "#7d2f0e")}
HEAT = {("A", "Düşük"): ("#2f7f6b", "#fff"), ("A", "Orta"): ("#fdf0cf", "#1f2a44"), ("A", "Yüksek"): ("#fbe3e0", "#1f2a44"),
        ("B", "Düşük"): ("#2f7f6b", "#fff"), ("B", "Orta"): ("#f6d98a", "#1f2a44"), ("B", "Yüksek"): ("#f2b8b2", "#1f2a44"),
        ("C", "Düşük"): ("#8cc5b5", "#1f2a44"), ("C", "Orta"): ("#f0c250", "#1f2a44"), ("C", "Yüksek"): ("#a8322b", "#fff")}
RISK_PILL = {"Yüksek": "r", "Orta": "y", "Düşük": "g"}


# ---------- önbellekli hesaplar (büyük tablolar _ ile başlayınca hash'lenmez) ----------
@st.cache_data(show_spinner=False)
def c_ozet(_m, anahtar, a, b):
    return an.ozet(_m, a, b)


@st.cache_data(show_spinner="Birlikte alınanlar hesaplanıyor…")
def c_birlikte(_m, anahtar, a, b):
    x = an.araliga_kes(_m, a, b)
    return an.birlikte(x), an.en_cok_satanlar(x)


@st.cache_data(show_spinner="Birlikte alınanlar (tüm yıl) hesaplanıyor…")
def c_birlikte_yil(_m, anahtar, yil):
    return an.birlikte(_m[_m["gun"].dt.year == yil])


@st.cache_data(show_spinner="Churn modeli eğitiliyor…")
def c_churn(_df, vid):
    return an.churn_modeli(_df)


@st.cache_data(show_spinner=False)
def c_supheli(_tum, _m, anahtar, a, b, tur):
    x, oc = an.supheli(_tum, an.araliga_kes(_m, a, b), tur)
    return x, int((oc["sapma"] > 0.10).sum()), float(oc.loc[oc["sapma"] > 0.10, "fazla"].sum())


# ---------- yardımcı çıktılar ----------
def pct(x):
    return ("▲ %" if x >= 0 else "▼ %") + ui.sayi(abs(x * 100), 1)


def chg(x, vurgu):
    sinif = "mute" if not vurgu else ("neg" if x < 0 else "pos")
    return f"<span class='chg {sinif}'>{pct(x)}</span>"


def chg_p(d, vurgu):
    return f"<span class='chg {'neu' if vurgu else 'mute'}'>{'▲ ' if d >= 0 else '▼ '}{ui.sayi(abs(d * 100), 1)} puan</span>"


def rel(a, b):
    return a / b - 1 if b else 0


def kart(baslik, nom, nom_c, gun_et, gun_v, gun_c, sari=False):
    return (f"<div class='kpi{' y' if sari else ''}'><div class='kl'>{baslik}</div><div class='kv'>{nom}</div>{nom_c}"
            f"<div class='rule'></div><div class='kl'>{gun_et}</div><div class='kv2'>{gun_v}</div>{gun_c}</div>")


def tablo(basliklar, satirlar, sag=()):
    h = "".join(f"<th class='{'r' if i in sag else ''}'>{b}</th>" for i, b in enumerate(basliklar))
    r = "".join("<tr>" + "".join(f"<td class='{'r' if i in sag else ''}'>{c}</td>" for i, c in enumerate(s)) + "</tr>"
                for s in satirlar)
    return f"<table class='t'><thead><tr>{h}</tr></thead><tbody>{r}</tbody></table>"


def isi_rengi(v, mx):
    t = 0 if mx <= 0 else min(1, v / mx)
    a, b = (238, 233, 223), (27, 94, 75)
    c = tuple(int(a[i] + (b[i] - a[i]) * t ** 0.8) for i in range(3))
    yazi = "#fff" if t > 0.55 else "#1f2a44"
    return f"background:rgb{c};color:{yazi}"


# ================= sayfa =================
tum = data.veri()
vid = (st.session_state.get("dosya_adi", ""), len(tum))
ui.baslik("Satış & Fiyat", "Ne zaman, kime, hangi ürünü, hangi indirimle satmalıyız?")
m, a, b, ca, cb = ui.filtreler(tum)
fk = (vid, st.session_state.get("f_kat"), st.session_state.get("f_urun"), st.session_state.get("f_sehir"))

if m.empty:
    st.warning("Bu filtrelerle veri yok. Filtreleri gevşetip tekrar dene.")
    st.stop()

S = c_ozet(m, fk, a, b)
C = c_ozet(m, fk, ca, cb)
ayni = S["gun"] == C["gun"]
hN, hD = ayni, not ayni
et = ui.tarih_etiketi

st.markdown(
    f"<span class='pill g'>Seçili: {et(a, b)} · {S['gun']} gün</span><span style='font-size:12px;color:#5b6475'>karşılaştırma</span> "
    f"<span class='pill'>{et(ca, cb)} · {C['gun']} gün</span>"
    f"<span class='pill y'>{'Aralıklar eşit uzunlukta: vurgulu fark nominal değerlere göre' if ayni else 'Aralık uzunlukları farklı: vurgulu fark günlük ortalamaya göre'}</span>"
    "<div class='kgrid'>" +
    kart("Net ciro", ui.sayi(S["net"] / 1e6, 2) + " M ₺", chg(rel(S["net"], C["net"]), hN), "Günlük ort.",
         ui.sayi(S["dnet"] / 1000, 1) + " bin ₺", chg(rel(S["dnet"], C["dnet"]), hD)) +
    kart("Sipariş adedi", ui.sayi(S["ord"]), chg(rel(S["ord"], C["ord"]), hN), "Günlük ort.",
         ui.sayi(S["dord"], 1), chg(rel(S["dord"], C["dord"]), hD)) +
    kart("Ort. sepet adedi", ui.sayi(S["b"], 1) + " adet", chg(rel(S["b"], C["b"]), hN), "Günlük ort.",
         ui.sayi(S["dbq"], 1) + " adet", chg(rel(S["dbq"], C["dbq"]), hD)) +
    kart("Ort. sepet tutarı", ui.sayi(S["basket"], 1) + " ₺", chg(rel(S["basket"], C["basket"]), hN), "Günlük ort.",
         ui.sayi(S["dbt"], 1) + " ₺", chg(rel(S["dbt"], C["dbt"]), hD)) +
    kart("İndirim oranı", "%" + ui.sayi(S["disc"] * 100, 1), chg_p(S["disc"] - C["disc"], hN), "Günlük ort.",
         "%" + ui.sayi(S["dd"] * 100, 1), chg_p(S["dd"] - C["dd"], hD), sari=True) +
    "</div><p class='sub'>Aralıklar eşit uzunlukta olursa (ör. 10 gün – 10 gün) vurgu nominal değerlere geçer. "
    "Aralıklar farklıysa (ör. 10 gün – 1 ay) günlük ortalamalar kıyaslanır.</p>", unsafe_allow_html=True)

# ---------- 1. Günlük ciro neden değişti? ----------
ef = [v / 1000 for v in an.kopru(S, C)]
adlar = ["Sipariş sayısı", "Sepet adedi", "Ürün karması", "İndirim"]
altlar = [f"günlük sipariş {ui.sayi(C['dord'], 1)} → {ui.sayi(S['dord'], 1)}",
          f"sepette {ui.sayi(C['b'], 1)} → {ui.sayi(S['b'], 1)} adet",
          f"ort. liste fiyat {ui.sayi(C['L'], 2)} → {ui.sayi(S['L'], 2)} ₺",
          f"indirim %{ui.sayi(C['disc'] * 100, 1)} → %{ui.sayi(S['disc'] * 100, 1)}"]
dch = rel(S["dnet"], C["dnet"])
dom = int(np.argmax([abs(v) for v in ef]))
with st.container(border=True):
    h1, h2 = st.columns([3, 2])
    with h1:
        ui.bolum(1, "Günlük ciro neden değişti?", "Seçili dönem ile karşılaştırma dönemi arasındaki günlük ciro farkı, dört nedene bölündü")
    with h2:
        st.markdown(f"<div style='text-align:right;padding-top:6px'><span class='pill'>{ui.sayi(C['dnet'] / 1000, 1)} bin ₺</span> → "
                    f"<span class='pill g'>{ui.sayi(S['dnet'] / 1000, 1)} bin ₺</span> "
                    f"<span class='chg {'neg' if dch < 0 else 'pos'}'>{pct(dch)}</span></div>", unsafe_allow_html=True)
    s1, s2 = st.columns([3, 2])
    with s1:
        fig = go.Figure(go.Bar(
            y=[f"{n}<br><span style='font-size:10px;color:#5b6475'>{s}</span>" for n, s in zip(adlar, altlar)],
            x=ef, orientation="h", marker_color=[ui.RENK["kirmizi"] if v < 0 else ui.RENK["yesil"] for v in ef],
            text=[f"{ui.isaret(v, 1)} bin ₺" for v in ef], textposition="outside", cliponaxis=False,
            hovertemplate="%{y}: %{text} günlük ciro etkisi<extra></extra>"))
        fig.update_yaxes(autorange="reversed")
        mxa = max([abs(v) for v in ef] + [1])
        fig.update_xaxes(zeroline=True, zerolinecolor="#9aa3b2", showgrid=False, showticklabels=False,
                         range=[-mxa * 1.45, mxa * 0.45 if min(ef) < 0 and max(ef) <= 0 else mxa * 1.45])
        fig.update_yaxes(automargin=True)
        fig.update_layout(height=300, margin=dict(l=10, r=10, t=6, b=0), plot_bgcolor="white")
        st.plotly_chart(fig, use_container_width=True)
    with s2:
        yil_hizi = tum["net"].sum() / ((tum["gun"].max() - tum["gun"].min()).days + 1)
        st.markdown(f"<div class='out'><div class='t'>Bu hızla sürerse (30 gün)</div><div class='v'>{ui.sayi(S['dnet'] * 30 / 1e6, 2)} M ₺</div>"
                    f"<div class='t'>veri ortalaması hızı: {ui.sayi(yil_hizi * 30 / 1e6, 2)} M ₺ · tahmin değil, hız çarpımı</div></div>",
                    unsafe_allow_html=True)
        if dom == 3:
            b1 = f"**İndirim en büyük etki.** Günlük ciroda {ui.isaret(ef[3], 1)} bin ₺ fark yarattı; indirimi hedefli kullan (bkz. 2)."
        elif dom == 2:
            b1 = f"**Ürün karmasına bak.** Satılan ürünlerin liste fiyatı değişti ({ui.isaret(ef[2], 1)} bin ₺)."
        else:
            b1 = (f"**{'İndirimi artırma.' if dch < 0 else 'Fiyat disiplinini koru.'}** Değişim fiyattan değil hacimden: "
                  f"indirim etkisi {ui.isaret(ef[3], 1)} bin ₺.")
        st.markdown("**Ne yapmalı?**")
        st.markdown(f"1. {b1}\n2. **Sipariş sıklığını artır.** Pasif C müşterilerini aktifleştir (bkz. 6 ve 7).\n"
                    "3. **Sepeti büyüt.** Birlikte al önerisini sipariş ekranına koy (bkz. 4).")

# ---------- 2. İndirim planı ----------
urunler = an.urun_listesi(tum, 50)
with st.container(border=True):
    ui.bolum(2, "İndirim planı", f"Hedefler seçili dönem için ({et(a, b)}, {S['gun']} gün). Karşılaştırma dönemi: {et(ca, cb)}")
    pl, pr = st.columns([3, 2])
    with pl:
        urun = st.selectbox("Ürün", urunler, key="plan_urun")
        P = an.urun_referans(tum, urun, S["gun"], ca, cb)
        Qr, Nr, Gr = P["q"], P["n"], P["g"]
        L = Gr / Qr if Qr else 0
        d0 = 1 - Nr / Gr if Gr else 0
        dq = st.slider(f"Hedef satış (adet) · karşılaştırma: {ui.sayi(Qr)}", -50, 100, 10, format="%d%%", key="plan_q")
        dc = st.slider(f"Hedef ciro (₺) · karşılaştırma: {ui.sayi(Nr)}", -50, 100, 5, format="%d%%", key="plan_c")
        cp = st.slider("Alış maliyeti (liste fiyatın yüzdesi)", 0, 100, 44, format="%d%%", key="plan_m",
                       help="Veride maliyet yok; bu ürünün maliyetini biliyorsan değiştir.")
        Cc = cp / 100
        Kr = Nr - Cc * Gr
        dk = st.slider(f"Hedef kâr (₺) · karşılaştırma: {ui.sayi(Kr)}", -50, 100, 0, format="%d%%", key="plan_k")
        st.caption(f"Liste fiyatı {ui.sayi(L, 2)} ₺ · hedef satış {ui.sayi(Qr * (1 + dq / 100))} adet · "
                   f"hedef ciro {ui.sayi(Nr * (1 + dc / 100))} ₺ · hedef kâr {ui.sayi(Kr * (1 + dk / 100))} ₺")
    tq, tc, tk = Qr * (1 + dq / 100), Nr * (1 + dc / 100), Kr * (1 + dk / 100)
    yeni = 1 - (tc / tq) / L if tq > 0 and L > 0 else 0
    kar = tc - Cc * L * tq
    nedenler = []
    if yeni > P["cap"] + 0.0005:
        nedenler.append("Gereken indirim ürünün yıl içinde yaygın üst sınırını aşıyor.")
    if kar < tk - 0.5:
        nedenler.append("Bu fiyat ve adetle kâr hedefi tutmuyor.")
    tamam = not nedenler
    with pr:
        c1, c2, c3 = st.columns(3)
        c1.markdown(f"<div class='out'><div class='t'>Gereken indirim</div><div class='v'>%{ui.sayi(yeni * 100, 1)}</div></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='out'><div class='t'>Karşılaştırma dönemi</div><div class='v'>%{ui.sayi(d0 * 100, 1)}</div></div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='out'><div class='t'>Fark</div><div class='v'>{ui.isaret((yeni - d0) * 100, 1)} puan</div></div>", unsafe_allow_html=True)
        durum = ("<span class='pill g'><b>ULAŞILABİLİR</b></span>" if tamam else
                 "<span class='pill' style='background:#e0a526'><b>HEDEF ZOR</b></span>")
        st.markdown(f"{durum} {'Hedefler birlikte tutuyor.' if tamam else ' '.join(nedenler)}", unsafe_allow_html=True)
        st.markdown(f"Bu hedefte tahmini kâr: **{ui.sayi(kar)} ₺** (hedef: {ui.sayi(tk)} ₺). Ürün yıl içinde satışlarının "
                    f"%95'ini en fazla %{ui.sayi(P['cap'] * 100)} indirimle yaptı, en yüksek indirim %{ui.sayi(P['mx'] * 100)}.")
        if P["fb"]:
            st.caption("Karşılaştırma döneminde bu ürün satılmamış; referans olarak veri ortalaması günlük hız kullanıldı. "
                       "İndirim = 1 − (hedef ciro ÷ hedef adet) ÷ liste fiyatı.")
        else:
            st.caption(f"Karşılaştırma dönemi {C['gun']} gün, seçili dönem {S['gun']} gün: karşılaştırma değerleri günlük ortalamayla "
                       f"{S['gun']} güne çevrildi. İndirim = 1 − (hedef ciro ÷ hedef adet) ÷ liste fiyatı.")

# ---------- 3. Haftanın günü × kategori ----------
mr = an.araliga_kes(m, a, b)
with st.container(border=True):
    t1, t2 = st.columns([3, 1])
    with t1:
        ui.bolum(3, "Haftanın günü × kategori", "Her kategorinin cirosunun günlere dağılımı (%) · en çok satan 6 kategori")
    with t2:
        gos = st.selectbox("Gösterim", ["Ciro payı", "Sipariş adedi"], key="hk_gos")
    hk = an.hafta_kategori(mr)[gos] if not mr.empty else pd.DataFrame()
    if hk.empty:
        st.info("Bu aralıkta satış yok.")
        gun_cum = ""
    else:
        mx = float(hk.values.max())
        satir = [[f"<td style='text-align:left'>{k}</td>"] + [
            f"<td style='text-align:center;{isi_rengi(v, mx)}'>{ui.sayi(v, 1)}</td>" for v in hk.loc[k].values] for k in hk.index]
        st.markdown("<table class='t'><thead><tr><th>Kategori</th>" + "".join(f"<th style='text-align:center'>{g}</th>" for g in GUNLER) +
                    "</tr></thead><tbody>" + "".join("<tr>" + "".join(r) + "</tr>" for r in satir) + "</tbody></table>", unsafe_allow_html=True)
        dow = mr.groupby("dow")["net"].sum().reindex(range(7), fill_value=0)
        pay = dow / dow.sum() * 100
        en = np.unravel_index(np.argmax(hk.values), hk.shape)
        en_gun = ["pazartesiye", "salıya", "çarşambaya", "perşembeye", "cumaya", "cumartesiye", "pazara"][en[1]]
        gun_cum = (f"Cironun %{ui.sayi(pay.max(), 0)}'i {['pazartesi', 'salı', 'çarşamba', 'perşembe', 'cuma', 'cumartesi', 'pazar'][int(pay.idxmax())]} günü, "
                   f"%{ui.sayi(pay[5] + pay[6], 1)}'si hafta sonu. {hk.index[en[0]]} {en_gun} yığılmış (%{ui.sayi(hk.values[en], 1)}). "
                   "Veride saat bilgisi yok, yalnız gün var.")
        st.caption(gun_cum)

# ---------- 4. Birlikte alınanlar ----------
cift, cok = c_birlikte(m, fk, a, b)
yil = pd.Timestamp(b).year
cift_yil = c_birlikte_yil(m, fk, yil)
with st.container(border=True):
    ui.bolum(4, "Birlikte alınanlar ve en çok satanlar", "Aynı siparişte en sık birlikte geçen ürün çiftleri · seçilen tarih aralığı ve yıl")
    k1, k2 = st.columns(2)
    for kol, bas, alt, liste in ((k1, "Seçilen tarih", et(a, b), cift), (k2, "Tüm yıl", f"Seçilen tarihin yılı: {yil}", cift_yil)):
        with kol, st.container(border=True):
            st.markdown(f"**{bas}**")
            st.caption(alt)
            if not liste:
                st.write("Çift bulunamadı.")
            if liste:
                st.markdown("<ol class='lst'>" + "".join(
                    f"<li><b>{c['a']} + {c['b']}</b><br><small>{c['n']} sipariş · %{ui.sayi(c['oran'] * 100, 0)}</small></li>"
                    for c in liste) + "</ol>", unsafe_allow_html=True)
    st.markdown(f"**Seçilen tarihte best seller'lar ve en çok birlikte alındıkları ürün · {et(a, b)}**")
    if cok.empty:
        st.info("Bu aralıkta satış yok.")
    else:
        g = cok.copy()
        g["Birlikte alma oranı"] = g["Birlikte alma oranı"].map(lambda v: f"%{ui.sayi(v * 100, 0)}")
        g["#"] = g["#"].astype(str)
        g["Adet"] = g["Adet"].map(ui.sayi)
        st.dataframe(g, hide_index=True, use_container_width=True)
    st.caption("Birlikte alma oranı: best seller'ı alan siparişlerin yüzde kaçında bu ürün de var. "
               "Sepette best seller varsa ikinci ürün öneri olarak gösterilir.")

# ---------- 5-6. Pareto ve kampanya ----------
_sk, _ = st.columns([1, 2])
tur = _sk.selectbox("Segmentasyon türü", ["Müşteri segmentasyonu", "Ürün segmentasyonu"], key="seg_tur")
musteri_mi = tur.startswith("Müşteri")
anahtar = "CustomerID" if musteri_mi else "Description"
birim = "Müşteri" if musteri_mi else "Ürün"
tip = "musteri" if musteri_mi else "urun"
pc = an.pareto(mr, anahtar)
churn, auc = c_churn(tum, vid)
if pc.empty:
    st.info("Bu aralıkta satış yok.")
    st.stop()
n = len(pc)
sayilar = {s: int((pc["seg"] == s).sum()) for s in "ABC"}
paylar = {s: pc.loc[pc["seg"] == s, "net"].sum() / pc["net"].sum() for s in "ABC"}

if musteri_mi:
    ozet_m = an.musteri_ozeti(tum, mr, pc, tum["gun"].max())
    ozet_m = ozet_m.join(churn[["p", "risk"]])
else:
    son_satis = tum.groupby("Description")["gun"].max()
    ozet_m = pc.copy()
    g = mr.groupby("Description").agg(adet=("Quantity", "sum"), brut=("gross", "sum"))
    ozet_m["adet"] = g["adet"]
    ozet_m["indirim"] = 1 - ozet_m["net"] / g["brut"]
    ozet_m["son"] = son_satis.reindex(ozet_m.index)
    ozet_m["pasif"] = (tum["gun"].max() - ozet_m["son"]).dt.days

p5, p6 = st.columns([2, 3])
with p5, st.container(border=True):
    ui.bolum(5, f"{birim} Pareto segmentleri", f"{birim}ler ciro payına göre sıralanıp 3 gruba bölündü: A %80, B %15, C %5")
    x = np.arange(1, n + 1) / n * 100
    fig = go.Figure()
    sinir = [0] + [sayilar["A"] / n * 100, (sayilar["A"] + sayilar["B"]) / n * 100, 100]
    for (x0, x1, renk, ad) in ((sinir[0], sinir[1], "#d6ece5", "A"), (sinir[1], sinir[2], "#fdf0cf", "B"), (sinir[2], sinir[3], "#fbe0d3", "C")):
        fig.add_vrect(x0=x0, x1=x1, fillcolor=renk, line_width=0, layer="below", annotation_text=ad, annotation_position="bottom")
    fig.add_scatter(x=np.r_[0, x], y=np.r_[0, pc["kum"].values * 100], mode="lines", line=dict(color="#1f2a44", width=2),
                    hovertemplate="%{x:.1f}% → %{y:.1f}%<extra></extra>")
    fig.add_scatter(x=[sinir[1]], y=[80], mode="markers+text", marker=dict(color="#c8503f", size=9),
                    text=[f"%{ui.sayi(sinir[1], 1)} → %80"], textposition="middle right")
    fig.update_layout(height=320, showlegend=False, margin=dict(l=0, r=0, t=6, b=0),
                      xaxis_title=f"{birim.lower()} yüzdesi (ciroya göre sıralı)", yaxis_title="kümülatif ciro %",
                      xaxis_range=[0, 100], yaxis_range=[0, 105], plot_bgcolor="white")
    st.plotly_chart(fig, use_container_width=True)

with p6, st.container(border=True):
    ui.bolum(6, f"Segmente özel kampanya önerisi" if musteri_mi else "Ürüne özel kampanya önerisi",
             "Her segment için ayrı hedef ve aksiyon · kampanya fikirleri A/B testle doğrulanmalı")
    satirlar = []
    for s in "ABC":
        z = ozet_m[ozet_m["seg"] == s]
        if musteri_mi:
            beh = f"Medyan {ui.sayi(z['siparis'].median(), 0)} sipariş, %{ui.sayi((z['pasif'] > 90).mean() * 100, 0)}'si 90+ gün pasif"
            if s == "C":
                beh += f" · müşteri başı ≈ {ui.sayi(z['net'].mean(), 0)} ₺"
        else:
            beh = (f"Ürün başı ≈ {ui.sayi(z['net'].mean(), 0)} ₺, ort. indirim %{ui.sayi(z['indirim'].mean() * 100, 1)}, "
                   f"%{ui.sayi((z['pasif'] > 120).mean() * 100, 0)}'i 120+ gündür satılmıyor")
        bg, fg = SEG_RENK[s]
        lead, rest = KAMPANYA[tip][s]
        satirlar.append([f"<span class='pill' style='background:{bg};color:{fg}'>{SEG_AD[s]}</span>", ui.sayi(sayilar[s]),
                         f"%{ui.sayi(paylar[s] * 100, 1)}", beh, f"<b>{lead}</b> {rest}"])
    st.markdown(tablo(["Segment", birim, "Ciro payı", "Davranış", "Önerilen kampanya"], satirlar, sag=(1, 2)), unsafe_allow_html=True)
    if musteri_mi:
        ex = pd.DataFrame({
            "Müşteri no": ozet_m.index, "Segment": ozet_m["seg"].map(SEG_AD).values, "İl": ozet_m["il"].values,
            "Sipariş sayısı": ozet_m["siparis"].values, "Son sipariş": ozet_m["son"].dt.strftime("%d.%m.%Y").values,
            "Kaç gündür sipariş yok": ozet_m["pasif"].values, "Churn riski": ozet_m["risk"].astype(str).values,
            "Net ciro (₺)": ozet_m["net"].round(0).values,
            "Önerilen kampanya": [" ".join(KAMPANYA["musteri"][s]) for s in ozet_m["seg"]]})
    else:
        ex = pd.DataFrame({
            "Ürün adı": ozet_m.index, "Segment": ozet_m["seg"].map(SEG_AD).values, "Satılan adet": ozet_m["adet"].values,
            "İndirim oranı": ozet_m["indirim"].round(3).values, "Son satış günü": ozet_m["son"].dt.strftime("%d.%m.%Y").values,
            "Net ciro (₺)": ozet_m["net"].round(0).values,
            "Önerilen kampanya": [" ".join(KAMPANYA["urun"][s]) for s in ozet_m["seg"]]})
    st.download_button(f"Excel'e aktar: tüm {birim.lower()}ler", ui.xlsx(ex, birim), file_name=f"{tip}_segmentleri.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary")
    st.caption("Listede her " + ("müşteri için: müşteri no · segment · il · sipariş sayısı · son sipariş · churn riski · önerilen kampanya."
                                 if musteri_mi else "ürün için: ürün adı · segment · satılan adet · indirim oranı · son satış günü · önerilen kampanya."))

# ---------- 7-8. Churn ısı haritası ----------
cm = an.pareto(mr, "CustomerID").join(churn[["p", "risk", "m30"]]).join(
    an.musteri_ozeti(tum, mr, an.pareto(mr, "CustomerID"), tum["gun"].max())[["il", "siparis", "son", "pasif"]])
cm["risk"] = cm["risk"].astype(str)
RISKLER = ["Düşük", "Orta", "Yüksek"]
RK = {"Düşük": "dusuk", "Orta": "orta", "Yüksek": "yuksek"}
ss = st.session_state
ss.setdefault("hm", ("A", "Yüksek"))
css = ""
for (sg, rk), (bg, fg) in HEAT.items():
    sec = ss["hm"] == (sg, rk)
    css += (f".st-key-hm_{sg}_{RK[rk]} button{{background:{bg};color:{fg};border:none;border-radius:6px;min-height:48px;font-weight:700;"
            f"{'outline:3px solid #1f2a44;outline-offset:-3px;' if sec else ''}}}")
st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

h7, h8 = st.columns(2)
with h7, st.container(border=True):
    ui.bolum(7, "Churn risk ısı haritası", "Önümüzdeki 30 günde sipariş vermeme olasılığı · bir kutuya tıkla, sağda o kutudaki müşteriler görünsün")
    bas = st.columns([1.4, 1, 1, 1])
    bas[0].markdown("<span class='sub'>Segment</span>", unsafe_allow_html=True)
    for i, rk in enumerate(RISKLER):
        bas[i + 1].markdown(f"<span class='sub'>{rk} risk</span>", unsafe_allow_html=True)
    for sg in "ABC":
        sat = st.columns([1.4, 1, 1, 1])
        sat[0].markdown(f"<div style='padding-top:10px;font-size:13px'>{SEG_AD[sg]}</div>", unsafe_allow_html=True)
        for i, rk in enumerate(RISKLER):
            adet = int(((cm["seg"] == sg) & (cm["risk"] == rk)).sum())
            if sat[i + 1].button(str(adet), key=f"hm_{sg}_{RK[rk]}", use_container_width=True):
                ss["hm"] = (sg, rk)
                st.rerun()
    toplam_net = cm["net"].sum()
    pills = ""
    for rk in RISKLER:
        z = cm[cm["risk"] == rk]
        pills += f"<span class='pill {RISK_PILL[rk]}'>{rk}: {ui.sayi(len(z))} müşteri · ciro %{ui.sayi(z['net'].sum() / toplam_net * 100, 1)}</span>"
    st.markdown(pills, unsafe_allow_html=True)
    st.caption(f"Gradient Boosting · zaman sıralı testte AUC {ui.sayi(auc, 2) if auc else 'hesaplanamadı'} · risk: yüksek ≥ %70, orta %40–70. "
               "Model tüm veriyle eğitilir, risk veri bitişi itibarıyla hesaplanır.")

sg, rk = ss["hm"]
hucre = cm[(cm["seg"] == sg) & (cm["risk"] == rk)].sort_values("net", ascending=False)
with h8, st.container(border=True):
    ui.bolum(8, f"{sg} · {rk} risk: en yüksek cirolu müşteriler", f"{ui.sayi(len(hucre))} müşteriden ciroya göre ilk 5 · tümü Excel'e iner")
    satirlar = [[i, ui.tl(r["net"]), f"{int(r['pasif']) if pd.notna(r['pasif']) else '—'} gün",
                 f"<span class='pill {RISK_PILL[rk]}'>%{ui.sayi(r['p'] * 100, 0)}</span>"] for i, r in hucre.head(5).iterrows()]
    st.markdown(tablo(["Müşteri", "Ciro", "Son siparişten", "Risk"], satirlar, sag=(1, 2, 3)), unsafe_allow_html=True)
    liste = pd.DataFrame({
        "Müşteri": hucre.index, "İl": hucre["il"].values, "Segment (A-B-C)": sg, "Churn riski": rk,
        "Bırakma olasılığı (%)": (hucre["p"] * 100).round(0).values, "Net ciro (₺)": hucre["net"].round(0).values,
        "Sipariş sayısı": hucre["siparis"].values, "Son sipariş": hucre["son"].dt.strftime("%d.%m.%Y").values,
        "Kaç gündür sipariş yok": hucre["pasif"].values,
        "Önümüzdeki 30 gün beklenen ciro (₺)": hucre["m30"].round(0).values})
    st.download_button(f"Excel'e indir: {sg} · {rk} risk ({ui.sayi(len(hucre))} müşteri)", ui.xlsx(liste, "Müşteriler"),
                       file_name=f"musteriler_{sg}_{RK[rk]}_risk.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary")
    st.caption({"Yüksek": "Öneri: bu müşterilere kişisel arama; C segmentinde otomatik hatırlatma.",
                "Orta": "Öneri: sipariş aralığına göre hatırlatma gönder.",
                "Düşük": "Öneri: düzenli alıyorlar; çapraz satış teklifi uygun."}[rk] + " Ciro: seçili dönem net ciro.")

# ---------- 9. Şüpheli sipariş radarı ----------
with st.container(border=True):
    r1, r2 = st.columns([3, 1])
    with r1:
        ui.bolum(9, "Şüpheli sipariş radarı", "Normal dışı sipariş tespiti · neye göre sapanı seçin, liste ona göre değişir")
    with r2:
        sapma = st.selectbox("Sapma türü", ["İndirime göre sapanlar", "Hacme göre sapanlar"], key="sup_tur")
    tkey = "indirim" if sapma.startswith("İndirim") else "hacim"
    sup, n_ind, kayip = c_supheli(tum, m, fk, a, b, tkey)
    st.markdown(f"<span class='pill r'>{ui.sayi(n_ind)} sipariş-kategoride kategori medyanından 10+ puan fazla indirim</span>"
                f"<span class='pill y'>Toplam fazla indirim ≈ {ui.tl(kayip)}</span>", unsafe_allow_html=True)
    if sup.empty:
        st.info("Bu aralıkta bu türde şüpheli sipariş yok.")
    else:
        if tkey == "indirim":
            tb = pd.DataFrame({"Sipariş": sup["InvoiceNo"], "Müşteri": sup["musteri"], "Kategori": sup["Category"],
                               "İndirim": sup["indirim"].map(lambda v: f"%{ui.sayi(v * 100, 0)}"),
                               "Kategori medyan indirimi": sup["md"].map(lambda v: f"%{ui.sayi(v * 100, 0)}"),
                               "Sapma": sup["sapma"].map(lambda v: f"+{ui.sayi(v * 100, 0)} puan"),
                               "Fazla indirim (₺)": sup["fazla"].round(0)})
        else:
            tb = pd.DataFrame({"Sipariş": sup["InvoiceNo"], "Müşteri": sup["musteri"], "Kategori": sup["Category"],
                               "Adet": sup["q"], "Kategori medyan adedi": sup["mq"].round(0),
                               "Katı": sup["qr"].map(lambda v: f"{ui.sayi(v, 0)}x"), "Net ciro (₺)": sup["n"].round(0)})
        st.dataframe(tb.head(10), hide_index=True, use_container_width=True)
        st.download_button("Excel'e aktar", ui.xlsx(tb, "Şüpheli siparişler"), file_name=f"supheli_siparisler_{tkey}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary")

# ---------- RafBot ----------
yuksek = cm[cm["risk"] == "Yüksek"]
a_yuk = cm[(cm["seg"] == "A") & (cm["risk"] == "Yüksek")]
bilgi = {
    "kopru": (f"Seçili dönemde günlük ciro karşılaştırma dönemine göre {'düştü' if dch < 0 else 'arttı'} (%{ui.sayi(abs(dch) * 100, 1)}; "
              f"{ui.sayi(C['dnet'] / 1000, 1)} → {ui.sayi(S['dnet'] / 1000, 1)} bin ₺). En büyük etki: {adlar[dom]} ({ui.isaret(ef[dom], 1)} bin ₺)."),
    "churn": (f"{ui.sayi(len(yuksek))} müşteri yüksek riskli (30 günde sipariş vermeme olasılığı ≥ %70). A segmentinde {ui.sayi(len(a_yuk))} "
              f"yüksek riskli müşteri var; önce bunları ara" + (f" ({', '.join(map(str, a_yuk.sort_values('net', ascending=False).head(3).index))})." if len(a_yuk) else ".")),
    "segment": (f"Müşteriler ciroya göre üç gruba ayrıldı: A {ui.sayi(sayilar['A'])} (cironun %{ui.sayi(paylar['A'] * 100, 0)}'i), "
                f"B {ui.sayi(sayilar['B'])} (%{ui.sayi(paylar['B'] * 100, 0)}), C {ui.sayi(sayilar['C'])} (%{ui.sayi(paylar['C'] * 100, 0)})."
                if musteri_mi else f"Ürünler üç gruba ayrıldı: A {ui.sayi(sayilar['A'])}, B {ui.sayi(sayilar['B'])}, C {ui.sayi(sayilar['C'])} ürün."),
    "indirim": (f"Seçili dönemde ağırlıklı indirim oranı %{ui.sayi(S['disc'] * 100, 1)}. {ui.sayi(n_ind)} sipariş-kategoride kategori medyanından "
                f"10+ puan fazla indirim verilmiş; toplam fazlası ≈ {ui.tl(kayip)}."),
    "birlikte": (f"En sık birlikte alınan çift {cift[0]['a']} + {cift[0]['b']} ({cift[0]['n']} sipariş). Ortalama sepet "
                 f"{ui.sayi(S['basket'], 1)} ₺ ve {ui.sayi(S['b'], 1)} adet.") if cift else None,
    "gun": gun_cum or None,
    "ciro": (f"Seçili {et(a, b)} döneminde net ciro {ui.sayi(S['net'] / 1e6, 2)} M ₺, günlük {ui.sayi(S['dnet'] / 1000, 1)} bin ₺; "
             f"{ui.sayi(S['ord'])} sipariş."),
}
chat.rafbot(bilgi)
