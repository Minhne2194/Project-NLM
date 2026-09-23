import io
from pathlib import Path
from typing import Optional

import httpx
import streamlit as st

from src.config import settings
from src.interfaces.styles import GLOBAL_CSS

_API = settings.api_url


def _api(method: str, path: str, **kwargs):
    try:
        return httpx.request(method, f"{_API}{path}", timeout=300.0, **kwargs)
    except httpx.RequestError as e:
        st.error(f"Lỗi kết nối đến Backend API ({_API}): {e}")
        return None


def _sidebar():
    import time

    st.sidebar.title("📚 Simple NotebookLM")
    st.sidebar.caption("Hệ thống hỗ trợ học tập dựa trên RAG")

    # Upload PDF
    st.sidebar.subheader("📤 Tải lên tài liệu PDF")
    uploaded_file = st.sidebar.file_uploader("Chọn file PDF", type=["pdf"])
    if uploaded_file is not None:
        if st.sidebar.button("🚀 Index tài liệu này", use_container_width=True):
            with st.sidebar.status("Đang phân đoạn, vector hóa và lưu trữ..."):
                files = {
                    "file": (
                        uploaded_file.name,
                        uploaded_file.getvalue(),
                        "application/pdf",
                    )
                }
                resp = _api("POST", "/upload", files=files)
                if resp and resp.status_code == 200:
                    data = resp.json()
                    st.sidebar.success(
                        f"✅ Đã nạp thành công {data['chunks_indexed']} chunks từ '{data['filename']}'!"
                    )
                    time.sleep(1)
                    st.rerun()
                else:
                    err_msg = resp.text if resp else "Không phản hồi"
                    st.sidebar.error(f"Lỗi khi tải file: {err_msg}")

    st.sidebar.markdown("---")
    st.sidebar.subheader("🗂️ Danh sách tài liệu")
    docs_resp = _api("GET", "/documents")
    doc_list = docs_resp.json() if docs_resp and docs_resp.status_code == 200 else []

    filenames = [d["filename"] for d in doc_list]

    if doc_list:
        for doc in doc_list:
            st.sidebar.text(f"• {doc['filename']} ({doc['total_pages']} trang, {doc['total_chunks']} chunks)")
    else:
        st.sidebar.info("Chưa có tài liệu nào được index.")

    st.sidebar.markdown("---")
    st.sidebar.subheader("🎯 Phạm vi ngữ cảnh")
    scope_option = st.sidebar.selectbox(
        "Lựa chọn tài liệu:",
        ["Toàn bộ tài liệu"] + filenames,
    )

    page_filter: Optional[int] = None
    selected_filename: Optional[str] = None

    if scope_option != "Toàn bộ tài liệu":
        selected_filename = scope_option
        use_page = st.sidebar.checkbox("Lọc theo số trang cụ thể")
        if use_page:
            page_filter = st.sidebar.number_input("Trang số", min_value=1, value=1, step=1)

    return selected_filename, page_filter


def _build_filter(filename: Optional[str], page: Optional[int]) -> Optional[dict]:
    if not filename and not page:
        return None
    f = {}
    if filename:
        f["filename"] = filename
    if page:
        f["page"] = page
    return f


def _tab_chat(filename: Optional[str], page: Optional[int]):
    st.header("💬 Hỏi đáp có căn cứ trích dẫn")
    st.write("Hệ thống sẽ tìm kiếm thông tin liên quan từ tài liệu đã nạp và trả lời có gắn nhãn nguồn.")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if "citations" in msg and msg["citations"]:
                with st.expander("📌 Nguồn trích dẫn"):
                    for c in msg["citations"]:
                        st.markdown(f"- **[{c['source_marker']}]** `{c['filename']}` - Trang {c['page']}")

    query = st.chat_input("Nhập câu hỏi về tài liệu...")
    if query:
        st.session_state.chat_history.append({"role": "user", "content": query})
        with st.chat_message("user"):
            st.markdown(query)

        payload = {
            "question": query,
            "filters": _build_filter(filename, page),
        }
        with st.chat_message("assistant"):
            with st.spinner("Đang truy xuất ngữ cảnh và tạo sinh phản hồi..."):
                resp = _api("POST", "/ask", json=payload)
                if resp and resp.status_code == 200:
                    ans_data = resp.json()
                    st.markdown(ans_data["answer"])

                    citations = ans_data.get("citations", [])
                    if citations:
                        with st.expander("📌 Nguồn trích dẫn"):
                            for c in citations:
                                st.markdown(f"- **[{c['source_marker']}]** `{c['filename']}` - Trang {c['page']}")

                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": ans_data["answer"],
                        "citations": citations,
                    })
                else:
                    st.error("Không thể kết nối hoặc nhận phản hồi từ hệ thống.")


