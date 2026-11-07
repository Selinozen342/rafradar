"""Veri Kalitesi. Güvenilirlik ve metrik tanımları."""
import pandas as pd
import streamlit as st
from common import analytics as an
from common import analytics2 as an2
from common import chat, data, ui

tum = data.veri()
kal = st.session_state.get("kalite") or {}
ui.baslik("Veri Kalitesi", "Bu verilere ne kadar güvenebiliriz ve rakamlar nasıl hesaplandı?")


@st.cache_data(show_spinner="Norm aşımı hesaplanıyor…")
def c_norm(_tum, vid):
    return an2.norm_asimi(_tum)


vid = (st.session_state.get("dosya_adi", ""), len(tum))
ham = kal.get("ham_satir", len(tum))
tem = kal.get("temiz_satir", len(tum))
atilan = kal.get("atilan", ham - tem)
nsip = tum["InvoiceNo"].nunique() if "InvoiceNo" in tum.columns else len(tum)
ilk, son = tum["gun"].min(), tum["gun"].max()
st.markdown(f"<span class='pill g'>{ui.sayi(tem)} / {ui.sayi(ham)} satır kullanıldı · %{ui.sayi(tem / ham * 100, 3)}</span>"
            f"<span class='pill'>{ui.tarih_etiketi(ilk.date(), son.date())}</span>"
            f"<span class='pill'>{ui.sayi(nsip)} sipariş · {ui.sayi(tum['CustomerID'].nunique())} müşteri</span>", unsafe_allow_html=True)

oc, kn = c_norm(tum, vid)
asan_say = int(oc["asan"].sum())
fazla = float(oc["fazla"].sum())

# 1
with st.container(border=True):
    ui.bolum(1, "Veri ön işleme · 5 adım", "Ham dosyadan panellere giden yol")
    adimlar = [("1 · YÜKLEME", ui.sayi(ham), f"satır okundu · {kal.get('ham_sutun', '?')} sütun"),
               ("2 · TEMİZLİK", "−" + ui.sayi(atilan), "sıfır/negatif satır çıkarıldı"),
               ("3 · HESAPLAMA", "+" + str(kal.get("yeni_sutun", "?")), "yeni sütun: brüt ciro, net ciro, indirim"),
               ("4 · SEGMENTLEME", "A · B · C", "müşteri ve ürün, ciro payına göre"),
               ("5 · ANOMALİ DENETİMİ", ui.sayi(asan_say), "sipariş normdan fazla indirimli")]
    for kol, (t, v, s) in zip(st.columns(5), adimlar):
        kol.markdown(f"<div style='background:#faf7f2;border:1px solid #e4dfd6;border-radius:12px;padding:10px 12px;height:100%'><div style='font-size:10px;font-weight:700;color:#5b6475;letter-spacing:.04em'>{t}</div>"
                     f"<div style='font-family:Poppins;font-weight:700;font-size:20px;margin:4px 0'>{v}</div><div style='font-size:11px;color:#5b6475'>{s}</div></div>", unsafe_allow_html=True)

# 2
bos = kal.get("bos", {})
ad = {"InvoiceNo": "Sipariş no", "CustomerID": "Müşteri no", "InvoiceDate": "Tarih", "Description": "Ürün adı", "Category": "Kategori", "City": "Şehir", "StockCode": "Stok kodu"}
satir = []
for k, e in ad.items():
    if k in bos:
        n = bos[k]
        satir.append((e, (1 - n / ham) * 100, f"{ui.sayi(n)} satır boş" if n else ""))
if "StockCode" in bos and kal.get("bilimsel"):
    satir[-1] = ("Stok kodu", satir[-1][1], f"dolu ama {ui.sayi(kal['bilimsel'])} kod bilimsel gösterimde bozulmuş")
