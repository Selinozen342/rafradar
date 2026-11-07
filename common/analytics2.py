"""Pazarlama, Tedarik, Yönetici ve Veri Kalitesi sayfalarının hesapları."""
import math
import numpy as np
import pandas as pd
from common import analytics as an

SEG_AD = ["Şampiyonlar", "Sadık", "Yeni / Potansiyel", "Dikkat gerektiren", "Risk altında", "Uykuda / Kayıp", "Dönemde sipariş vermeyen"]
SEG_ACIKLAMA = ["Yakın zamanda, sık ve yüksek tutarla aldı", "Sık ve yüksek tutarla alıyor, son siparişi biraz eski",
                "Yakın zamanda aldı, sıklık ve tutar düşük", "Orta zamanda aldı, sıklık ve tutar düşük",
                "Eskiden iyi alıyordu, uzun süredir almadı", "Seçili dönemde en erken aldı, sıklık ve tutar düşük",
                "Önceden müşteri, bu dönemde hiç sipariş vermedi"]
SEG_RENK = ["#1d6b58", "#3d9a84", "#3b6fd1", "#e0a526", "#d9622b", "#9aa3b2", "#c9c3b6"]
SEG_YAZI = ["#fff", "#fff", "#fff", "#1f2a44", "#fff", "#1f2a44", "#1f2a44"]
POLITIKA = {"AX": "Otomatik yenile", "AY": "Tahmin + güvenlik stoğu", "AZ": "Yakın takip", "BX": "Periyodik sipariş",
            "BY": "Periyodik + güvenlik stoğu", "BZ": "Siparişe göre", "CX": "Toplu sipariş", "CY": "Minimum stok",
            "CZ": "Siparişe göre, tasfiye adayı"}


# ======================= PAZARLAMA =======================
def q5(vals, artan):
    """1..5 puan (5 = en iyi); eşitlikte sıra korunur."""
    v = np.asarray(vals, dtype=float)
    n = len(v)
    anahtar = v if artan else -v
    sira = np.lexsort((np.arange(n), anahtar))
    out = np.empty(n, dtype=int)
    out[sira] = np.floor(np.arange(n) * 5 / n).astype(int) + 1
    return out


def seg_of(R, FM):
    if R >= 4:
        return 0 if FM >= 4 else 2
    if R == 3:
        return 1 if FM >= 4 else 3
    return 4 if FM >= 3 else 5


def musteri_degisim(tum, m, a, b, ca, cb):
    """Seçili ve karşılaştırma dönemi arasında müşteri tabanı hareketi."""
    ilk = tum.groupby("CustomerID")["gun"].min()
    S = set(an.araliga_kes(m, a, b)["CustomerID"])
    C = set(an.araliga_kes(m, ca, cb)["CustomerID"])
    yeni = {c for c in S - C if ilk[c] >= pd.Timestamp(a)}
    geri = (S - C) - yeni
    return dict(aS=len(S), aC=len(C), nw=len(yeni), bk=len(geri), ls=len(C - S), ct=len(S & C))


def kohort(m, yil):
    """Ay satırında alanların yüzde kaçı sütundaki ayda da aldı."""
    x = m[m["gun"].dt.year == yil]
    if x.empty:
        return None, None
    ay = x.assign(ay=x["gun"].dt.month).drop_duplicates(["CustomerID", "ay"])
    P = pd.crosstab(ay["CustomerID"], ay["ay"]).reindex(columns=range(1, 13), fill_value=0)
    cnt = P.sum()
    M = np.zeros((12, 12))
    for i in range(12):
        for j in range(12):
            M[i, j] = (P[i + 1] & P[j + 1]).sum() / cnt[i + 1] * 100 if cnt[i + 1] else 0
    return M, cnt.values


