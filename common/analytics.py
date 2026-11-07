"""Satış sayfasının hesapları. Hepsi saf pandas: veri nereden gelirse gelsin çalışır."""
import itertools
import numpy as np
import pandas as pd


def araliga_kes(df, a, b):
    return df[(df["gun"] >= pd.Timestamp(a)) & (df["gun"] <= pd.Timestamp(b))]


def ozet(df, a, b):
    """Bir tarih aralığının özet göstergeleri (toplam + günlük ortalama)."""
    m = araliga_kes(df, a, b)
    gun = (pd.Timestamp(b) - pd.Timestamp(a)).days + 1
    net, brut, adet = m["net"].sum(), m["gross"].sum(), m["Quantity"].sum()
    sip = m["InvoiceNo"].nunique()
    g = m.groupby("gun").agg(net=("net", "sum"), gross=("gross", "sum"), q=("Quantity", "sum"),
                             o=("InvoiceNo", "nunique"), c=("CustomerID", "nunique"))
    g1 = g[g["o"] > 0]
    g2 = g[g["gross"] > 0]
    return dict(
        gun=gun, net=net, gross=brut, q=adet, ord=sip, musteri=m["CustomerID"].nunique(), dcust=g["c"].sum() / gun,
        dnet=net / gun, dord=sip / gun, dq=adet / gun,
        b=adet / sip if sip else 0, basket=net / sip if sip else 0,
        disc=1 - net / brut if brut else 0, L=brut / adet if adet else 0,
        dbq=(g1["q"] / g1["o"]).mean() if len(g1) else 0,
        dbt=(g1["net"] / g1["o"]).mean() if len(g1) else 0,
        dd=(1 - g2["net"] / g2["gross"]).mean() if len(g2) else 0,
    )


def kopru(S, C):
    """Günlük ciro farkını 4 nedene böler (sırayla değiştirerek)."""
    N = lambda o, b, L, d: o * b * L * (1 - d)
    n0 = N(C["dord"], C["b"], C["L"], C["disc"])
    n1 = N(S["dord"], C["b"], C["L"], C["disc"])
    n2 = N(S["dord"], S["b"], C["L"], C["disc"])
    n3 = N(S["dord"], S["b"], S["L"], C["disc"])
    n4 = N(S["dord"], S["b"], S["L"], S["disc"])
    return [n1 - n0, n2 - n1, n3 - n2, n4 - n3]


def urun_listesi(df, n=20):
    return df.groupby("Description")["net"].sum().sort_values(ascending=False).head(n).index.tolist()


def urun_referans(tum, urun, S_gun, ca, cb):
    """Karşılaştırma dönemindeki ürün satışı, seçili dönem uzunluğuna ölçeklenir."""
    p = tum[tum["Description"] == urun]
    c = araliga_kes(p, ca, cb)
    cgun = (pd.Timestamp(cb) - pd.Timestamp(ca)).days + 1
    fb = False
    if c["Quantity"].sum() > 0:
        q, n, g, f = c["Quantity"].sum(), c["net"].sum(), c["gross"].sum(), S_gun / cgun
    else:
        gun_yil = (tum["gun"].max() - tum["gun"].min()).days + 1
        q, n, g, f, fb = p["Quantity"].sum(), p["net"].sum(), p["gross"].sum(), S_gun / gun_yil, True
    # ürünün yaygın indirim üst sınırı: satırların adetle ağırlıklı %95'lik dilimi
    d = p[["disc", "Quantity"]].sort_values("disc")
    cum = d["Quantity"].cumsum() / d["Quantity"].sum() if len(d) else d["Quantity"]
    cap = float(d["disc"][cum >= 0.95].iloc[0]) if len(d) else 0.0
    mx = float(d["disc"].max()) if len(d) else 0.0
    return dict(q=q * f, n=n * f, g=g * f, fb=fb, cap=cap, mx=mx)


def hafta_kategori(m, ilk=6):
    top = m.groupby("Category")["net"].sum().sort_values(ascending=False).head(ilk).index
    x = m[m["Category"].isin(top)]
    ciro = x.pivot_table(index="Category", columns="dow", values="net", aggfunc="sum", fill_value=0)
    sip = x.groupby(["Category", "dow"])["InvoiceNo"].nunique().unstack(fill_value=0)
    out = {}
    for ad, t in (("Ciro payı", ciro), ("Sipariş adedi", sip)):
        t = t.reindex(index=top, columns=range(7), fill_value=0)
        out[ad] = t.div(t.sum(axis=1).replace(0, np.nan), axis=0).fillna(0) * 100
    return out