with st.container(border=True):
    ui.bolum(2, "Alan doluluğu", "Her alanın yüzde kaçı dolu · sarı ve kırmızı olanlar dikkat ister")
    h = ""
    for e, p, n in satir:
        renk = "#3d9a84" if p >= 99.995 else ("#e0a526" if p >= 95 else "#d9622b")
        h += (f"<div style='display:grid;grid-template-columns:150px 1fr 70px 1.6fr;gap:10px;align-items:center;padding:5px 0;font-size:13px'><span>{e}</span>"
              f"<div style='background:#ece7dd;border-radius:5px;height:10px'><div style='width:{p:.2f}%;background:{renk};height:10px;border-radius:5px'></div></div>"
              f"<b>%{ui.sayi(p, 2).rstrip('0').rstrip(',')}</b><span style='font-size:11px;color:#5b6475'>{n}</span></div>")
    st.markdown(h, unsafe_allow_html=True)

# 3
tekrar = kal.get("tekrar", 0)
with st.container(border=True):
    ui.bolum(3, "Tekrar eden satırlar")
    st.markdown(f"<div style='font-size:13px'>Birebir aynı satır <b>{ui.sayi(tekrar)}</b> <span class='pill y'>%{ui.sayi(tekrar / ham * 100, 1)}</span></div>"
                f"<div style='font-size:12px;color:#5b6475;margin-top:4px'>Silinmedi: aynı ürün aynı siparişte iki kez okutulmuş olabilir. Silmek cirodan yaklaşık %{ui.sayi(tekrar / ham * 100, 1)} götürürdü.</div>"
                "<span class='pill'>Bilinen risk · küçük</span>", unsafe_allow_html=True)

# 4
with st.container(border=True):
    ui.bolum(4, "Hangi kategoride indirim normu en çok aşılıyor?", "Her kategorinin normal indirimi (norm) var. Normun 10 puan üstünde indirimle kesilen siparişlerin payı")
    st.markdown(f"<div style='font-family:Poppins;font-weight:700;font-size:18px'>Her 100 siparişin {ui.sayi(asan_say / len(oc) * 100, 0)}'si normun üstünde indirimli</div>"
                f"<div style='font-size:12px;color:#5b6475;margin-bottom:8px'>Fazlası toplam ≈ {ui.tl(fazla)}</div>", unsafe_allow_html=True)
    h = ""
    for kat, r in kn.head(7).iterrows():
        h += (f"<div style='display:grid;grid-template-columns:200px 1fr 130px;gap:10px;align-items:center;padding:5px 0;font-size:13px'><b>{kat}</b>"
              f"<div><div style='background:#ece7dd;border-radius:5px;height:10px'><div style='width:{min(r['pay'] * 100 * 2, 100):.1f}%;background:#d9622b;height:10px;border-radius:5px'></div></div>"
              f"<div style='font-size:11px;color:#5b6475'>%{ui.sayi(r['pay'] * 100, 0)} ({ui.sayi(r['asan'])} sipariş) · norm %{ui.sayi(r['md'] * 100, 0)}, %{ui.sayi((r['md'] + 0.10) * 100, 0)} ve üzeri</div></div>"
              f"<span style='text-align:right;font-size:12px'>≈ {ui.tl(r['fazla'])} fazla</span></div>")
    st.markdown(h, unsafe_allow_html=True)

# 5
with st.container(border=True):
    ui.bolum(5, "Varsayımlar ve sınırlar", "Kararlarda bu dört noktaya dikkat edilmeli")
    kt = [("Varsayım", "Maliyet verisi yok", "Alış maliyeti ürüne göre değişir. Tek ürün planında maliyeti sen girersin; başlangıç değeri liste fiyatın %44'ü", "Satış · indirim planı"),
          ("Varsayım", "Stok verisi yok", "Güvenlik stoğu ve sipariş noktası talebe göre hesaplanıyor", "Tedarik · yönetici özeti"),
          ("Sınır", "Saat bilgisi yok", "Yalnız gün bazlı analiz yapılabiliyor", "Satış · haftanın günü"),
          ("Sınır", "Yalnız 2020", "Yıllık mevsimsellik öğrenilemiyor; tahmin hatası ≈ %25", "Yönetici · tahminler")]
    for kol, (t, b, s, y) in zip(st.columns(4), kt):
        kol.markdown(f"<div style='background:#faf7f2;border:1px solid #e4dfd6;border-radius:12px;padding:10px 12px;height:100%'><span class='pill {'y' if t == 'Sınır' else 'g'}'>{t}</span>"
                     f"<div style='font-weight:700;margin:4px 0'>{b}</div><div style='font-size:12px;line-height:1.5'>{s}</div>"
                     f"<div style='font-size:11px;color:#5b6475;margin-top:6px'>{y}</div></div>", unsafe_allow_html=True)

