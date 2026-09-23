# 📚 Simple NotebookLM (RAG-based Learning System)

Hệ thống hỗ trợ học tập và nghiên cứu thông minh từ tài liệu PDF cá nhân dựa trên kiến trúc **RAG (Retrieval-Augmented Generation)**.

Dự án cung cấp các tính năng:
- **💬 Hỏi đáp có căn cứ (Grounded Q&A):** Trả lời câu hỏi trực tiếp dựa trên nội dung tài liệu, tự động đính kèm nguồn trích dẫn `[S1], [S2], ...` theo từng file và số trang.
- **📝 Tóm tắt thông minh:** Tự động áp dụng **Single-pass** (tài liệu ngắn) hoặc **Map-Reduce** (tài liệu dài) để rút trích bản tóm tắt và danh sách các ý chính cốt lõi.
- **🧩 Tạo Quiz & Flashcards:** Tự động tạo câu hỏi trắc nghiệm (4 phương án, đáp án đúng, giải thích chi tiết) và thẻ ghi nhớ ôn tập (mặt trước/mặt sau/gợi ý), validate chặt chẽ qua Pydantic.
- **🖥️ Giao diện đa kênh:** 
  - **Streamlit Web UI** trực quan, hiện đại (`src/interfaces/ui.py`).
  - **FastAPI REST API** chuẩn hóa với tài liệu tương tác Swagger (`src/interfaces/api.py`).
  - **Typer CLI** tiện lợi cho terminal (`src/interfaces/cli.py`).
- **⚡ Tối ưu hóa truy xuất:** Phân đoạn linh hoạt Recursive Chunking kết hợp mô hình Cross-Encoder Reranker (`BAAI/bge-reranker-v2-m3`).

---

## 🚀 HƯỚNG DẪN CHẠY HỆ THỐNG CHI TIẾT (QUICKSTART)

Để chạy trọn vẹn hệ thống (gồm Backend API và Giao diện Web Streamlit), bạn thực hiện theo 3 bước đơn giản dưới đây:

### Bước 1: Cài đặt thư viện phụ thuộc

Mở Terminal trong thư mục dự án và chạy:
```bash
pip install -r requirements.txt
```

### Bước 2: Cấu hình Khóa API (.env)

Tạo hoặc chỉnh sửa file `.env` ở thư mục gốc của dự án:
```env
# Nhập khóa Google Gemini API của bạn (nếu dùng backend Gemini)
GOOGLE_API_KEY=AIzaSy...your_gemini_api_key...

# Cấu hình backend LLM: 'gemini' | 'hf_local' | 'vllm'
RAG_LLM_PROVIDER=gemini

# Cấu hình mô hình Embedding (chạy CPU: -1, GPU: 0)
RAG_EMBEDDING_MODEL=GreenNode/GreenNode-Embedding-Large-VN-Mixed-V1
RAG_HF_DEVICE=-1

# Cấu hình chunking & truy xuất
RAG_CHUNK_SIZE=1000
RAG_CHUNK_OVERLAP=150
RAG_TOP_K=5
RAG_API_URL=http://localhost:8000
```

