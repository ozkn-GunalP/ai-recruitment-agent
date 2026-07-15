import streamlit as st
import chromadb

from utils.auth import check_password
from utils.resume_parser import parse_resume
from utils.llm_client import analyze_candidates

# ─── Sayfa ayarları ───
st.set_page_config(page_title="AI Recruitment Agent", page_icon="🧑‍💼", layout="wide")

# ─── Parola koruması ───
if not check_password():
    st.stop()

# ─── Başlık ───
st.title("🧑‍💼 AI Recruitment Agent")
st.markdown("Upload resumes and find the best candidate for your job description.")


# ─── ChromaDB bağlantısı ───
@st.cache_resource
def get_chroma_collection():
    """ChromaDB koleksiyonunu döner. Hosted bağlantı varsa onu kullanır."""
    host = st.secrets.get("CHROMA_HOST")

    if host:
        import chromadb.config

        chroma_api_key = st.secrets.get("CHROMA_API_KEY", "")
        settings = chromadb.config.Settings(
            chroma_api_impl="rest",
            chroma_server_host=host,
            chroma_server_headers={"Authorization": f"Bearer {chroma_api_key}"}
            if chroma_api_key
            else {},
        )
        client = chromadb.HttpClient(host=host, settings=settings)
    else:
        client = chromadb.PersistentClient(path="./resumes_db")
        st.sidebar.caption(
            "⚠️ Yerel depolama kullanılıyor — Streamlit Cloud'da veriler "
            "uygulama yeniden başladığında silinebilir."
        )

    return client.get_or_create_collection("resumes")


col = get_chroma_collection()


# ─── Sidebar: CV Yükleme ───
with st.sidebar:
    st.header("📁 Upload Resumes")
    uploaded_files = st.file_uploader(
        "Upload resumes (DOCX or PDF)",
        type=["docx", "pdf"],
        accept_multiple_files=True,
    )

    if uploaded_files:
        if st.button("📥 Index Resumes", use_container_width=True):
            indexed = 0
            skipped = 0

            progress = st.progress(0, text="İndeksleniyor...")
            for i, f in enumerate(uploaded_files):
                try:
                    text, content_hash = parse_resume(f)
                    if not text.strip():
                        st.warning(f"⚠️ {f.name} — boş içerik, atlandı.")
                        skipped += 1
                        continue

                    # İçerik hash'ine göre dedup (aynı ad, farklı içerik → yeni kayıt)
                    doc_id = f"resume_{content_hash}"
                    existing = col.get(ids=[doc_id])

                    if existing["ids"]:
                        skipped += 1
                    else:
                        col.add(
                            ids=[doc_id],
                            documents=[text],
                            metadatas=[{"src": f.name, "hash": content_hash}],
                        )
                        indexed += 1

                except Exception as e:
                    st.error(f"❌ {f.name} — {e}")

                progress.progress((i + 1) / len(uploaded_files))

            progress.empty()
            st.success(f"✅ {indexed} yeni CV indekslendi, {skipped} zaten mevcuttu.")

    st.divider()
    st.metric("📄 Total Resumes", col.count())

# ─── Ana alan: İş İlanı ───
st.header("📋 Job Description")
job_description = st.text_area(
    "Enter the job description",
    height=200,
    placeholder=(
        "We are looking for a Senior Data Scientist with:\n"
        "- 5+ years of experience in machine learning\n"
        "- Strong Python and SQL skills\n"
        "- Experience with NLP and deep learning\n"
        "- Team leadership experience"
    ),
)

n_candidates = st.slider("Number of candidates to compare", 1, 5, 3)

# ─── Analiz ───
if st.button("🔍 Find Best Candidate", type="primary", use_container_width=True):
    if not job_description.strip():
        st.warning("Please enter a job description.")
    elif col.count() == 0:
        st.warning("Please upload and index resumes first.")
    else:
        with st.spinner("Analyzing candidates..."):
            results = col.query(
                query_texts=[job_description],
                n_results=min(n_candidates, col.count()),
            )

            candidates = []
            for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
                candidates.append({"name": meta["src"], "text": doc})

            analysis = analyze_candidates(job_description, candidates)

        st.divider()
        st.header("🏆 Analysis Result")

        # ─── Hata durumu ───
        if analysis.get("error"):
            st.error(f"Analiz başarısız: {analysis['error']}")

        # ─── JSON parse başarısız — ham metin göster ───
        elif analysis.get("_parse_failed"):
            st.warning(
                "Model yapılandırılmış çıktı üretemedi, ham metin gösteriliyor."
            )
            st.markdown(analysis.get("raw_text", ""))

        # ─── Başarılı yapılandırılmış çıktı ───
        else:
            # İş özeti
            st.subheader("📋 Job Summary")
            st.write(analysis.get("job_summary", ""))

            # Aday kartları
            for c in analysis.get("candidates", []):
                rank = c.get("rank", "?")
                score = c.get("match_score", "?")
                icon = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else "📄"

                with st.expander(
                    f"{icon} #{rank} — {c.get('file', 'Bilinmiyor')} — Eşleşme: %{score}",
                    expanded=(rank == 1),
                ):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**✅ Güçlü Yönler**")
                        for s in c.get("strengths", []):
                            st.markdown(f"- {s}")

                        st.markdown("**🎯 Eşleşen Beceriler**")
                        for s in c.get("matching_skills", []):
                            st.markdown(f"- {s}")

                    with col2:
                        st.markdown("**⚠️ Zayıf Yönler**")
                        for w in c.get("weaknesses", []):
                            st.markdown(f"- {w}")

                        st.markdown("**📝 Deneyim Değerlendirmesi**")
                        st.write(c.get("experience_match", ""))

                    st.markdown("**📌 Kanıt (CV'den)**")
                    st.info(c.get("evidence", "Belirtilmedi"))

            # Nihai öneri
            st.subheader("💡 Final Recommendation")
            st.success(analysis.get("recommendation", ""))

            # Hangi model kullanıldı
            model_used = analysis.get("_model_used", "bilinmiyor")
            st.caption(f"Model: {model_used}")

        # ─── Rapor indirme ───
        import json as _json

        report_json = _json.dumps(analysis, ensure_ascii=False, indent=2)
        st.download_button(
            label="📥 Download Report (JSON)",
            data=report_json,
            file_name="recruitment_report.json",
            mime="application/json",
        )
