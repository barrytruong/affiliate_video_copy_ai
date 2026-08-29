# Command Notes — chạy / tắt app

Thư mục project: `E:\code_workspace\affiliate_video_copy_ai`

## Yêu cầu trước khi chạy
- Ollama app phải đang chạy sẵn (icon system tray), có pull model `qwen2.5:7b` (hoặc model khác đã set trong `.env`).

## Start server (chạy app local)

PowerShell:
```powershell
cd E:\code_workspace\affiliate_video_copy_ai
.venv\Scripts\python.exe run.py
```

Mặc định chạy tại `http://127.0.0.1:8000`. Lệnh này chạy ở foreground (chiếm terminal) — bấm `Ctrl+C` để dừng.

### Chạy ngầm (background), không chiếm terminal
```powershell
cd E:\code_workspace\affiliate_video_copy_ai
Start-Process -FilePath ".venv\Scripts\python.exe" -ArgumentList "run.py" -WindowStyle Hidden -PassThru | Select-Object -ExpandProperty Id | Out-File server.pid
```
PID được lưu vào `server.pid` để tắt sau này (xem phần Stop).

## Start ngrok tunnel (public URL)

Domain tĩnh free đã config sẵn: `dander-donor-slinky.ngrok-free.dev`

```powershell
cd E:\code_workspace\affiliate_video_copy_ai
ngrok http 8000 --url=dander-donor-slinky.ngrok-free.dev
```
(Flag cũ `--domain` vẫn chạy được nhưng bị deprecated ở ngrok 3.39.10, nên dùng `--url`.)

Chạy ngầm tương tự:
```powershell
Start-Process -FilePath "ngrok" -ArgumentList "http 8000 --url=dander-donor-slinky.ngrok-free.dev" -WindowStyle Hidden -PassThru | Select-Object -ExpandProperty Id | Out-File ngrok.pid
```

## Stop (tắt app)

**Cách 1 — tắt đúng process đã lưu PID (an toàn hơn):**
```powershell
Stop-Process -Id (Get-Content server.pid) -Force
Stop-Process -Id (Get-Content ngrok.pid) -Force
```

**Cách 2 — tắt theo tên process (nhanh nhưng tắt luôn MỌI instance cùng tên):**
```powershell
Stop-Process -Name ngrok -Force
Stop-Process -Name python -Force
```
⚠️ Cách 2 sẽ tắt mọi `python.exe`/`ngrok.exe` đang chạy trên máy, không riêng app này — cẩn thận nếu có script Python khác đang chạy song song.

## Kiểm tra trạng thái đang chạy hay không

```powershell
# App local
Invoke-WebRequest http://127.0.0.1:8000/api/health -UseBasicParsing | Select-Object StatusCode

# Tunnel public
Invoke-WebRequest https://dander-donor-slinky.ngrok-free.dev/api/health -UseBasicParsing | Select-Object StatusCode

# Xem process đang chạy
Get-Process python, ngrok -ErrorAction SilentlyContinue
```

## Ghi chú
- Server chạy với `--reload` (trong `run.py`) nên sửa code trong `app/` sẽ tự áp dụng, không cần restart thủ công.
- Nếu đổi `.env` (model, whisper device...) thì **cần restart server** — biến môi trường chỉ đọc lúc khởi động.