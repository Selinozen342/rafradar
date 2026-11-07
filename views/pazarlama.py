"""Pazarlama & Müşteri sayfası. HTML taslağındaki 7 panelin aynısı, veriden canlı hesaplanır."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from common import analytics as an
from common import analytics2 as an2
from common import chat, data, ui
from common import widgets as w

tum = data.veri()
vid = (st.session_state.get("dosya_adi", ""), len(tum))
ui.baslik("Pazarlama & Müşteri", "Hangi müşteriye, hangi ürünle, ne zaman gitmeliyiz?")
m, a, b, ca, cb = ui.filtreler(tum)
K = w.fk()
if m.empty:
    st.warning("Bu filtrelerle veri yok. Filtreleri gevşetip tekrar dene.")
    st.stop()
et = ui.tarih_etiketi
S, C = w.ozet_c(m, K, a, b), w.ozet_c(m, K, ca, cb)
hN, hD = S["gun"] == C["gun"], S["gun"] != C["gun"]
ch = an2.musteri_degisim(tum, m, a, b, ca, cb)
mr = an.araliga_kes(m, a, b)
perC = S["net"] / ch["aS"] if ch["aS"] else 0
perCc = C["net"] / ch["aC"] if ch["aC"] else 0
dpc = S["dnet"] / S["dcust"] if S["dcust"] else 0
dpcc = C["dnet"] / C["dcust"] if C["dcust"] else 0

st.markdown(w.ust_bilgi(S, C, a, b, ca, cb), unsafe_allow_html=True)
w.kgrid([
    w.kart("Aktif müşteri", ui.sayi(ch["aS"]), w.chg(w.rel(ch["aS"], ch["aC"]), hN), "Günlük ort.", ui.sayi(S["dcust"], 1), w.chg(w.rel(S["dcust"], C["dcust"]), hD)),
    w.kart("Yeni müşteri", ui.sayi(ch["nw"]), w.chg(w.rel(ch["nw"], ch["nwC"]), hN), "Günlük ort.", ui.sayi(ch["nw"] / S["gun"], 2), w.chg(w.rel(ch["nw"] / S["gun"], ch["nwC"] / C["gun"]), hD)),
    w.kart("Satılan adet", ui.sayi(S["q"] / 1000, 1) + " bin", w.chg(w.rel(S["q"], C["q"]), hN), "Günlük ort.", ui.sayi(S["dq"]), w.chg(w.rel(S["dq"], C["dq"]), hD)),
    w.kart("Net ciro", ui.sayi(S["net"] / 1e6, 2) + " M ₺", w.chg(w.rel(S["net"], C["net"]), hN), "Günlük ort.", ui.sayi(S["dnet"] / 1000, 1) + " bin ₺", w.chg(w.rel(S["dnet"], C["dnet"]), hD)),
    w.kart("Müşteri başı ciro", ui.sayi(perC / 1000, 1) + " bin ₺", w.chg(w.rel(perC, perCc), hN), "Günlük ort.", ui.sayi(dpc) + " ₺", w.chg(w.rel(dpc, dpcc), hD), "#e0a526"),
])
w.not_kutusu("Tüm paneller seçtiğin tarihlere göre hesaplanır. Yalnız 2. panel (aylar arası tekrar alım) seçtiğin yılın tamamını gösterir.")

# ---------- 1. Müşteri tabanı değişimi ----------
net = ch["aS"] - ch["aC"]
with st.container(border=True):
    ui.bolum(1, "Müşteri tabanı bu dönemde nasıl değişti?", f"Karşılaştırma dönemindeki aktif müşteri {ui.sayi(ch['aC'])} → seçili dönemdeki aktif müşteri {ui.sayi(ch['aS'])}")
    w.vurgu(f"{ui.sayi(ch['nw'])} yeni ve {ui.sayi(ch['bk'])} geri dönen müşteri geldi, {ui.sayi(ch['ls'])} müşteri alım yapmadı. "
            f"Aktif müşteri {ui.sayi(abs(net))} {'arttı' if net >= 0 else 'azaldı'}.")
    k1, k2 = st.columns([3, 2])
    with k1:
        v = [-ch["ls"], ch["nw"], ch["bk"], net]
        ad = ["Kaybedilen", "Yeni", "Geri dönen", "Net değişim"]
        al = ["karşılaştırmada aldı, şimdi almadı", "ilk alımı bu dönemde", "daha önce almış, karşılaştırmada almamış", "aktif müşteri farkı"]
        mxa = max([abs(x) for x in v] + [1])
        fig = go.Figure(go.Bar(y=[f"{x}<br><span style='font-size:10px;color:#5b6475'>{y}</span>" for x, y in zip(ad, al)], x=v, orientation="h",
                               marker_color=[ui.RENK["kirmizi"] if x < 0 else ui.RENK["yesil"] for x in v],
                               text=[("+" if x >= 0 else "−") + ui.sayi(abs(x)) for x in v], textposition="outside", cliponaxis=False))
        fig.update_yaxes(autorange="reversed", automargin=True)
        fig.update_xaxes(zeroline=True, zerolinecolor="#1f2a44", zerolinewidth=2, showgrid=False, showticklabels=False,
                         range=[-mxa * 1.4, mxa * 1.4], title_text="← azalma  |  0  |  artış →")
        fig.update_layout(height=290, margin=dict(l=10, r=10, t=6, b=0), plot_bgcolor="white")
        st.plotly_chart(fig, use_container_width=True)
    with k2:
        for t, x in (("Karşılaştırma dönemi · aktif müşteri", ch["aC"]), ("Seçili dönem · aktif müşteri", ch["aS"]),
                     ("İki dönemde de alan (devam eden)", ch["ct"])):
            st.markdown(f"<div class='out'><div class='t'>{t}</div><div class='v'>{ui.sayi(x)}</div></div><div style='height:6px'></div>", unsafe_allow_html=True)
        st.caption("Veri ilk gününde başladığı için ilk ayda “yeni” sayısı yüksek çıkar.")

# ---------- 2. Kohort ----------
yillar = sorted(set(tum["gun"].dt.year.unique().tolist()) | {tum["gun"].dt.year.min() - 1, tum["gun"].dt.year.max() + 1})
with st.container(border=True):
    c1, c2 = st.columns([4, 1])
    with c1:
        ui.bolum(2, "Bir ayda alanlar başka aylarda da alıyor mu?", "Yıl bazlı · seçtiğin tarihten bağımsız")
    with c2:
        yil = st.selectbox("Yıl", yillar, index=yillar.index(tum["gun"].dt.year.max()), key="koh_yil")
    M, cnt = an2.kohort(m, yil)
    if M is None:
        st.markdown(f"<div style='padding:40px 16px;text-align:center;background:#faf7f2;border-radius:10px;font-size:13px;color:#5b6475'>"
                    f"<b style='color:#1f2a44'>{yil} için veri yok.</b><br>Veri seti bu yılı kapsamıyor.</div>", unsafe_allow_html=True)
    else:
        w.vurgu(f"Şubat’ta alanların %{ui.sayi(M[1][2], 0)}’i Mart’ta, %{ui.sayi(M[1][3], 0)}’i Nisan’da, %{ui.sayi(M[1][4], 0)}’i Mayıs’ta da aldı.")
        tip = w.info("Satır: o ayda en az bir sipariş veren müşteriler. Sütun: aynı müşterilerin o ayda da sipariş verdiği oran. Örnek: Şubat satırı, Mart sütunu = Şubat’ta alanların yüzde kaçı Mart’ta da aldı.")
        h = f"<table class='t'><thead><tr><th>Alım yapılan ay{tip}</th><th class='r'>Müşteri adedi</th>" + "".join(f"<th style='text-align:center'>{x}</th>" for x in ui.AYLAR) + "</tr></thead><tbody>"
        for i in range(12):
            h += f"<tr><td style='font-weight:600'>{w.AY_AD[i]}</td><td class='r' style='color:#5b6475'>{ui.sayi(cnt[i])}</td>"
            for j in range(12):
                if i == j:
                    h += "<td style='text-align:center;background:#e4dfd6;color:#5b6475'>—</td>"
                else:
                    v = M[i][j]
                    h += f"<td style='text-align:center;font-weight:600;background:{w.mix('#f6f3ee', '#2f8a73', min(1, v / 60))};color:{'#fff' if v > 38 else '#1f2a44'}'>{ui.sayi(v, 0)}</td>"
            h += "</tr>"
        st.markdown(h + "</tbody></table>", unsafe_allow_html=True)
        st.caption("Hücredeki sayı: satırdaki ayda alanların yüzde kaçı sütundaki ayda da aldı. Koyu renk daha yüksek oran.")

# ---------- 3. RFM ----------
rf, onceden = an2.rfm(tum, m, a, b)
cnt_seg = [int((rf["seg"] == i).sum()) for i in range(6)] + [len(onceden)]
net_seg = [rf.loc[rf["seg"] == i, "net"].sum() for i in range(6)]
net_top = sum(net_seg) or 1
harita = np.zeros((5, 5), dtype=int)
for _, r in rf.iterrows():
    harita[5 - int(r["FM"]), int(r["R"]) - 1] += 1
churn, auc = w.churn_c(tum, vid)
with st.container(border=True):
    ui.bolum(3, "Müşteriler davranışlarına göre kimler?",
             f"{et(a, b)} döneminde sipariş veren {ui.sayi(len(rf))} müşteri, son sipariş zamanı, sipariş sıklığı ve ciroya göre altı gruba ayrıldı (RFM)" +
             w.info("Son sipariş (Recency), sipariş sıklığı (Frequency) ve ciro (Monetary) seçili dönemde müşterileri 1–5 arası puanlar. Puanlara göre altı grup oluşur."))
    s1, s2 = st.columns([1, 1.3])
    with s1:
        g = "<div style='display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:3px'>"
        for r in range(5):
            for c in range(5):
                sg = an2.seg_of(c + 1, 5 - r)
                g += (f"<div style='background:{an2.SEG_RENK[sg]};color:{an2.SEG_YAZI[sg]};border-radius:6px;min-height:46px;display:flex;flex-direction:column;"
                      f"align-items:center;justify-content:center;line-height:1.15' title='{an2.SEG_AD[sg]}: {harita[r][c]} müşteri'>"
                      f"<b style='font-size:13px'>{harita[r][c]}</b><span style='font-size:9px;opacity:.85'>müşteri</span></div>")
        g += "</div><div style='font-size:11px;color:#5b6475;text-align:center;margin-top:4px'>son sipariş: eski → yeni · satırlar: sipariş sıklığı ve ciro, yüksek üstte</div>" \
             "<div style='font-size:11px;color:#5b6475;text-align:center'>Kutudaki sayı: müşteri adedi · renk: segment</div>"
        st.markdown(g, unsafe_allow_html=True)
    with s2:
        satir = []
        for i in range(7):
            nokta = f"<span style='display:inline-block;width:10px;height:10px;border-radius:50%;background:{an2.SEG_RENK[i]};margin-right:6px'></span>"
            satir.append([nokta + an2.SEG_AD[i] + w.info(an2.SEG_ACIKLAMA[i]), ui.sayi(cnt_seg[i]),
                          f"%{ui.sayi(cnt_seg[i] / max(1, len(rf)) * 100, 1)}" if i < 6 else "–",
                          f"%{ui.sayi(net_seg[i] / net_top * 100, 1)}" if i < 6 else "–"])
        satir.append(["<b>Tüm müşteriler</b>", f"<b>{ui.sayi(len(rf) + len(onceden))}</b>", "", ""])
        st.markdown(w.tablo(["Segment", "Müşteri adedi", "Müşteri payı", "Ciro payı"], satir, sag=(1, 2, 3)), unsafe_allow_html=True)
    sec = st.selectbox("Excel için segment", ["Tüm müşteriler"] + an2.SEG_AD[:6], key="rfm_sec")
    secim = rf if sec == "Tüm müşteriler" else rf[rf["seg"] == an2.SEG_AD.index(sec)]
    cr = an.araliga_kes(m, ca, cb).groupby("CustomerID").agg(cs=("InvoiceNo", "nunique"), cn=("net", "sum"))
    ilk_t = tum.groupby("CustomerID")["gun"].min()
    pc = an.pareto(mr, "CustomerID")
    il = tum.groupby("CustomerID")["City"].agg(lambda s: s.mode().iloc[0] if s.notna().any() and len(s.mode()) else "")
    ex = pd.DataFrame({
        "Müşteri": secim.index, "İl": il.reindex(secim.index).values,
        "Segment (RFM)": secim["seg"].map(lambda i: an2.SEG_AD[i]).values, "Segment (A-B-C)": pc["seg"].reindex(secim.index).values,
        "Seçili aralıkta sipariş sayısı": secim["sip"].values, "Seçili aralıkta net ciro (₺)": secim["net"].round(0).values,
        "Karşılaştırma aralığında sipariş sayısı": cr["cs"].reindex(secim.index).fillna(0).astype(int).values,
        "Karşılaştırma aralığında net ciro (₺)": cr["cn"].reindex(secim.index).fillna(0).round(0).values,
        "İlk sipariş": ilk_t.reindex(secim.index).dt.strftime("%d.%m.%Y").values,
        "Son sipariş": secim["son"].dt.strftime("%d.%m.%Y").values, "Kaç gündür sipariş yok": secim["rec"].values,
        "Bırakma riski (30 gün)": (churn["p"].reindex(secim.index) * 100).round(0).values})
    st.download_button(f"Excel’e indir: {sec} · {ui.sayi(len(ex))} müşteri", ui.xlsx(ex, "Müşteriler"),
                       file_name="musteriler_" + sec.lower().replace(" ", "_").replace("/", "") + ".xlsx", mime=w.XLSX, type="primary")

# ---------- 4. Sipariş aralığı ----------
gd = an2.gecikme(tum, rf, b)
with st.container(border=True):
    ui.bolum(4, "Sipariş aralığı uzayan müşteriler kimler?", f"Her müşterinin kendi tipik sipariş aralığına göre, {et(b, b)} itibarıyla")
    rf2 = rf.assign(g=gd.reindex(rf.index))
    sayim = {i: [int(((rf2["seg"] == i) & (rf2["g"] == k)).sum()) for k in range(4)] for i in range(6)}
    ond = gd.reindex(onceden).value_counts()
    sayim[6] = [int(ond.get(k, 0)) for k in range(4)]
    cok_gec = sum(sayim[i][2] for i in range(7))
    vip = sayim[0][2] + sayim[1][2]
    w.vurgu(f"{ui.sayi(cok_gec)} müşteri, kendi tipik aralığının 2 katından uzun süredir sipariş vermedi" + (f"; {ui.sayi(vip)}’i Şampiyon veya Sadık." if vip else "."))
    ren = ["#3d9a84", "#e0a526", "#d0574f", "#cfc9bd"]
    ad = ["Zamanında", "Gecikmiş", "Çok gecikmiş", "Yeterli geçmiş yok"]
    tn = ["Son siparişten bu yana geçen süre, müşterinin tipik sipariş aralığını aşmadı. Tipik aralık: müşterinin sipariş günleri arasındaki ortanca gün sayısı.",
          "Geçen süre tipik aralığın 1 ile 2 katı arasında.", "Geçen süre tipik aralığın 2 katından fazla. Müşteri büyük olasılıkla alışverişi yavaşlattı veya bıraktı.",
          "Müşterinin 3’ten az sipariş günü var, tipik aralık hesaplanamadı."]
    st.markdown("<div style='display:flex;gap:14px;flex-wrap:wrap;font-size:12px;margin-bottom:8px'>" + "".join(
        f"<span><span style='display:inline-block;width:10px;height:10px;border-radius:50%;background:{ren[i]};margin-right:4px'></span>{ad[i]}{w.info(tn[i])}</span>" for i in range(4)) + "</div>", unsafe_allow_html=True)
    bars = ""
    for i in range(7):
        t = sum(sayim[i])
        if not t:
            continue
        bars += (f"<div style='display:grid;grid-template-columns:150px minmax(0,1fr) 40px;gap:8px;align-items:center;padding:4px 0;font-size:12px'><span>{an2.SEG_AD[i]}</span>"
                 "<div style='display:flex;height:20px;border-radius:5px;overflow:hidden;background:#f0ebe2'>" +
                 "".join(f"<div style='flex:{v} 1 0;background:{ren[k]}' title='{ad[k]}: {v} müşteri'></div>" for k, v in enumerate(sayim[i])) +
                 f"</div><span style='text-align:right;color:#5b6475'>{t}</span></div>")
    st.markdown(bars, unsafe_allow_html=True)
    st.caption("Sağdaki sayı: gruptaki müşteri adedi. Bırakma olasılığı için Satış sayfasına bak.")

# ---------- 5-6. İl ve birlikte alınanlar ----------
p5, p6 = st.columns([1.3, 1])
ild = an2.il_dagilimi(tum, mr)
with p5, st.container(border=True):
    ui.bolum(5, "Hangi ilden ne kadar satıyoruz?", "Seçili dönemde cironun il payı, aktif müşteri adedi ve sipariş sayısı")
    if ild.empty:
        st.info("Bu aralıkta sipariş yok.")
    else:
        top = ild.head(8)
        tot = ild["net"].sum()
        w.vurgu(f"{top.index[0]} cironun %{ui.sayi(top['net'].iloc[0] / tot * 100, 0)}’ini getiriyor; ilk {len(top)} il toplam %{ui.sayi(top['net'].sum() / tot * 100, 0)}.")
        mx = top["net"].iloc[0]
        h = ""
        for il_ad, r in top.iterrows():
            h += (f"<div style='display:grid;grid-template-columns:80px minmax(0,1fr) 50px 170px;gap:8px;align-items:center;padding:4px 0;font-size:12px'><span>{il_ad}</span>"
                  f"<div style='height:16px;background:#f0ebe2;border-radius:4px'><div style='width:{r['net'] / mx * 100:.1f}%;height:100%;background:#d9622b;border-radius:4px'></div></div>"
                  f"<span style='text-align:right;font-weight:600'>%{ui.sayi(r['net'] / tot * 100, 1)}</span>"
                  f"<span style='text-align:right;color:#5b6475;white-space:nowrap'>{int(r['musteri'])} müşteri · {ui.sayi(r['siparis'])} sipariş</span></div>")
        st.markdown(h, unsafe_allow_html=True)
        st.caption(f"Diğer iller %{ui.sayi(max(0, 100 - top['net'].sum() / tot * 100), 1)}. İl, müşterinin en çok sipariş verdiği ildir.")
cift = w.birlikte_c(m, K, a, b)
gor, gorulen = [], set()
for c in cift:
    k = " ".join(c["a"].split()[:2]).lower()
    if k not in gorulen and len(gor) < 8:
        gorulen.add(k)
        gor.append(c)
with p6, st.container(border=True):
    ui.bolum(6, "Hangi ürünler birlikte alınıyor?", "Seçili dönemde aynı siparişte en sık görülen ürün çiftleri" +
             w.info("Ürün çiftleri, seçili dönemde en çok satan ürünler arasından seçilir ve aynı siparişteki sipariş sayısına göre sıralanır."))
    if not gor:
        st.info("Bu aralıkta yeterli birlikte alım yok.")
    else:
        w.vurgu("Çiftlerin çoğu aynı serinin kitapları: paket fiyatla birlikte teklif edilebilir.")
        mx = gor[0]["n"]
        st.markdown("".join(
            f"<div style='padding:5px 0;font-size:12px'><div style='display:flex;justify-content:space-between;gap:8px'><span><b>{c['a']}</b> + <b>{c['b']}</b></span>"
            f"<span style='white-space:nowrap;font-weight:600'>{c['n']} sipariş</span></div><div style='height:6px;background:#f0ebe2;border-radius:3px;margin-top:3px'>"
            f"<div style='width:{c['n'] / mx * 100:.0f}%;height:100%;background:#3d9a84;border-radius:3px'></div></div></div>" for c in gor), unsafe_allow_html=True)

# ---------- 7. Kategori tercihi ----------
with st.container(border=True):
    ui.bolum(7, "Hangi grup hangi kategoriyi daha çok alıyor?", f"{et(a, b)} · grubun kategori payı ÷ tüm müşterilerin kategori payı · 100 = ortalama" +
             w.info("Örnek: 150 = bu grup, o kategoriyi diğer müşterilere göre 1,5 kat fazla alıyor. Yalnız cirosu en yüksek 6 kategori gösterildi."))
    cats, KM = an2.kategori_endeksi(mr, rf)
    if not cats:
        st.info("Bu aralıkta yeterli veri yok.")
    else:
        en = max(((v, i, j) for i, r in enumerate(KM) for j, v in enumerate(r) if cnt_seg[i] > 0), default=None)
        if en:
            w.vurgu(f"{an2.SEG_AD[en[1]]} grubunun {cats[en[2]]} alımı ortalamanın {ui.sayi(en[0] / 100, 1)} katı.")
        st.markdown(w.sapma_tablo(an2.SEG_AD[:6], cats, KM), unsafe_allow_html=True)

# ---------- RafBot ----------
bilgi = {
    "ciro": f"Seçili dönemde {ui.sayi(ch['aS'])} müşteri sipariş verdi: " + ", ".join(f"{an2.SEG_AD[i]} {cnt_seg[i]}" for i in range(6)) + ".",
    "segment": f"Seçili dönemde {ui.sayi(ch['aS'])} müşteri sipariş verdi: " + ", ".join(f"{an2.SEG_AD[i]} {cnt_seg[i]}" for i in range(6)) + ".",
    "churn": f"{ui.sayi(cok_gec)} müşteri kendi tipik sipariş aralığının 2 katından uzun süredir sipariş vermedi.",
    "kopru": f"Aktif müşteri {ui.sayi(ch['aC'])} → {ui.sayi(ch['aS'])}: {ui.sayi(ch['nw'])} yeni, {ui.sayi(ch['bk'])} geri dönen, {ui.sayi(ch['ls'])} kaybedilen.",
    "birlikte": (f"Seçili dönemde en sık birlikte alınan çift: {gor[0]['a']} + {gor[0]['b']} ({gor[0]['n']} sipariş).") if gor else None,
    "indirim": None, "gun": None,
}
chat.rafbot(bilgi)
