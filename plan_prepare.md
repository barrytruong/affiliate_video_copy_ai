# Plan Prepare — TikTok Script Writer

## Mục tiêu
Web app local: dán link TikTok hoặc tải video lên → sinh **kịch bản (script)** chân thực (không lộ giọng AI), chọn được tiếng Anh hoặc tiếng Việt, để dùng quay video affiliate. Chi phí gần bằng 0 — chạy hoàn toàn local (Whisper + Ollama), không dùng API trả phí.

Đây chính là một **"script writer"** đúng nghĩa: input là video (qua transcript giọng nói), output là văn bản kịch bản có cấu trúc (HOOK/BODY/CTA) — không phải video editor hay video generator.

Kế hoạch gốc: `C:\Users\DucThi\.claude\plans\cached-wiggling-bear.md` (bản đầy đủ, chi tiết implementation từng file nằm ở `plan_result.md` trong repo — vì file trên nằm ngoài repo, không có trong git history).

## Trạng thái hiện tại: đã build xong, đã test end-to-end thành công, **chưa commit** (đang chờ user tự test qua giao diện trước).

## Stack đã chọn
- Backend: Python 3.13 + FastAPI (venv tại `.venv/`)
- Transcribe: `faster-whisper` (GPU CUDA, fallback CPU tự động)
- LLM viết script: Ollama local, model `qwen2.5:7b` (đã pull sẵn, có thể nâng cấp lên `qwen2.5:14b` nếu muốn chất lượng tốt hơn — máy có RTX 5060 Ti 16GB VRAM, dư sức)
- Tải video TikTok: `yt-dlp` (Python API) + `curl_cffi` (giả lập browser để qua anti-bot)
- Frontend: Jinja2 + vanilla JS, tiếng Việt, đơn giản cho non-tech user

## Các vấn đề đã gặp và cách fix trong lúc build/test

1. **CUDA không load được cho faster-whisper trên RTX 5060 Ti (Blackwell)**
   - Lỗi: `Library cublas64_12.dll is not found or cannot be loaded`
   - Fix: thêm `nvidia-cublas-cu12`, `nvidia-cudnn-cu12` vào `requirements.txt`; `app/config.py::ensure_cuda_dlls_on_path()` tự động thêm bin dir của 2 package này vào PATH lúc app khởi động (chạy trước khi import faster_whisper trong `transcriber.py`). Không cần user cài ffmpeg/CUDA toolkit thủ công.
   - Nếu vẫn lỗi: `transcriber.py::get_model()` tự fallback sang `device=cpu, compute_type=int8` và cache quyết định đó cho cả process (không lặp lại thử-fail mỗi request).

2. **TikTok anti-bot challenge khiến tải video chập chờn (lúc được lúc không)**
   - Lỗi ban đầu: `Unexpected response from webpage request` (thiếu impersonation) → fix bằng cài `curl_cffi`.
   - Lỗi tiếp theo: `Unable to extract universal data for rehydration` — xảy ra ngẫu nhiên ~1/4 lần dù cùng 1 link, do TikTok's JS challenge solver của yt-dlp không phải lúc nào cũng qua được.
   - Fix: `downloader.py::_extract_with_retry()` tự retry tối đa 4 lần (delay 2s) khi gặp lỗi thuộc nhóm "challenge flaky" (`_CHALLENGE_RETRY_MARKERS`).
   - Cũng đã update yt-dlp lên bản **nightly** trong venv hiện tại (`2026.08.27.231323.dev0`, mới hơn bản stable `2026.8.19` từng cài) vì bản nightly vá lỗi TikTok nhanh hơn. Ghi chú trong README: nếu tải fail hàng loạt về sau, chạy `pip install -U --pre yt-dlp`.
   - **Lưu ý cho tương lai:** đây là cuộc đua liên tục giữa yt-dlp và TikTok — không có fix "vĩnh viễn", chỉ có retry + update thường xuyên.

3. **Một số TikTok chỉ có audio, không có video track thật**
   - Video dạng "ảnh trượt + nhạc nền" (slideshow post) — yt-dlp chỉ list được format `audio` (mp3), không có mp4.
   - Đã đổi format spec từ `"mp4/best"` sang `"best"` trong `downloader.py` vì pipeline chỉ cần audio để transcribe, không cần video thật — không mất tính năng gì.
   - Nếu video dạng này không có giọng nói (chỉ nhạc) → app báo đúng lỗi "Không phát hiện được giọng nói trong video này" (không crash).