def _cift_say(m, ust=300, max_satir=30):
    satir = m[["InvoiceNo", "Description"]].drop_duplicates()
    c = satir.groupby("InvoiceNo").size()
    satir = satir[satir["InvoiceNo"].isin(c[c <= max_satir].index)]
    pop = satir["Description"].value_counts()
    satir = satir[satir["Description"].isin(pop.head(ust).index)]
    x = satir.merge(satir, on="InvoiceNo")
    x = x[x["Description_x"] < x["Description_y"]]
    pc = x.groupby(["Description_x", "Description_y"]).size().sort_values(ascending=False)
    return pc


def birlikte(m, ilk=3):
    """En sık birlikte geçen ürün çiftleri."""
    if m.empty:
        return []
    pc = _cift_say(m)
    siparis = m.groupby("Description")["InvoiceNo"].nunique()
    out = []
    for (x, y), n in pc.head(ilk).items():
        a, b = (x, y) if siparis[x] >= siparis[y] else (y, x)
        out.append(dict(a=a, b=b, n=int(n), oran=n / siparis[a]))
    return out


def en_cok_satanlar(m, ilk=5):
    """Best seller'lar ve en çok birlikte alındıkları ürün."""
    if m.empty:
        return pd.DataFrame()
    top = m.groupby("Description")["Quantity"].sum().sort_values(ascending=False).head(ilk)
    pc = _cift_say(m)
    siparis = m.groupby("Description")["InvoiceNo"].nunique()
    rows = []
    for i, (u, q) in enumerate(top.items(), 1):
        ort, n = "—", 0
        a = pc[pc.index.get_level_values(0) == u]
        b = pc[pc.index.get_level_values(1) == u]
        adaylar = [(k[1], v) for k, v in a.items()] + [(k[0], v) for k, v in b.items()]
        if adaylar:
            ort, n = max(adaylar, key=lambda t: t[1])
        rows.append({"#": i, "Best seller": u, "Adet": int(q), "Birlikte en çok alınan ürün": ort,
                     "Birlikte alma oranı": n / siparis[u] if siparis[u] else 0})
    return pd.DataFrame(rows)


def pareto(m, anahtar):
    """Ciroya göre A (%80), B (%15), C (%5) segmentleri. anahtar: 'CustomerID' veya 'Description'."""
    s = m.groupby(anahtar)["net"].sum().sort_values(ascending=False)
    if s.empty:
        return s.to_frame("net").assign(seg="A", kum=0.0)
    kum = s.cumsum() / s.sum()
    seg = np.where(kum <= 0.8, "A", np.where(kum <= 0.95, "B", "C"))
    seg[0] = "A"
    return pd.DataFrame({"net": s, "kum": kum, "seg": seg})


def musteri_ozeti(tum, m, pc, bitis):
    """Her müşteri için: segment, il, tüm zamanlardaki sipariş sayısı, son sipariş ve pasif gün.
    Segment seçili aralıktan gelir; davranış (sipariş sayısı, pasiflik) veri bitişine göre ölçülür."""
    ids = pc.index
    h = tum[tum["CustomerID"].isin(ids)]
    g = h.groupby("CustomerID")
    il = g["City"].agg(lambda s: s.mode().iloc[0] if s.notna().any() and len(s.mode()) else "")
    t = pc.copy()
    t["il"] = il
    t["siparis"] = g["InvoiceNo"].nunique()
    t["son"] = g["gun"].max()
    t["pasif"] = (pd.Timestamp(bitis) - t["son"]).dt.days
    return t


