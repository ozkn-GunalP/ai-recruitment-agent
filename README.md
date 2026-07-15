# 🧑‍💼 AI Recruitment Agent

CV'leri indeksleyip iş ilanına en uygun adayları bulan, yapılandırılmış rapor üreten bir AI aracı.

## Hızlı Başlangıç

```bash
# 1. Repo'yu klonla
git clone https://github.com/KULLANICI_ADIN/ai-recruitment-agent.git
cd ai-recruitment-agent

# 2. Sanal ortam
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Bağımlılıklar
pip install -r requirements.txt

# 4. Secrets dosyasını oluştur
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# secrets.toml dosyasını aç ve kendi değerlerini yaz

# 5. Çalıştır
streamlit run app.py
```

## Streamlit Cloud'a Deploy

1. Repo'yu GitHub'a push et
2. [share.streamlit.io](https://share.streamlit.io) → "New app" → repo'nu seç
3. **App settings → Secrets** kısmına `secrets.toml` içeriğini yapıştır
4. Deploy

## Secrets Açıklaması

| Anahtar | Zorunlu | Açıklama |
|---|---|---|
| `OPENROUTER_API_KEY` | ✅ | OpenRouter API anahtarın |
| `APP_PASSWORD` | ✅ | Uygulamaya erişim parolası |
| `CHROMA_HOST` | ❌ | Hosted ChromaDB adresi (yoksa yerel dosya kullanılır) |
| `CHROMA_API_KEY` | ❌ | Hosted ChromaDB API anahtarı |

## Orijinalden Farklar

| # | İyileştirme |
|---|---|
| 1 | API anahtarı koddan çıkarıldı → `st.secrets` |
| 2 | Parola koruması eklendi |
| 3 | LLM çağrısında retry + timeout + 3 modelli fallback zinciri |
| 4 | Dosya adı yerine içerik hash'i ile tekilleştirme |
| 5 | 1000 karakter sınırı → 3000 karakter (ayarlanabilir) |
| 6 | PDF desteği eklendi (pdfplumber) |
| 7 | Serbest metin → yapılandırılmış JSON çıktı (puan, kanıt, beceri listesi) |
| 8 | Opsiyonel hosted ChromaDB bağlantı desteği |

## Proje Yapısı

```
ai-recruitment-agent/
├── .gitignore
├── .streamlit/
│   └── secrets.toml.example
├── README.md
├── requirements.txt
├── app.py                    # Ana uygulama
└── utils/
    ├── __init__.py
    ├── auth.py               # Parola koruması
    ├── resume_parser.py      # DOCX + PDF okuyucu
    └── llm_client.py         # LLM retry/fallback/JSON
```

## Lisans

MIT
