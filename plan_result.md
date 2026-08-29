# Plan Result — Kế hoạch implement code

File này ghi lại các kế hoạch implementation đã được duyệt và thực hiện cho project, theo thứ tự thời gian. Khác với `plan_prepare.md` (ghi trạng thái/vấn đề/note nhanh), file này ghi **kế hoạch kỹ thuật** — kiến trúc, file nào thay đổi, vì sao — để tra cứu lại khi cần hiểu quyết định thiết kế.

---

## Kế hoạch 1 — MVP: TikTok → English Script Writer

**Ngày:** 2026-08-29
**Trạng thái:** Đã implement xong, đã test end-to-end thành công với video thật.

### Context
Cần một web app local giúp biến 1 video TikTok (dán link hoặc upload) thành kịch bản tiếng Anh chân thực để quay lại video affiliate. Yêu cầu: chạy local, chi phí gần 0, giao diện đơn giản cho non-tech user. Máy có RTX 5060 Ti 16GB VRAM, Ollama đã cài sẵn model `qwen2.5:7b`.

### Kiến trúc
- Backend: Python 3.13 + FastAPI, venv riêng (`.venv/`)
- Job xử lý bất đồng bộ qua in-memory `JobStore` (`app/jobs.py`) + `ThreadPoolExecutor(max_workers=1)` — cố ý serialize vì Whisper và Ollama dùng chung 1 GPU, 1 user local không cần chạy song song.
- State machine: `pending → downloading|ingesting → transcribing → writing → done|error`

### Pipeline (`app/pipeline/`)
1. **`downloader.py`** — tải video TikTok qua `yt_dlp.YoutubeDL` (Python API). `format: "best"` (không ép `mp4` vì có video TikTok dạng slideshow chỉ có audio track).
2. **`ingest.py`** — validate + lưu file upload, probe duration qua PyAV (`av.open`).
3. **`transcriber.py`** — `faster-whisper`, model cache theo `(size, device, compute_type)`, tự fallback CPU nếu CUDA lỗi.
4. **`scriptwriter.py`** — prompt engineering + gọi Ollama REST API (`app/ollama_client.py`, dùng `requests` thuần, không cần package `ollama`).
5. **`pipeline.py`** — điều phối toàn bộ luồng, cập nhật `JobStore`, dọn file tạm ở `finally`.

### Prompt design (phần quan trọng nhất — quyết định độ "chân thực")
System prompt yêu cầu model:
- Giữ cấu trúc/nhịp điệu từ transcript có timestamp (đoạn ngắn = nói nhanh, đoạn dài = giải thích)
- Biến tấu lại chứ không dịch máy móc, nhưng giữ nguyên số liệu/tên sản phẩm
- Dùng văn nói tự nhiên (contractions, câu hỏi tu từ, xưng hô trực tiếp)
- Cấm rõ các cliché kiểu AI ("In today's video", "Let's dive in"...)
- Output format cố định: `HOOK [start-end s]` / `BODY N [start-end s]` / `CTA [start-end s]`

Generation params: `temperature=0.85, repeat_penalty=1.15`, `num_predict` scale theo độ dài video. Validate output bằng regex (`HOOK...CTA`), retry 1 lần ở temperature thấp hơn nếu fail.

### Routes (`app/routes/`)
- `POST /api/jobs` (form: `url` hoặc `file`, exactly one) → tạo job, submit background
- `GET /api/jobs/{id}` → polling status
- `GET /api/jobs/{id}/script` → tải file .txt
- `GET /api/health` → check Ollama + model
- `GET /`, `GET /jobs/{id}` → trang Jinja2 (tiếng Việt, đơn giản)

