# RafRadar

B2B kitap/kırtasiye dağıtıcısı için karar destek dashboard'u (ISL 533 Veri Madenciliği, HW1).

Uygulama açılınca önce veri dosyası yüklenir (.xlsx, .csv veya .parquet), sonra sayfalar açılır.

**Canlı dashboard:** _Streamlit Cloud linki buraya eklenecek_

## Sayfalar
| Dosya | Sayfa | Sorumlu |
|---|---|---|
| `views/yukle.py` | Veri yükle | Selin |
| `views/satis.py` | Satış & Fiyat | Selin |
| `views/yonetici.py` | Yönetici Özeti | |
| `views/pazarlama.py` | Pazarlama & Müşteri | |
| `views/tedarik.py` | Tedarik Zinciri | |
| `views/kalite.py` | Veri Kalitesi | |

## Yüklenecek dosyadaki sütunlar
`InvoiceNo, CustomerID, InvoiceDate, Description, Category, City, Quantity, UnitPrice, NetPrice`

## Yerelde çalıştırma
```
pip install -r requirements.txt
streamlit run streamlit_app.py
```
