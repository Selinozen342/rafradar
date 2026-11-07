"""Tedarik Zinciri sayfası. HTML taslağındaki 7 panelin aynısı, veriden canlı hesaplanır."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from common import analytics as an
from common import analytics2 as an2
from common import chat, data, ui
from common import widgets as w


@st.cache_data(show_spinner="Ürün sınıfları hesaplanıyor…")
def c_abc(_tum, vid):
    return an2.abc_xyz(_tum)


@st.cache_data(show_spinner=False)
def c_hafta(_tum, vid, urun):
    wk, gunluk = an2.haftalik(_tum, urun)
    sonuc, en = an2.geri_test(wk)
    return wk, gunluk, sonuc, en


@st.cache_data(show_spinner=False)
def c_satissiz(_tum, vid):
    return an2.satissiz(_tum)


tum = data.veri()
vid = (st.session_state.get("dosya_adi", ""), len(tum))
ui.baslik("Tedarik Zinciri", "Ne kadar stok tutmalı, ne zaman sipariş vermeli?")
m, a, b, ca, cb = ui.filtreler(tum)
K = w.fk()
if m.empty:
    st.warning("Bu filtrelerle veri yok. Filtreleri gevşetip tekrar dene.")
    st.stop()
et = ui.tarih_etiketi
S, C = w.ozet_c(m, K, a, b), w.ozet_c(m, K, ca, cb)
hN, hD = S["gun"] == C["gun"], S["gun"] != C["gun"]
AV = "#3b6fd1"

st.markdown(w.ust_bilgi(S, C, a, b, ca, cb), unsafe_allow_html=True)
w.kgrid([
    w.kart("Satılan adet", ui.sayi(S["q"] / 1000, 1) + " bin", w.chg(w.rel(S["q"], C["q"]), hN), "Günlük ort.", ui.sayi(S["dq"]) + " adet", w.chg(w.rel(S["dq"], C["dq"]), hD), AV),
    w.kart("Sipariş adedi", ui.sayi(S["ord"]), w.chg(w.rel(S["ord"], C["ord"]), hN), "Günlük ort.", ui.sayi(S["dord"], 1), w.chg(w.rel(S["dord"], C["dord"]), hD), AV),
    w.kart("Ort. sepet adedi", ui.sayi(S["b"], 1) + " adet", w.chg(w.rel(S["b"], C["b"]), hN), "Günlük ort.", ui.sayi(S["dbq"], 1) + " adet", w.chg(w.rel(S["dbq"], C["dbq"]), hD), AV),
    w.kart("Aktif müşteri", ui.sayi(S["musteri"]), w.chg(w.rel(S["musteri"], C["musteri"]), hN), "Günlük ort.", ui.sayi(S["dcust"], 1), w.chg(w.rel(S["dcust"], C["dcust"]), hD), AV),
    w.kart("Net ciro", ui.sayi(S["net"] / 1e6, 2) + " M ₺", w.chg(w.rel(S["net"], C["net"]), hN), "Günlük ort.", ui.sayi(S["dnet"] / 1000, 1) + " bin ₺", w.chg(w.rel(S["dnet"], C["dnet"]), hD), "#e0a526"),
])
bit = tum["gun"].max()
w.not_kutusu(f"Üstteki göstergeler seçtiğin tarihlere göre hesaplanır. Paneller verinin son gününe ({et(bit, bit)}) ve tüm veriye göre hazırlandı.")

qadet, kum, abc, xyz = c_abc(tum, vid)
nprod = len(qadet)
cnt = {k: int((abc == k).sum()) for k in "ABC"}
a_pay = cnt["A"] / nprod * 100

# ---------- 1-2 ----------
p1, p2 = st.columns([1.2, 1])
with p1, st.container(border=True):
    ui.bolum(1, "Adedin %80’ini hangi ürünler getiriyor?", "Ürünler satılan adede göre sıralandı")
    w.vurgu(f"Ürünlerin %{ui.sayi(a_pay, 0)}’i ({ui.sayi(cnt['A'])} ürün) satılan adedin %80’ini oluşturuyor.")
    x = np.arange(1, nprod + 1) / nprod * 100
    ix = np.unique(np.linspace(0, nprod - 1, 300).astype(int))
    bx = (cnt["A"] + cnt["B"]) / nprod * 100
    fig = go.Figure()
    for x0, x1, rn in ((0, a_pay, "#d6ece5"), (a_pay, bx, "#fdf0cf")):
        fig.add_vrect(x0=x0, x1=x1, fillcolor=rn, line_width=0, layer="below")
    fig.add_hline(y=80, line_dash="dot", line_color=ui.RENK["yesil"])
    fig.add_scatter(x=np.r_[0, x[ix]], y=np.r_[0, kum.values[ix] * 100], mode="lines", line=dict(color="#1f2a44", width=2.5),
                    hovertemplate="%{x:.1f}% ürün → %{y:.1f}% adet<extra></extra>")
    fig.add_annotation(x=a_pay, y=80, text=f"A: ürünlerin %{ui.sayi(a_pay, 1)}’i", showarrow=False, xanchor="left", yanchor="top", xshift=6, yshift=-6)
    fig.update_layout(height=300, showlegend=False, margin=dict(l=0, r=0, t=6, b=0), plot_bgcolor="white",
                      xaxis=dict(title="ürünler, adedi en yüksekten düşüğe sıralı (%)", range=[0, 100]),
                      yaxis=dict(title="birikimli adet payı (%)", range=[0, 102]))
    st.plotly_chart(fig, use_container_width=True)
    st.markdown(f"<span class='pill g'>A · {ui.sayi(cnt['A'])} ürün · adetin %80’i</span><span class='pill y'>B · {ui.sayi(cnt['B'])} ürün · %15</span>"
                f"<span class='pill'>C · {ui.sayi(cnt['C'])} ürün · %5</span>", unsafe_allow_html=True)
cls = abc + xyz
toplam_q = qadet.sum()
hucre = {k: (int((cls == k).sum()), float(qadet[cls == k].sum() / toplam_q * 100)) for k in an2.POLITIKA}
with p2, st.container(border=True):
    ui.bolum(2, "Hangi ürünün talebi düzensiz?", "Satış hacmi (A-B-C) ve aylık satışın oynaklığı (X-Y-Z)")
    w.vurgu(f"A ürünlerinin {ui.sayi(hucre['AZ'][0])} tanesi düzensiz: adedin %{ui.sayi(hucre['AZ'][1], 0)}’i stok sürprizi riski taşıyor.")
    mxu = max(v[1] for v in hucre.values()) or 1
    g = "<div style='display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px'>"
    for k, (n, u) in hucre.items():
        t = min(1, u / mxu)
        g += (f"<div style='background:{w.mix('#e8f2ef', '#2f8a73', t ** 0.5)};color:{'#fff' if t > 0.45 else '#1f2a44'};border-radius:8px;padding:8px 10px;min-height:78px'>"
              f"<div style='font-size:12px;font-weight:700'>{k}</div><div style='font-size:11px'>{ui.sayi(n)} ürün</div><div style='font-size:11px'>adetin %{ui.sayi(u, 1)}’i</div>"
              f"<div style='font-size:11px;font-weight:600;margin-top:2px'>{an2.POLITIKA[k]}</div></div>")
    st.markdown(g + "</div>", unsafe_allow_html=True)
    st.caption("Düzenli: aylık satışın dalgalanması düşük. Dalgalı: orta. Düzensiz: çok yüksek (bir ay çok, bir ay hiç).")

# ---------- 3. Talep tahmini ----------
top12 = qadet.head(12).index.tolist()
with st.container(border=True):
    ui.bolum(3, "Önümüzdeki 8 haftada ne kadar talep bekleniyor?", "Ürünü seç; üç basit yöntem son 12 haftada denendi, hatası en düşük olan seçildi")
    urun = st.selectbox("Ürün", top12, format_func=lambda s: s if len(s) < 50 else s[:50] + "…", key="ted_urun")
    wk, gunluk, sonuc, en = c_hafta(tum, vid, urun)
    best = sonuc[en]
    f8 = best["f"](wk, 8)
    sum8, last8 = sum(f8), float(wk[-8:].sum())
    w.vurgu(f"{urun if len(urun) < 50 else urun[:50] + '…'}: {ui.sayi(sum8)} adet, son 8 haftadan " +
            (f"%{ui.sayi((sum8 / max(1, last8) - 1) * 100, 0)} fazla." if sum8 >= last8 else f"%{ui.sayi((1 - sum8 / max(1, last8)) * 100, 0)} az."))
    cols = st.columns(3)
    for i, (kol, r) in enumerate(zip(cols, sonuc)):
        on = i == en
        kol.markdown(f"<div style='border:1px solid {'#3d9a84' if on else '#e4dfd6'};background:{'#eaf4f0' if on else '#fff'};border-radius:10px;padding:8px 10px'>"
                     f"<div style='font-size:12px'>{r['ad']}</div><div style='font-size:13px;font-weight:700'>Hata %{ui.sayi(r['wape'] * 100, 1)}</div>"
                     + ("<div style='font-size:11px;color:#14513f;font-weight:600'>✓ seçilen</div>" if on else "") + "</div>", unsafe_allow_html=True)
    hist = wk[-26:]
    n = len(hist)
    hh = np.arange(n)
    e = [1.28 * best["sd"] * np.sqrt(k + 1) for k in range(8)]
    up = [v + x for v, x in zip(f8, e)]
    lo = [max(0, v - x) for v, x in zip(f8, e)]
    fig = go.Figure()
    fig.add_vrect(x0=n - 12, x1=n - 1, fillcolor="#efeae0", line_width=0, layer="below", annotation_text="test dönemi", annotation_position="top")
    fig.add_scatter(x=np.r_[np.arange(n, n + 8), np.arange(n + 7, n - 1, -1)], y=np.r_[up, lo[::-1]], fill="toself",
                    fillcolor="rgba(159,207,194,.55)", line=dict(width=0), hoverinfo="skip", name="olası aralık")
    fig.add_scatter(x=hh, y=hist, mode="lines", line=dict(color="#1f2a44", width=2), name="gerçek haftalık adet")
    fig.add_scatter(x=np.arange(n - 12, n), y=best["fcs"], mode="lines", line=dict(color="#3d9a84", width=1.5, dash="dash"), name="test tahmini")
    fig.add_scatter(x=np.r_[n - 1, np.arange(n, n + 8)], y=np.r_[hist[-1], f8], mode="lines", line=dict(color="#3d9a84", width=2.5, dash="dash"), name="tahmin")
    fig.add_vline(x=n - 1, line_dash="dot", line_color="#1f2a44")
    fig.update_layout(height=320, margin=dict(l=0, r=0, t=10, b=0), plot_bgcolor="white", legend=dict(orientation="h", y=-0.15),
                      xaxis=dict(showticklabels=False, title="26 hafta önce → son hafta → +8 hafta"), yaxis=dict(title="haftalık adet", rangemode="tozero"))
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Hata %: 4 haftalık toplam talepte, tahmin ile gerçek arasındaki farkların toplamı ÷ gerçek toplam (son 12 deneme). Düşük olan iyi. "
               "Veri tek yıl olduğu için mevsimsel yöntemler denenmedi.")

# ---------- 4. Güvenlik stoğu ----------
with st.container(border=True):
    ui.bolum(4, "Ne kadar güvenlik stoğu tutmalı?", "Aynı ürün için tedarik süresini ve hizmet seviyesini değiştir")
    s1, s2 = st.columns([1, 1.2])
    with s1:
        lt = st.slider("Tedarik süresi (hafta)", 1, 6, 2, key="ted_lt")
        sl = st.slider("Hizmet seviyesi (%)", 85, 99, 95, key="ted_sl")
        st.caption("Hizmet seviyesi: talebin stoktan karşılanma olasılığı. Güvenlik stoğu = z × haftalık sapma × √tedarik süresi. "
                   "Sipariş noktası = haftalık talep × süre + güvenlik stoğu.")
    stk = an2.stok(wk, gunluk, lt, sl)
    with s2:
        c = st.columns(2)
        for kol, (t, v, alt) in zip(c * 2, [("Güvenlik stoğu", f"{ui.sayi(stk['ss'])} adet", ""), ("Sipariş noktası", f"{ui.sayi(stk['rop'])} adet", "stok bu seviyeye inince sipariş ver"),
                                            ("Haftalık talep", f"{ui.sayi(stk['mu'])} adet", "son 26 hafta ortalaması"),
                                            ("Stoksuz gün", f"{stk['out']} / {stk['n']}", "son 26 haftayı bu kuralla oynatınca")]):
            kol.markdown(f"<div class='out'><div class='t'>{t}</div><div class='v'>{v}</div><div class='t'>{alt}</div></div><div style='height:6px'></div>", unsafe_allow_html=True)
    fig = go.Figure()
    d = np.arange(stk["n"])
    fig.add_hrect(y0=0, y1=stk["ss"], fillcolor="#fdf0cf", line_width=0, layer="below", annotation_text="güvenlik stoğu", annotation_position="top left")
    for dd in stk["outd"]:
        fig.add_vrect(x0=dd - 0.5, x1=dd + 0.5, fillcolor="rgba(208,87,79,.45)", line_width=0, layer="below")
    fig.add_scatter(x=d, y=stk["ser"], mode="lines", line=dict(color="#3d9a84", width=2), name="stok")
    fig.add_hline(y=stk["rop"], line_dash="dash", line_color="#1f2a44", annotation_text="sipariş noktası", annotation_position="top right")
    fig.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0), plot_bgcolor="white", showlegend=False,
                      xaxis=dict(showticklabels=False, title="26 hafta önce → son hafta"), yaxis=dict(title="stok (adet)", rangemode="tozero"))
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Oynatma varsayımı: sipariş miktarı 4 haftalık talep, tedarik süresi sabit. Stok verisi olmadığı için gerçek stok değil, satış geçmişi kullanıldı. "
               "Kırmızı çizgiler stoksuz günleri gösterir.")

# ---------- 5. Mevsimsellik ----------
cats, SM, yil = an2.mevsimsellik(tum)
with st.container(border=True):
    ui.bolum(5, "Hangi ay hangi kategori güçlü?", f"Kategorinin aylık satılan adedi ÷ kendi aylık ortalaması · 100 = ortalama · {yil}")
    if len(cats):
        bs = max(((v, i, j) for i, r in enumerate(SM) for j, v in enumerate(r)), default=(0, 0, 0))
        w.vurgu(f"{cats[bs[1]]} talebi {w.AY_AD[bs[2]]} ayında ortalamanın {ui.sayi(bs[0] / 100, 1)} katına çıkıyor.")
        st.markdown(w.sapma_tablo(cats, ui.AYLAR, SM), unsafe_allow_html=True)

# ---------- 6. Satışsız ürünler ----------
ds = c_satissiz(tum, vid)
bk = [(0, 30), (31, 90), (91, 180), (181, 10000)]
bs_ad = ["0–30 gün", "31–90 gün", "91–180 gün", "181+ gün"]
bs_n = [int(((ds["gun"] >= x) & (ds["gun"] <= y)).sum()) for x, y in bk]
bs_r = ["#3d9a84", "#8bbf7a", "#e0a526", "#d0574f"]
idle120 = int((ds["gun"] >= 120).sum())
with st.container(border=True):
    ui.bolum(6, "Hangi ürünler uzun süredir satılmıyor?", f"Ürünlerin son satıştan bu yana geçen gün sayısı · {et(bit, bit)} itibarıyla")
    st.markdown(f"<div style='padding:10px 12px;border-radius:10px;background:#fdf0cf;color:#5c4200;font-size:13px;font-weight:600;line-height:1.4'>Uyarı: {ui.sayi(idle120)} ürün 120 günden uzun süredir "
                f"satılmadı (toplam {ui.sayi(len(ds))} üründen). Stokta varsa eritme kampanyası veya iade konuşulmalı.</div>", unsafe_allow_html=True)
    mx = max(bs_n) or 1
    st.markdown("".join(f"<div style='display:grid;grid-template-columns:80px minmax(0,1fr) 60px;gap:8px;align-items:center;padding:4px 0;font-size:12px'><span>{bs_ad[i]}</span>"
                        f"<div style='height:18px;background:#f0ebe2;border-radius:4px'><div style='width:{v / mx * 100:.1f}%;height:100%;background:{bs_r[i]};border-radius:4px'></div></div>"
                        f"<span style='text-align:right;font-weight:600'>{ui.sayi(v)}</span></div>" for i, v in enumerate(bs_n)), unsafe_allow_html=True)
    esik = st.selectbox("Liste", [120, 180, 270], format_func=lambda x: f"{x}+ gün", key="ted_idle")
    lst = ds[ds["gun"] >= esik].sort_values("gun", ascending=False)
    ex = pd.DataFrame({"Ürün": lst.index, "Kategori": lst["kategori"].values, "Kaç gündür satılmadı": lst["gun"].values,
                       "Toplam adet": lst["adet"].values, "Toplam net ciro (₺)": lst["net"].round(0).values})
    st.download_button(f"Excel’e indir: satışsız ürün listesi · {ui.sayi(len(ex))} ürün · {esik}+ gün", ui.xlsx(ex, "Satışsız ürünler"),
                       file_name=f"satissiz_urunler_{esik}_gun.xlsx", mime=w.XLSX, type="primary")

# ---------- 7. Stok planı ----------
with st.container(border=True):
    ui.bolum(7, "En çok satan 12 ürün için stok planı", f"Tedarik süresi {lt} hafta, hizmet seviyesi %{sl} ile önerilen stok · yukarıdaki ayarlarla değişir")
    satir, stil = [], []
    for u in top12:
        wk_u, gk_u, sn_u, en_u = c_hafta(tum, vid, u)
        f4 = sum(sn_u[en_u]["f"](wk_u, 4))
        k = an2.stok(wk_u, gk_u, lt, sl)
        hata = sn_u[en_u]["wape"]
        sinif = cls[u]
        satir.append([u if len(u) < 40 else u[:40] + "…", f"<span class='pill g'>{sinif}</span>", ui.sayi(f4),
                      f"<span style='color:{'#8f2a24' if hata > 0.2 else '#14513f'};font-weight:600'>%{ui.sayi(hata * 100, 1)}</span>",
                      ui.sayi(k["ss"]), ui.sayi(k["rop"]), an2.POLITIKA[sinif]])
        stil.append("background:#eaf4f0" if u == urun else "")
    st.markdown(w.tablo(["Ürün", "Sınıf", "4 haftalık talep", "Hata %", "Güvenlik stoğu", "Sipariş noktası", "İzlenecek politika"], satir, sag=(2, 3, 4, 5), stil=stil), unsafe_allow_html=True)
    st.caption("Hata %’si 20’nin üstündeyse (kırmızı) tahmine fazla güvenme, siparişe göre tedarik daha güvenli.")

# ---------- RafBot ----------
bilgi = {
    "ciro": f"Seçili {et(a, b)} döneminde {ui.sayi(S['q'])} adet satıldı, günlük {ui.sayi(S['dq'])} adet.",
    "indirim": f"{urun} için {lt} hafta tedarik süresi ve %{sl} hizmet seviyesiyle güvenlik stoğu ≈ {ui.sayi(stk['ss'])}, sipariş noktası ≈ {ui.sayi(stk['rop'])} adet.",
    "churn": f"{ui.sayi(idle120)} ürün 120+ gündür satılmadı; {ui.sayi(bs_n[3])} ürün 181+ gündür. Listeyi 6. panelden Excel’e alabilirsin.",
    "kopru": f"{urun} için en iyi yöntem “{best['ad']}” (hata %{ui.sayi(best['wape'] * 100, 1)}). Önümüzdeki 8 haftada ≈ {ui.sayi(sum8)} adet bekleniyor.",
    "segment": f"Ürünlerin %{ui.sayi(a_pay, 1)}’i adedin %80’ini getiriyor (A). A ürünlerinin {ui.sayi(hucre['AZ'][0])} tanesinde talep düzensiz.",
    "birlikte": None, "gun": None,
}
chat.rafbot(bilgi)