def rfm(tum, m, a, b):
    """Seçili aralıkta sipariş veren müşterilerin RFM segmentleri."""
    mr = an.araliga_kes(m, a, b)
    g = mr.groupby("CustomerID")
    t = pd.DataFrame({"son": g["gun"].max(), "sip": g["InvoiceNo"].nunique(), "net": g["net"].sum()})
    t["rec"] = (pd.Timestamp(b) - t["son"]).dt.days
    R, F, M = q5(t["rec"], False), q5(t["sip"], True), q5(t["net"], True)
    fm = np.clip(np.floor((F + M) / 2 + 0.5).astype(int), 1, 5)
    t["R"], t["FM"] = R, fm
    t["seg"] = [seg_of(r, f) for r, f in zip(R, fm)]
    ilk = tum.groupby("CustomerID")["gun"].min()
    onceden = ilk[(ilk <= pd.Timestamp(b)) & (~ilk.index.isin(t.index))].index
    return t, list(onceden)


def gecikme(tum, rf, bitis):
    """Her müşterinin kendi tipik sipariş aralığına göre gecikme durumu: 0 zamanında, 1 gecikmiş, 2 çok gecikmiş, 3 geçmiş yok."""
    h = tum[tum["gun"] <= pd.Timestamp(bitis)][["CustomerID", "gun"]].drop_duplicates()
    gun_listesi = h.sort_values("gun").groupby("CustomerID")["gun"].apply(lambda s: s.values)
    out = {}
    for c, d in gun_listesi.items():
        if len(d) < 3:
            out[c] = 3
            continue
        aralik = np.diff(d).astype("timedelta64[D]").astype(int)
        med = max(1, float(np.median(aralik)))
        ra = (pd.Timestamp(bitis) - pd.Timestamp(d[-1])).days / med
        out[c] = 0 if ra <= 1 else (1 if ra <= 2 else 2)
    return pd.Series(out)


def il_dagilimi(tum, mr):
    il = tum.groupby("CustomerID")["City"].agg(lambda s: s.mode().iloc[0] if s.notna().any() and len(s.mode()) else "Belirsiz")
    x = mr.assign(il=mr["CustomerID"].map(il).fillna("Belirsiz"))
    return x.groupby("il").agg(net=("net", "sum"), musteri=("CustomerID", "nunique"), siparis=("InvoiceNo", "nunique")).sort_values("net", ascending=False)


def kategori_endeksi(mr, rf, ilk=6):
    top = mr.groupby("Category")["net"].sum().sort_values(ascending=False).head(ilk).index.tolist()
    x = mr[mr["CustomerID"].isin(rf.index)].assign(seg=lambda d: d["CustomerID"].map(rf["seg"]))
    toplam = x["net"].sum()
    ov = x[x["Category"].isin(top)].groupby("Category")["net"].sum() / toplam
    M = []
    for s in range(6):
        y = x[x["seg"] == s]
        sh = y.groupby("Category")["net"].sum() / y["net"].sum() if len(y) else pd.Series(dtype=float)
        M.append([int(round(sh.get(c, 0) / ov[c] * 100)) if len(y) and ov.get(c, 0) else 100 for c in top])
    return top, M


# ======================= TEDARİK =======================
def haftalik(tum, urun):
    """Ürünün haftalık satılan adedi (verinin ilk gününden 7'şer gün)."""
    p = tum[tum["Description"] == urun].groupby("gun")["Quantity"].sum()
    bas, bit = tum["gun"].min(), tum["gun"].max()
    p = p.reindex(pd.date_range(bas, bit), fill_value=0)
    n = len(p) // 7
    return p.values[: n * 7].reshape(n, 7).sum(axis=1), p.values


def f_holt(w, h):
    a, b, ph = 0.4, 0.1, 0.9
    l, t = w[0], 0.0
    for v in w[1:]:
        lp = l
        l = a * v + (1 - a) * (l + ph * t)
        t = b * (l - lp) + (1 - b) * ph * t
    f, s, p = [], 0.0, 1.0
    for _ in range(h):
        p *= ph
        s += p
        f.append(max(0.0, l + s * t))
    return f


def f_ort(n):
    return lambda w, h: [float(np.mean(w[-n:]))] * h


MODELLER = [("Son 4 hafta ortalaması", f_ort(4)), ("Son 8 hafta ortalaması", f_ort(8)), ("Trend (Holt)", f_holt)]