### Vấn đề phát sinh ngoài kế hoạch gốc (xử lý ngay trong lúc implement)
1. **CUDA không load** trên RTX 5060 Ti (Blackwell) — thiếu `cublas64_12.dll`. Fix: thêm `nvidia-cublas-cu12` + `nvidia-cudnn-cu12` vào `requirements.txt`, tự động set PATH trong `app/config.py::ensure_cuda_dlls_on_path()`.
2. **TikTok anti-bot** chặn yt-dlp — cần `curl_cffi` để impersonate browser, và cần retry (TikTok's JS challenge solver chập chờn ~1/4 lần fail ngẫu nhiên). Fix: thêm `curl_cffi` vào requirements, thêm `downloader.py::_extract_with_retry()` (tối đa 4 lần, delay 2s).
3. Update yt-dlp lên bản nightly trong venv vì bản stable lỗi extraction với TikTok tại thời điểm test.

### File đã tạo (danh sách đầy đủ)
```
requirements.txt, .env.example, run.py, README.md
app/__init__.py, config.py, models.py, errors.py, jobs.py, ollama_client.py, main.py
app/pipeline/{__init__,downloader,ingest,transcriber,scriptwriter,pipeline}.py
app/routes/{__init__,pages,api}.py
app/templates/{base,index,result}.html
app/static/css/style.css, app/static/js/poll.js
tests/smoke_test.py
storage/{uploads,downloads}/.gitkeep
```

### Verification đã thực hiện
- GPU spike test (`WhisperModel` CUDA) — pass sau khi fix DLL path.
- Test qua 2 link TikTok thật của user: 1 video slideshow không giọng nói (đúng báo lỗi "không phát hiện giọng nói"), 1 video có giọng nói (chạy trọn end-to-end, script sinh ra đạt yêu cầu chân thực).
- Test error handling: URL không hợp lệ (YouTube link) → báo lỗi đúng, không crash.

---

## Kế hoạch 2 — Thêm option chọn ngôn ngữ kịch bản (Tiếng Anh / Tiếng Việt)

**Ngày:** 2026-08-29
**Trạng thái:** Đã implement xong, đã test cả 2 ngôn ngữ.

### Context
User muốn có thể chọn xuất kịch bản bằng tiếng Việt thay vì chỉ tiếng Anh (ví dụ: giữ nguyên ngôn ngữ gốc thay vì luôn dịch/biến tấu sang tiếng Anh).

### Thay đổi
- `app/models.py`: thêm `Job.target_language: Literal["en", "vi"] = "en"`
- `app/pipeline/scriptwriter.py`: tách `SYSTEM_PROMPT` thành `SYSTEM_PROMPT_EN` + `SYSTEM_PROMPT_VI` (2 bộ quy tắc riêng — bản VI cấm sáo ngữ AI kiểu Việt như "Trong video hôm nay", khuyến khích từ nối tự nhiên "thiệt tình", "nói thiệt nha"...). `build_messages()` và `generate_script()` nhận thêm param `target_language`.
- `app/jobs.py`: `JobStore.create()` nhận thêm `target_language`.
- `app/routes/api.py`: `POST /api/jobs` nhận thêm form field `language` (validate `en`/`vi`).
- `app/pipeline/pipeline.py`: truyền `job.target_language` vào `generate_script()`, đổi stage message theo ngôn ngữ.
- `app/templates/index.html` + `app/static/css/style.css`: thêm radio button chọn ngôn ngữ (🇬🇧/🇻🇳), style `.lang-toggle`/`.lang-option`.

### Kết quả test — phát hiện quan trọng
Test với video tiếng Việt thật (skit nhiều nhân vật, giọng Nam Bộ): output tiếng Việt kém tự nhiên hơn hẳn tiếng Anh cho cùng 1 transcript nhiễu. Nguyên nhân xác định: **không phải bug** — model `qwen2.5:7b` có năng lực tiếng Anh mạnh hơn tiếng Việt rõ rệt ở size 7B (model "làm mượt" transcript nhiễu tốt bằng tiếng Anh nhưng bám sát từ ngữ nhiễu hơn khi viết tiếng Việt). Khuyến nghị đã ghi trong README/plan_prepare.md: pull `qwen2.5:14b` nếu cần chất lượng tiếng Việt tốt hơn.

---

## Kế hoạch 3 — Publish qua ngrok tunnel

**Ngày:** 2026-08-29
**Trạng thái:** Đã chạy, đã verify hoạt động.

### Context
User có sẵn domain tĩnh free ngrok (`dander-donor-slinky.ngrok-free.dev`) và authtoken đã config sẵn trên máy, muốn expose app local ra ngoài để truy cập qua domain này.

### Thực hiện
- Verify local server (port 8000) đang chạy, ngrok đã cài (`winget`) và có config hợp lệ.
- Chạy `ngrok http 8000 --domain=dander-donor-slinky.ngrok-free.dev` (nền, log ra `ngrok.log`, pid lưu `ngrok.pid`) — flag `--domain` bị deprecated ở ngrok 3.39.10 (khuyến nghị `--url`) nhưng vẫn hoạt động, chỉ in warning.
- Verify qua `curl` tới `https://dander-donor-slinky.ngrok-free.dev/` và `/api/health` — cả 2 trả về đúng.

### Rủi ro đã note cho user
App chưa có xác thực — bất kỳ ai có link đều dùng được, tốn GPU/tài nguyên máy local. Cần chủ động tắt tunnel khi không dùng.

### Việc chưa làm (nếu cần dùng ngrok lâu dài)
- Chưa thêm xác thực (basic auth / token) cho app trước khi public — nên cân nhắc nếu để tunnel mở lâu dài thay vì chỉ demo tạm thời.
- Chưa cấu hình ngrok tự khởi động cùng app (hiện tại là 2 process riêng, chạy tay).