def _tab_summary(filename: Optional[str], page: Optional[int]):
    st.header("📝 Tóm tắt nội dung thông minh")
    st.caption("Tự động áp dụng Single-pass hoặc Map-Reduce đối với văn bản dài.")

    custom_query = st.text_input("Yêu cầu tóm tắt trọng tâm (tùy chọn):", placeholder="Ví dụ: Tóm tắt phần phương pháp huấn luyện")
    
    if st.button("Tạo bản tóm tắt", type="primary"):
        payload = {
            "document": filename,
            "query": custom_query.strip() or None,
            "filters": _build_filter(filename, page),
        }
        with st.spinner("Đang tổng hợp thông tin..."):
            resp = _api("POST", "/summarize", json=payload)
            if resp and resp.status_code == 200:
                data = resp.json()
                st.subheader("Bản tóm tắt")
                st.write(data["summary"])

                if data.get("key_points"):
                    st.subheader("💡 Các ý chính cốt lõi:")
                    for kp in data["key_points"]:
                        st.markdown(f"- {kp}")

                if data.get("citations"):
                    with st.expander("Trích dẫn tài liệu"):
                        for c in data["citations"]:
                            st.markdown(f"- **[{c['source_marker']}]** `{c['filename']}` - Trang {c['page']}")

                # Download
                summary_md = f"# Tóm tắt\n\n{data['summary']}\n\n## Ý chính\n" + "\n".join(f"- {kp}" for kp in data.get("key_points", []))
                st.download_button("📥 Tải về Markdown", summary_md, file_name="summary.md")
            else:
                st.error("Lỗi khi tạo bản tóm tắt.")


def _tab_quiz(filename: Optional[str], page: Optional[int]):
    st.header("🧩 Tạo câu hỏi trắc nghiệm (Quiz)")
    count = st.slider("Số lượng câu hỏi:", min_value=1, max_value=15, value=5)
    custom_query = st.text_input("Chủ đề tập trung (tùy chọn):", key="quiz_query")

    if st.button("Tạo Quiz", type="primary"):
        payload = {
            "document": filename,
            "query": custom_query.strip() or None,
            "filters": _build_filter(filename, page),
            "count": count,
        }
        with st.spinner("Đang trích xuất kiến thức và biên soạn câu hỏi..."):
            resp = _api("POST", "/quiz", json=payload)
            if resp and resp.status_code == 200:
                st.session_state.current_quiz = resp.json()
            else:
                st.error("Lỗi khi tạo bộ câu hỏi.")

    if "current_quiz" in st.session_state:
        quiz_data = st.session_state.current_quiz
        items = quiz_data.get("items", [])
        st.write(f"Đã tạo **{len(items)}** câu hỏi trắc nghiệm:")

        for i, item in enumerate(items, start=1):
            with st.container():
                st.markdown(f"**Câu {i}: {item['question']}**")
                user_choice = st.radio(
                    f"Lựa chọn cho câu {i}:",
                    [f"{chr(65+j)}. {opt}" for j, opt in enumerate(item["options"])],
                    key=f"q_{i}",
                    index=None,
                )
                with st.expander("Xem đáp án & giải thích"):
                    st.success(f"Đáp án đúng: **{chr(65 + item['correct_index'])}. {item['options'][item['correct_index']]}**")
                    st.info(f"Giải thích: {item['explanation']}")
                    if item.get("source_markers"):
                        st.caption(f"Nguồn: {', '.join(item['source_markers'])}")
                st.markdown("---")


def _tab_flashcards(filename: Optional[str], page: Optional[int]):
    st.header("🃏 Thẻ ghi nhớ (Flashcards)")
    count = st.slider("Số lượng flashcards:", min_value=1, max_value=20, value=8)
    custom_query = st.text_input("Chủ đề tập trung (tùy chọn):", key="fc_query")

    if st.button("Tạo Flashcards", type="primary"):
        payload = {
            "document": filename,
            "query": custom_query.strip() or None,
            "filters": _build_filter(filename, page),
            "count": count,
        }
        with st.spinner("Đang tạo thẻ ghi nhớ..."):
            resp = _api("POST", "/flashcards", json=payload)
            if resp and resp.status_code == 200:
                st.session_state.current_flashcards = resp.json()
            else:
                st.error("Lỗi khi tạo flashcards.")

    if "current_flashcards" in st.session_state:
        fc_data = st.session_state.current_flashcards
        cards = fc_data.get("cards", [])
        st.write(f"Đã tạo **{len(cards)}** thẻ ghi nhớ:")

        cols = st.columns(2)
        for i, card in enumerate(cards):
            col = cols[i % 2]
            with col:
                st.markdown(
                    f"""
                    <div class="flashcard-box">
                        <div style="font-size: 12px; color: #818cf8; font-weight: 600; margin-bottom: 6px;">
                            THẺ #{i+1} • {card.get('topic') or 'Kiến thức'}
                        </div>
                        <div class="flashcard-front">
                            {card['front']}
                        </div>
                        <details style="cursor: pointer;">
                            <summary style="color: #38bdf8; font-weight: 500;">👁️ Bấm để xem đáp án</summary>
                            <div class="flashcard-back" style="margin-top: 10px;">
                                {card['back']}
                            </div>
                        </details>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


def run():
    st.set_page_config(
        page_title="Simple NotebookLM",
        page_icon="📖",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

    filename, page = _sidebar()
    tabs = st.tabs(["💬 Hỏi đáp", "📝 Tóm tắt", "🧩 Quiz", "🃏 Flashcards"])

    with tabs[0]:
        _tab_chat(filename, page)
    with tabs[1]:
        _tab_summary(filename, page)
    with tabs[2]:
        _tab_quiz(filename, page)
    with tabs[3]:
        _tab_flashcards(filename, page)


if __name__ == "__main__":
    run()