def geri_test(w):
    """Üç yöntemi son 12 denemede 4 haftalık toplam hatayla karşılaştırır."""
    T = len(w)
    baslangic = max(12, T - 16)
    sonuc = []
    for ad, f in MODELLER:
        hata = toplam = 0.0
        for t in range(baslangic, T - 3):
            f4 = sum(f(w[:t], 4))
            a4 = w[t:t + 4].sum()
            hata += abs(a4 - f4)
            toplam += a4
        rs, fcs = [], []
        for u in range(max(12, T - 12), T):
            f1 = f(w[:u], 1)[0]
            rs.append(w[u] - f1)
            fcs.append(f1)
        sonuc.append(dict(ad=ad, wape=hata / toplam if toplam else 0, sd=float(np.std(rs)), fcs=fcs, f=f))
    en = int(np.argmin([r["wape"] for r in sonuc]))
    return sonuc, en


def z_of(p):
    t = math.sqrt(-2 * math.log(1 - p))
    c, d = (2.515517, 0.802853, 0.010328), (1.432788, 0.189269, 0.001308)
    return t - (c[0] + c[1] * t + c[2] * t * t) / (1 + d[0] * t + d[1] * t * t + d[2] * t * t * t)


def stok(w, gunluk, Lw, sl):
    """Güvenlik stoğu, sipariş noktası ve son 26 haftanın stok simülasyonu."""
    son = w[-26:]
    mu, sd = float(np.mean(son)), float(np.std(son))
    z = z_of(sl / 100)
    ss = z * sd * math.sqrt(Lw)
    rop = mu * Lw + ss
    q = gunluk[-182:]
    L = int(Lw * 7)
    Q = max(1.0, 4 * mu)
    S = rop + Q
    on = S
    pipe, out, outd, ser, ords = [], 0, [], [], []
    for d in range(len(q)):
        gelen = [p for p in pipe if p[0] == d]
        for p in gelen:
            on += p[1]
        pipe = [p for p in pipe if p[0] != d]
        if on >= q[d]:
            on -= q[d]
        else:
            out += 1
            outd.append(d)
            on = 0
        pos = on + sum(p[1] for p in pipe)
        if pos <= rop:
            pipe.append((d + L, S - pos))
            ords.append(d)
        ser.append(on)
    return dict(mu=mu, sd=sd, ss=ss, rop=rop, out=out, ser=ser, ords=ords, outd=outd, L=L, S=S, n=len(q))


def abc_xyz(tum):
    """Ürünler adede göre A-B-C, aylık adet oynaklığına göre X-Y-Z."""
    q = tum.groupby("Description")["Quantity"].sum().sort_values(ascending=False)
    kum = q.cumsum() / q.sum()
    abc = pd.Series(np.where(kum <= 0.8, "A", np.where(kum <= 0.95, "B", "C")), index=q.index)
    ay = tum.assign(ay=tum["gun"].dt.to_period("M"))
    aylar = pd.period_range(ay["ay"].min(), ay["ay"].max(), freq="M")
    pv = ay.groupby(["Description", "ay"])["Quantity"].sum().unstack(fill_value=0).reindex(columns=aylar, fill_value=0)
    cv = (pv.std(axis=1) / pv.mean(axis=1)).reindex(q.index).fillna(9)
    xyz = pd.Series(np.where(cv <= 0.5, "X", np.where(cv <= 1, "Y", "Z")), index=q.index)
    return q, kum, abc, xyz


def mevsimsellik(tum, ilk=6):
    yil = tum["gun"].dt.year.max()
    x = tum[tum["gun"].dt.year == yil]
    top = x.groupby("Category")["Quantity"].sum().sort_values(ascending=False).head(ilk).index.tolist()
    pv = x[x["Category"].isin(top)].assign(ay=x["gun"].dt.month).groupby(["Category", "ay"])["Quantity"].sum().unstack(fill_value=0)
    pv = pv.reindex(index=top, columns=range(1, 13), fill_value=0)
    ort = pv.replace(0, np.nan).mean(axis=1)
    return top, (pv.div(ort, axis=0).fillna(0) * 100).round().values, yil


def satissiz(tum):
    son = tum.groupby("Description")["gun"].max()
    bitis = tum["gun"].max()
    gun = (bitis - son).dt.days
    d = pd.DataFrame({"gun": gun, "adet": tum.groupby("Description")["Quantity"].sum(),
                      "net": tum.groupby("Description")["net"].sum(),
                      "kategori": tum.groupby("Description")["Category"].agg(lambda s: s.dropna().iloc[0] if s.notna().any() else "")})
    return d


