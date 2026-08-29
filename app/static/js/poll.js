async function fetchHealth() {
  const banner = document.getElementById("health-banner");
  if (!banner) return;
  try {
    const resp = await fetch("/api/health");
    const data = await resp.json();
    if (data.ollama_ok && data.model_ok) {
      banner.textContent = `Sẵn sàng — dùng model "${data.ollama_model}" (${data.whisper_device === "cuda" ? "GPU" : "CPU"})`;
      banner.className = "banner banner-ok";
    } else {
      banner.textContent = data.detail || "Ollama chưa sẵn sàng.";
      banner.className = "banner banner-error";
    }
  } catch (err) {
    banner.textContent = "Không thể kiểm tra trạng thái hệ thống.";
    banner.className = "banner banner-error";
  }
}