## Đã test thật với 2 link TikTok của user
- Link 1 (`ZSVtCATj8`): video slideshow ảnh + nhạc, không có giọng nói → app báo lỗi đúng như thiết kế (không phải bug).
- Link 2 (`ZSVtqWgBw`): video có giọng nói → chạy trọn pipeline download → transcribe → writing → done. Script sinh ra có format HOOK/BODY/CTA, dùng contractions, giọng văn tự nhiên, không sáo rỗng kiểu AI.

## Việc user sẽ tự làm tiếp
- Tự chạy server (`.venv\Scripts\python run.py` hoặc `.venv/Scripts/python.exe run.py`) và test qua giao diện trình duyệt `http://127.0.0.1:8000`.
- Sau khi hài lòng → mới commit (user chủ động yêu cầu, chưa commit gì trong session này).

## Đã publish qua ngrok (tunnel công khai tạm thời)
- User có sẵn domain tĩnh free: `dander-donor-slinky.ngrok-free.dev`.
- Lệnh chạy: `ngrok http 8000 --url=dander-donor-slinky.ngrok-free.dev` (flag `--domain` đã deprecated ở ngrok v3.39, dùng `--url` thay thế — dùng `--domain` vẫn chạy được, chỉ in warning).
- Authtoken ngrok đã config sẵn từ trước tại `C:\Users\DucThi\AppData\Local\ngrok\ngrok.yml`, không cần setup lại.
- Đã verify: `https://dander-donor-slinky.ngrok-free.dev/` và `/api/health` trả về đúng qua tunnel.
- **Lưu ý bảo mật:** app chưa có xác thực/đăng nhập — ai có link cũng dùng được, tốn GPU/tài nguyên máy local. Cần tắt tunnel khi không dùng (`kill $(cat ngrok.pid)` trong session đã mở, hoặc tắt process `ngrok.exe` qua Task Manager).

## Đã thêm: chọn ngôn ngữ kịch bản (Tiếng Anh / Tiếng Việt)
- UI: radio button ở trang chủ (`index.html`), mặc định English.
- `scriptwriter.py`: có 2 system prompt riêng (`SYSTEM_PROMPT_EN`, `SYSTEM_PROMPT_VI`) — bản tiếng Việt cấm các sáo ngữ AI kiểu Việt ("Trong video hôm nay", "Đừng quên like share...") và khuyến khích từ nối tự nhiên miền Nam/Bắc thường dùng.
- `Job.target_language`, `POST /api/jobs` nhận thêm field `language` ("en"/"vi").

### Phát hiện quan trọng khi test tiếng Việt (link `ZSVtqWgBw`, video skit "đám giỗ" nhiều nhân vật, giọng Nam Bộ)
- Whisper transcribe tiếng Việt cho video này khá nhiễu (giọng vùng miền, nhiều người nói chồng tiếng, VD "đám dỗ" thay vì "đám giỗ", "béo phùy" không rõ nghĩa).
- Output tiếng Anh từ transcript nhiễu này vẫn đọc mượt (model 7B "làm mượt" tốt bằng tiếng Anh dù input lộn xộn) — nhưng output tiếng Việt bám sát từ ngữ nhiễu của transcript hơn, nghe lủng củng, kém tự nhiên hơn hẳn bản tiếng Anh.
- **Kết luận: đây không phải bug, mà là giới hạn năng lực tiếng Việt của model `qwen2.5:7b`** (tiếng Anh mạnh hơn tiếng Việt rõ rệt ở size 7B, phổ biến với hầu hết model đa ngôn ngữ nhỏ).
- **Khuyến nghị nếu cần script tiếng Việt chất lượng tốt hơn:** pull model lớn hơn (`ollama pull qwen2.5:14b`) hoặc thử với video nguồn có 1 người nói rõ ràng thay vì skit nhiều nhân vật/giọng vùng miền nặng — chưa có thời gian test lại để xác nhận cải thiện bao nhiêu.

## Việc còn có thể làm sau (chưa làm, không nằm trong MVP)
- Thêm lựa chọn model Ollama ngay trên UI (hiện tại chỉ đổi qua `.env`).
- Refine pass thứ 2 cho script (loại bỏ cliché sót lại) — đã kiến trúc sẵn chỗ để thêm (`ENABLE_REFINE_PASS`) nhưng chưa implement vì tăng gấp đôi latency trên model 7B local.
- Dọn dẹp tự động file cũ trong `storage/uploads`/`storage/downloads` nếu job bị crash giữa chừng (hiện tại có cleanup ở `finally` trong `pipeline.py` cho luồng chạy bình thường).
