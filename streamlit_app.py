"""RafRadar - ana dosya. Önce veri yüklenir, sonra sayfalar açılır."""
import streamlit as st

st.set_page_config(page_title="RafRadar", page_icon="📚", layout="wide")

yukle = st.Page("views/yukle.py", title="Veri yükle", icon="📂", default=True)
yonetici = st.Page("views/yonetici.py", title="Yönetici Özeti", icon="🧭")
satis = st.Page("views/satis.py", title="Satış & Fiyat", icon="💰")
pazarlama = st.Page("views/pazarlama.py", title="Pazarlama & Müşteri", icon="🎯")
tedarik = st.Page("views/tedarik.py", title="Tedarik Zinciri", icon="📦")
kalite = st.Page("views/kalite.py", title="Veri Kalitesi", icon="🔍")

if "df" not in st.session_state:
    # Veri yüklenmeden yalnızca yükleme sayfası görünür
    pg = st.navigation([yukle], position="hidden")
else:
    pg = st.navigation([yonetici, satis, pazarlama, tedarik, kalite, yukle])
pg.run()