# ---------------- churn modeli ----------------
def _ozellikler(od, kes):
    h = od[od["d"] <= kes].sort_values("d")
    h = h.assign(aralik=h.groupby("CustomerID")["d"].diff().dt.days)
    f = h.groupby("CustomerID").agg(son=("d", "max"), ilk=("d", "min"), sik=("InvoiceNo", "nunique"),
                                    para=("v", "sum"), aralik=("aralik", "mean"))
    f["rec"] = (kes - f["son"]).dt.days
    f["yas"] = (kes - f["ilk"]).dt.days + 1
    f["f90"] = h[h["d"] > kes - pd.Timedelta(days=90)].groupby("CustomerID")["InvoiceNo"].nunique().reindex(f.index).fillna(0)
    f["hiz"] = f["sik"] / f["yas"] * 30
    f["aov"] = f["para"] / f["sik"]
    f["aralik"] = f["aralik"].fillna(f["yas"])
    f["rec_gap"] = f["rec"] / (f["aralik"] + 1)
    return f.drop(columns=["son", "ilk"])


def churn_modeli(df):
    """Tüm veriyle zaman sıralı eğitim; veri bitişi itibarıyla 30 gün sipariş vermeme olasılığı."""
    od = df.groupby(["CustomerID", "InvoiceNo"]).agg(d=("gun", "first"), v=("net", "sum")).reset_index()
    bit = od["d"].max()
    f_son = _ozellikler(od, bit)
    span = ((bit - od.groupby("CustomerID")["d"].min()).dt.days + 1).reindex(f_son.index)
    net = df.groupby("CustomerID")["net"].sum().reindex(f_son.index)
    m30 = net / np.maximum(span, 30) * 30
    kesimler = pd.date_range(od["d"].min() + pd.Timedelta(days=90), bit - pd.Timedelta(days=30), freq="30D")
    auc = None
    try:
        from sklearn.ensemble import GradientBoostingClassifier
        from sklearn.metrics import roc_auc_score
        parca = []
        for k in kesimler:
            f = _ozellikler(od, k)
            gel = od[(od["d"] > k) & (od["d"] <= k + pd.Timedelta(days=30))]["CustomerID"].unique()
            f["y"] = (~f.index.isin(gel)).astype(int)
            f["kes"] = k
            parca.append(f)
        T = pd.concat(parca)
        cols = [c for c in T.columns if c not in ("y", "kes")]
        esik = bit - pd.Timedelta(days=120)
        trn, tst = T[T["kes"] < esik], T[T["kes"] >= esik]
        if len(trn) > 100 and trn["y"].nunique() > 1 and len(tst) and tst["y"].nunique() > 1:
            mdl = GradientBoostingClassifier(random_state=0).fit(trn[cols], trn["y"])
            auc = float(roc_auc_score(tst["y"], mdl.predict_proba(tst[cols])[:, 1]))
        mdl = GradientBoostingClassifier(random_state=0).fit(T[cols], T["y"])
        p = mdl.predict_proba(f_son[cols])[:, 1]
    except Exception:
        # model kurulamazsa: son siparişten geçen süre / olağan aralık oranından basit olasılık
        p = 1 - np.exp(-f_son["rec_gap"].values / 2)
    out = pd.DataFrame({"p": p, "m30": m30.values}, index=f_son.index)
    out["risk"] = pd.cut(out["p"], [-1, .4, .7, 1.01], labels=["Düşük", "Orta", "Yüksek"])
    return out, auc


# ---------------- şüpheli sipariş radarı ----------------
def siparis_kategori(df):
    oc = (df.dropna(subset=["Category"]).groupby(["InvoiceNo", "Category"])
            .agg(musteri=("CustomerID", "first"), tarih=("gun", "first"), satir=("Quantity", "size"),
                 q=("Quantity", "sum"), g=("gross", "sum"), n=("net", "sum")).reset_index())
    oc["indirim"] = 1 - oc["n"] / oc["g"]
    return oc


def supheli(tum, m, tur):
    """Kategorinin kendi medyanından sapan siparişler. Medyanlar tüm veriden, liste seçili aralıktan."""
    ref = siparis_kategori(tum)
    med = ref.groupby("Category").agg(md=("indirim", "median"), mq=("q", "median"))
    oc = siparis_kategori(m).join(med, on="Category")
    oc["sapma"] = oc["indirim"] - oc["md"]
    oc["fazla"] = oc["sapma"] * oc["g"]
    oc["qr"] = oc["q"] / oc["mq"]
    if tur == "indirim":
        x = oc[oc["sapma"] > 0.10].sort_values("fazla", ascending=False)
    else:
        x = oc[(oc["qr"] >= 20) & (oc["n"] >= 3000)].sort_values("n", ascending=False)
    return x, oc