# ======================= YÖNETİCİ =======================
def aylik(tum, yil):
    x = tum[tum["gun"].dt.year == yil]
    if x.empty:
        return None
    g = x.assign(ay=x["gun"].dt.month).groupby("ay").agg(net=("net", "sum"), gross=("gross", "sum"))
    g = g.reindex(range(1, 13), fill_value=0)
    g["disc"] = np.where(g["gross"] > 0, 1 - g["net"] / g["gross"].replace(0, np.nan), np.nan)
    return g


def metrik_dagilimi(tum):
    """12 ayın günlük ortalama göstergeleri ve yıl ortalaması."""
    bit = tum["gun"].max()
    yil = bit.year
    out = {k: [] for k in ("dnet", "dord", "basket", "disc", "dcust", "dq")}
    for ay in range(1, 13):
        a = pd.Timestamp(yil, ay, 1)
        b = (a + pd.offsets.MonthEnd(0))
        if b < tum["gun"].min() or a > bit:
            continue
        o = an.ozet(tum, max(a, tum["gun"].min()).date(), min(b, bit).date())
        for k in out:
            out[k].append(o[k])
    return out


def haftalik_net(tum):
    s = tum.groupby("gun")["net"].sum().reindex(pd.date_range(tum["gun"].min(), tum["gun"].max()), fill_value=0)
    n = len(s) // 7
    return s.values[: n * 7].reshape(n, 7).sum(axis=1)


def baz_tahmin30(tum):
    """Önümüzdeki 30 gün için baz tahmin (sönümlü trend) ve geri test hatası."""
    w = haftalik_net(tum)
    f = f_holt(w, 5)
    baz = sum(f[:4]) + f[4] * (30 - 28) / 7
    hata = hata_t = 0.0
    for t in range(max(12, len(w) - 16), len(w) - 3):
        hata += abs(w[t:t + 4].sum() - sum(f_holt(w[:t], 4)))
        hata_t += w[t:t + 4].sum()
    return baz, (hata / hata_t if hata_t else 0.25)


def yavas_urunler(tum):
    bit = tum["gun"].max()
    q = tum.groupby("Description")["Quantity"].sum()
    q90 = tum[tum["gun"] > bit - pd.Timedelta(days=90)].groupby("Description")["Quantity"].sum()
    qp = tum[(tum["gun"] <= bit - pd.Timedelta(days=90)) & (tum["gun"] > bit - pd.Timedelta(days=180))].groupby("Description")["Quantity"].sum()
    d = pd.DataFrame({"q": q}).join(q90.rename("q90")).join(qp.rename("qp")).fillna(0)
    sl = d[(d["q"] >= 200) & (d["qp"] >= 100) & (d["q90"] < 0.3 * d["qp"])].copy()
    g = tum[tum["Description"].isin(sl.index)].groupby("Description").agg(net=("net", "sum"), gross=("gross", "sum"), qq=("Quantity", "sum"))
    sl["d"] = (1 - g["net"] / g["gross"]).reindex(sl.index)
    sl["pr"] = (g["net"] / g["qq"]).reindex(sl.index)
    return sl.sort_values("q", ascending=False)


# ======================= VERİ KALİTESİ =======================
def norm_asimi(tum, esik=0.10, min_satir=100):
    oc = an.siparis_kategori(tum)
    med = oc.groupby("Category")["indirim"].median().rename("md")
    oc = oc.join(med, on="Category")
    oc["sapma"] = oc["indirim"] - oc["md"]
    oc["asan"] = oc["sapma"] > esik
    oc["fazla"] = np.where(oc["asan"], oc["sapma"] * oc["g"], 0.0)
    k = oc.groupby("Category").agg(n=("asan", "size"), asan=("asan", "sum"), md=("md", "first"), fazla=("fazla", "sum"))
    k = k[k["n"] >= min_satir]
    k["pay"] = k["asan"] / k["n"]
    return oc, k.sort_values("pay", ascending=False)