> **Lưu ý:**
> - Nếu chưa có Google API Key, bạn có thể lấy miễn phí tại [Google AI Studio](https://aistudio.google.com/).
> - Nếu muốn dùng mô hình local trên máy (không cần internet/API key), đặt `RAG_LLM_PROVIDER=hf_local`.

---

### Bước 3: Khởi chạy ứng dụng

Hệ thống hoạt động theo mô hình Client - Server: Backend xử lý dữ liệu (FastAPI) và Frontend hiển thị (Streamlit).

#### 3.1. Khởi động Backend API (Terminal 1)
Mở cửa sổ Terminal thứ nhất và chạy:
```bash
python -m uvicorn src.interfaces.api:app --host 127.0.0.1 --port 8000 --reload
```
- Server API sẽ chạy tại: **http://localhost:8000**
- Tài liệu tương tác API (Swagger UI): **http://localhost:8000/docs**

#### 3.2. Khởi động Giao diện Web Streamlit (Terminal 2)
Mở cửa sổ Terminal thứ hai và chạy:
```bash
python -m streamlit run src/interfaces/ui.py
```
- Trình duyệt sẽ tự động mở trang web tại: **http://localhost:8501**

---

## 📖 HƯỚNG DẪN SỬ DỤNG CÁC TÍNH NĂNG TRÊN WEB UI

Truy cập vào **http://localhost:8501**:

1. **📤 Tải lên và Index tài liệu PDF**:
   - Ở thanh menu bên trái (Sidebar), bấm nút **"Browse files"** để chọn file PDF học tập của bạn (ví dụ file trong thư mục `docs/` hoặc `data/`).
   - Nhấn nút **"Index tài liệu này"**. Hệ thống sẽ đọc nội dung, chia nhỏ thành các đoạn chunk và lưu vector vào Qdrant database.
   - Sau khi nạp xong, tên file sẽ xuất hiện trong danh sách tài liệu.

2. **🎯 Chọn phạm vi truy vấn (Scope Filter)**:
   - Bạn có thể chọn tìm kiếm trên:
     - **Toàn bộ tài liệu**: Tìm kiếm tổng hợp trên tất cả các file PDF đã nạp.
     - **Một tài liệu cụ thể**: Chỉ tập trung vào file được chọn.
     - **Một trang cụ thể**: Nhập số trang cần tra cứu thông tin.

3. **💬 Tab Hỏi đáp (Grounded Q&A)**:
   - Nhập câu hỏi vào khung chat ở dưới cùng (ví dụ: *"LoRA là gì và hoạt động thế nào?"*, *"SFT giúp gì cho mô hình?"*).
   - Hệ thống phản hồi câu trả lời dựa trên tài liệu kèm theo mục **"📌 Nguồn trích dẫn"** hiển thị chi tiết tên file và số trang làm bằng chứng (`[S1]`, `[S2]`).

4. **📝 Tab Tóm tắt (Summary)**:
   - Bạn có thể nhập chủ đề trọng tâm cần tóm tắt hoặc để trống để tóm tắt tổng thể.
   - Bấm nút **"Tạo bản tóm tắt"**. Hệ thống tự động áp dụng chiến lược **Map-Reduce** nếu tài liệu dài để không bỏ sót thông tin.
   - Hỗ trợ nút **"📥 Tải về Markdown"** để lưu file tóm tắt về máy.

5. **🧩 Tab Tạo câu hỏi trắc nghiệm (Quiz)**:
   - Dùng thanh kéo để chọn số lượng câu hỏi mong muốn (1 - 15 câu).
   - Bấm **"Tạo Quiz"**.
   - Bạn có thể trực tiếp làm bài thi trắc nghiệm bằng cách chọn đáp án A, B, C, D và bấm **"Xem đáp án & giải thích"** để đối chiếu.

6. **🃏 Tab Thẻ ghi nhớ (Flashcards)**:
   - Chọn số lượng flashcard ôn tập cần tạo $\to$ bấm **"Tạo Flashcards"**.
   - Các thẻ ghi nhớ sẽ hiển thị dạng lưới: mặt trước ghi khái niệm/câu hỏi, bấm **"👁️ Bấm để xem đáp án"** để mở lời giải mặt sau.

---

## 💻 HƯỚNG DẪN SỬ DỤNG BẰNG GIAO DIỆN DÒNG LỆNH (CLI)

Ngoài Web UI, bạn có thể thực thi trực tiếp các tác vụ thông qua Terminal với Typer CLI:

```bash
# 1. Nạp (Index) toàn bộ file PDF trong thư mục data/ vào Qdrant
python -m src.interfaces.cli ingest

# Nạp lại từ đầu (xóa collection cũ trước khi nạp)
python -m src.interfaces.cli ingest --recreate

# 2. Đặt câu hỏi trực tiếp trên dòng lệnh
python -m src.interfaces.cli ask "Ý tưởng cốt lõi của LoRA là gì?"

# 3. Kiểm tra kết quả tìm kiếm Semantic Search (không tốn token gọi LLM)
python -m src.interfaces.cli debug-retrieval "Supervised Fine-Tuning" -k 3

# 4. Tóm tắt tài liệu và xuất kết quả ra file Markdown
python -m src.interfaces.cli summarize --fmt md --output "tom_tat.md"

# 5. Tạo bộ câu hỏi trắc nghiệm (5 câu)
python -m src.interfaces.cli quiz -c 5

# 6. Tạo thẻ ghi nhớ Flashcards và lưu ra file markdown
python -m src.interfaces.cli flashcards -c 8 -o "flashcards.md"
```

---

## 🔌 HƯỚNG DẪN SỬ DỤNG REST API

Backend FastAPI cung cấp đầy đủ các endpoint RESTful để tích hợp vào ứng dụng khác:

| Phương thức | Đường dẫn | Chức năng |
| :--- | :--- | :--- |
| `GET` | `/health` | Kiểm tra trạng thái hoạt động của hệ thống |
| `GET` | `/documents` | Lấy danh sách tài liệu đã index cùng số trang và số chunk |
| `POST` | `/ingest` | Kích hoạt nạp toàn bộ file trong thư mục `data/` |
| `POST` | `/upload` | Tải lên một file PDF và lập chỉ mục ngay lập tức |
| `POST` | `/ask` | Gửi câu hỏi và nhận câu trả lời có trích dẫn `[S1], [S2]` |
| `POST` | `/summarize` | Tạo bản tóm tắt nội dung kèm danh sách ý chính cốt lõi |
| `POST` | `/quiz` | Sinh câu hỏi trắc nghiệm 4 lựa chọn có đáp án chuẩn |
| `POST` | `/flashcards` | Sinh bộ thẻ ghi nhớ phục vụ ôn tập kiến thức |

*Xem chi tiết định dạng Request/Response tại Swagger UI:* **http://localhost:8000/docs**

---

## 📂 CẤU TRÚC THƯ MỤC DỰ ÁN

```text
Project-NLM/
├── data/                          # Chứa các file PDF học tập đầu vào
├── docs/                          # Tài liệu mô tả kiến trúc hệ thống
├── storage/qdrant/                # Cơ sở dữ liệu Vector Qdrant (lưu trữ cục bộ)
├── src/
│   ├── prompts/                   # Jinja2 prompt templates
│   │   ├── answer.jinja2          # Template hỏi đáp có trích dẫn
│   │   ├── summary_single.jinja2  # Template tóm tắt trực tiếp
│   │   ├── summary_map.jinja2     # Template tóm tắt từng phần (Map)
│   │   ├── summary_reduce.jinja2  # Template tổng hợp tóm tắt (Reduce)
│   │   ├── quiz.jinja2            # Template tạo câu hỏi trắc nghiệm
│   │   └── flashcards.jinja2      # Template tạo thẻ ghi nhớ
│   ├── interfaces/                # Các lớp giao tiếp người dùng
│   │   ├── api.py                 # REST API FastAPI
│   │   ├── cli.py                 # Giao diện dòng lệnh Typer
│   │   ├── ui.py                  # Giao diện web Streamlit
│   │   └── styles.py             # Định dạng giao diện CSS
│   ├── evaluation/                # Đánh giá & tối ưu Reranking
│   │   ├── chunking_strategies.py # Chiến lược phân đoạn Recursive & Semantic
│   │   ├── ragas_evaluator.py     # Đo lường 4 chỉ số Ragas
│   │   └── run_reranking.py       # Tích hợp Cross-Encoder Reranker
│   ├── config.py                  # Cấu hình tập trung bằng Pydantic BaseSettings
│   ├── schemas.py                 # Pydantic schemas (RagAnswer, Summary, Quiz, ...)
│   ├── indexing.py                # Pipeline đọc PDF, băm mã định danh & chia chunk
│   ├── store.py                   # Quản lý Embedding và Qdrant local VectorStore
│   ├── filters.py                 # Chuẩn hóa bộ lọc metadata
│   ├── rag.py                     # Lõi truy xuất Semantic Search & trả lời
│   ├── llm.py                     # Điều phối LLM (Gemini, HuggingFace, vLLM)
│   ├── learning.py                # Xử lý tóm tắt Map-Reduce, Quiz, Flashcards
│   └── export.py                  # Xuất kết quả ra file Markdown / JSON
├── requirements.txt               # Danh sách thư viện cần thiết
├── .env.example                   # File mẫu cấu hình biến môi trường
├── .env                           # File cấu hình hoạt động
└── README.md                      # Tài liệu hướng dẫn sử dụng
```