# 6
SOZLUK = {
    "Net ciro": ("Net ciro = Σ miktar × net fiyat", "İndirim düşüldükten sonra tahsil edilen tutar. Liste fiyat üzerinden hesaplanan brüt ciro ayrıca tutulur.", "Satış · KPI · Yönetici · karne"),
    "İndirim oranı": ("İndirim oranı = 1 − net ciro / brüt ciro", "Liste fiyata göre verilen toplam indirim. Dönem içinde ciro ağırlıklı hesaplanır.", "Satış · Yönetici"),
    "Fazla indirim": ("Fazla indirim = Σ (sipariş indirimi − kategori normu) × brüt tutar", "Yalnız normdan 10 puan fazla indirimli siparişler sayılır. Kategori normu, o kategorinin ortanca indirimidir.", "Satış · şüpheli sipariş · Veri kalitesi"),
    "Segment A-B-C": ("A: cironun ilk %80’i · B: sonraki %15 · C: son %5", "Müşteri ve ürünler ciroya göre büyükten küçüğe sıralanır, kümülatif paya göre bölünür.", "Satış · Yönetici · Tedarik"),
    "Churn riski": ("Risk = P(30 gün içinde sipariş vermeme)", "Geçmiş sipariş sıklığı, son siparişten geçen süre ve tutarlardan öğrenen bir model hesaplar. %70 ve üzeri yüksek risk.", "Satış · Pazarlama · Yönetici"),
    "Sipariş noktası": ("Sipariş noktası = ort. günlük talep × temin süresi + güvenlik stoğu", "Güvenlik stoğu = z × talep sapması × √temin süresi. Stok seviyesi bu noktaya inince sipariş verilir.", "Tedarik"),
    "Talep tahmini": ("Üç yöntemden 4 haftalık hatası en küçük olan seçilir", "Son 4 hafta ortalaması, son 8 hafta ortalaması ve sönümlü trend. Hata, geçmişte denenerek ölçülür.", "Tedarik · Yönetici"),
}
with st.container(border=True):
    ui.bolum(6, "Metrik sözlüğü", "Bir metriğe bas: formülü ve hangi sayfada kullanıldığını gör")
    sec = st.radio("Metrik", list(SOZLUK), horizontal=True, label_visibility="collapsed", key="kal_metrik")
    f, a, y = SOZLUK[sec]
    st.markdown(f"<div style='background:#faf7f2;border-radius:10px;padding:12px 14px'><div style='font-family:Poppins;font-weight:700'>{f}</div>"
                f"<div style='font-size:12px;margin:4px 0'>{a}</div><span class='pill'>{y}</span></div>", unsafe_allow_html=True)

# 7
with st.container(border=True):
    ui.bolum(7, "İşlenmiş veriden örnek 5 satır")
    gos = [c for c in ["InvoiceNo", "gun", "CustomerID", "Description", "Category", "City", "Quantity", "UnitPrice", "gross", "net", "disc"] if c in tum.columns]
    st.dataframe(tum[gos].head(5), hide_index=True, use_container_width=True)

bilgi = {"ciro": f"{ui.sayi(tem)} satırın tamamı kullanıldı (ham {ui.sayi(ham)}, atılan {ui.sayi(atilan)}).",
         "indirim": f"{ui.sayi(asan_say)} sipariş kategori normunun 10 puan üstünde indirimli; fazlası ≈ {ui.tl(fazla)}.",
         "kopru": None, "churn": None, "segment": None, "birlikte": None, "gun": None}
chat.rafbot(bilgi)
