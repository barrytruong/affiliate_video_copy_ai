# affiliate_video_copy_ai

Công cụ web chạy local: dán link TikTok hoặc tải video lên, tự động tạo ra **kịch bản tiếng Anh chân thực** (không "lộ" giọng AI) để bạn quay lại video affiliate của riêng mình.

Chạy 100% local, chi phí gần bằng 0: transcribe bằng Whisper local, viết kịch bản bằng Ollama local (không dùng API trả phí).

## Yêu cầu

- Python 3.13 (khuyến nghị) hoặc 3.12
- [Ollama](https://ollama.com) đã cài và đang chạy, với model đã pull sẵn:
  ```
  ollama pull qwen2.5:7b
  ```
- GPU NVIDIA (khuyến nghị, để transcribe nhanh) — nếu không có GPU, app vẫn chạy được bằng CPU (chậm hơn), chỉnh `WHISPER_DEVICE=cpu` trong `.env`.

## Cài đặt

```powershell
py -3.13 -m venv .venv
.venv\Scripts\pip install -r requirements.txt
copy .env.example .env
```

### Lưu ý quan trọng cho GPU trên Windows

`faster-whisper` cần thư viện cuBLAS/cuDNN của NVIDIA nhưng không tự bundle chúng trên Windows. `requirements.txt` đã bao gồm `nvidia-cublas-cu12` và `nvidia-cudnn-cu12` để giải quyết việc này — code trong `app/config.py::ensure_cuda_dlls_on_path()` sẽ tự động trỏ PATH tới các DLL này khi app khởi động, không cần chỉnh gì thêm. Nếu vẫn gặp lỗi CUDA, app sẽ tự động fallback về CPU (chậm hơn nhưng vẫn chạy được).

## Chạy app

```powershell
.venv\Scripts\python run.py
```

Mở trình duyệt tại `http://127.0.0.1:8000`.

## Cách dùng

1. Trang chủ hiện banner trạng thái hệ thống (Ollama sẵn sàng chưa, dùng GPU hay CPU).
2. Chọn tab "Dán link TikTok" hoặc "Tải video lên".
3. Bấm "Tạo kịch bản" — theo dõi tiến trình: Đang tải video → Đang chuyển giọng nói thành văn bản → Đang viết kịch bản.
4. Khi xong, copy hoặc tải file `.txt` kịch bản.

## Khắc phục sự cố

| Vấn đề | Nguyên nhân / cách xử lý |
|---|---|
| "Không thể kết nối tới Ollama" | Mở app Ollama, đảm bảo đang chạy ở `127.0.0.1:11434` |
| "Chưa cài model..." | Chạy `ollama pull qwen2.5:7b` (hoặc đổi `OLLAMA_MODEL` trong `.env`) |
| "Tải video thất bại" dù link đúng | TikTok có cơ chế chống bot gây lỗi **chập chờn** (không phải lỗi cố định) — app đã tự động thử lại vài lần, nhưng nếu vẫn lỗi hãy thử lại sau ít phút. Nếu lỗi liên tục, cập nhật yt-dlp: `.venv\Scripts\pip install -U --pre yt-dlp` (TikTok đổi cơ chế chống bot thường xuyên, bản yt-dlp mới nhất — kể cả bản nightly — thường vá lỗi này nhanh hơn bản stable) |
| "Không phát hiện được giọng nói" | Video không có lời thoại (ví dụ chỉ có nhạc nền/ảnh trượt) — chọn video khác có người nói |
| "Video quá dài" | Mặc định giới hạn 600 giây (`MAX_VIDEO_SECONDS` trong `.env`) |
| Muốn chất lượng transcribe tốt hơn | Đổi `WHISPER_MODEL_SIZE=large-v3` trong `.env` (card 16GB VRAM trở lên chạy thoải mái) |
| Muốn kịch bản "hay" hơn | Pull model lớn hơn, ví dụ `ollama pull qwen2.5:14b`, rồi đổi `OLLAMA_MODEL=qwen2.5:14b` trong `.env` |

## Kiểm tra nhanh (smoke test)

Với server đang chạy:

```powershell
.venv\Scripts\python tests\smoke_test.py path\to\video.mp4
```

## Cấu trúc project

```
app/
  main.py            # FastAPI app
  config.py          # Settings + CUDA DLL PATH fix cho Windows
  jobs.py            # Job store trong bộ nhớ (xử lý tuần tự, 1 job/lần)
  ollama_client.py   # Gọi Ollama REST API
  pipeline/
    downloader.py    # Tải video từ TikTok (yt-dlp)
    ingest.py         # Xử lý file upload
    transcriber.py    # Chuyển giọng nói thành văn bản (faster-whisper)
    scriptwriter.py   # Prompt + gọi LLM viết kịch bản
    pipeline.py        # Điều phối toàn bộ luồng xử lý
  routes/             # API + trang web
  templates/, static/ # Giao diện
storage/              # File tạm (tự động xoá sau khi xử lý xong)
```
