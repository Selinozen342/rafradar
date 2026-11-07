"""RafBot: sağ altta yüzen sohbet düğmesi. Cevaplar sayfanın hesapladığı sayılardan gelir."""
import re
import streamlit as st

ONERILER = ["Ciro neden düştü?", "Hangi segmente ne yapmalı?", "Fazla indirim ne kadar?", "Kimi aramalıyım?"]
YEDEK = ("Ciro, indirim, segment, churn, birlikte alınanlar ve şüpheli sipariş hakkında soru sorabilirsin. "
         "Cevaplar o an seçili tarih aralığındaki veriden gelir.")


def cevapla(soru: str, f: dict) -> str:
    t = soru.lower().replace("İ", "i").replace("I", "ı")
    kurallar = [
        (r"neden|düştü|düşüş|köprü|azaldı|arttı", f.get("kopru")),
        (r"churn|kaybed|riskli|risk|ara", f.get("churn")),
        (r"segment|pareto|vip|bayi", f.get("segment")),
        (r"fazla indirim|iskonto|indirim|sapma|şüpheli", f.get("indirim")),
        (r"birlikte|best|çok satan|sepet", f.get("birlikte")),
        (r"pazartesi|hafta|gün", f.get("gun")),
        (r"ciro|satış|satis", f.get("ciro")),
    ]
    for kalip, cevap in kurallar:
        if cevap and re.search(kalip, t):
            return cevap
    return YEDEK


def rafbot(bilgi: dict):
    """bilgi: sayfanın hesapladığı hazır cümleler (kopru, churn, segment, indirim, birlikte, gun, ciro)."""
    ss = st.session_state
    ss.setdefault("rb_mesajlar", [])
    with st.container(key="rafbot"):
        with st.popover("💬"):
            st.markdown("**RafBot**")
            st.caption("Merhaba, ben RafBot. Ciro, indirim, segment ve churn hakkında sorabilirsin.")
            kutu = st.container(height=260)
            for rol, metin in ss["rb_mesajlar"][-12:]:
                kutu.chat_message("user" if rol == "u" else "assistant").write(metin)
            soru = None
            for i, o in enumerate(ONERILER):
                if st.button(o, key=f"rb_o{i}", use_container_width=True):
                    soru = o
            with st.form("rb_form", clear_on_submit=True):
                yaz = st.text_input("Sorunu yaz", label_visibility="collapsed", placeholder="Sorunu yaz…")
                if st.form_submit_button("Gönder") and yaz.strip():
                    soru = yaz.strip()
            if soru:
                ss["rb_mesajlar"] += [("u", soru), ("b", cevapla(soru, bilgi))]
                st.rerun()
