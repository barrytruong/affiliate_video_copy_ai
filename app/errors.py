class PipelineError(Exception):
    """Base class for pipeline errors with a Vietnamese, user-facing message."""

    user_message_vi = "Đã có lỗi xảy ra, vui lòng thử lại."

    def __init__(self, detail: str = ""):
        self.detail = detail
        super().__init__(detail or self.user_message_vi)


class InvalidURLError(PipelineError):
    user_message_vi = "Đường link không hợp lệ hoặc không được hỗ trợ."


class PrivateVideoError(PipelineError):
    user_message_vi = "Video này ở chế độ riêng tư hoặc đã bị gỡ."


class VideoUnavailableError(PipelineError):
    user_message_vi = "Không thể truy cập video này. Vui lòng kiểm tra lại link."


class DownloadFailedError(PipelineError):
    user_message_vi = "Tải video thất bại. Vui lòng thử lại hoặc dùng link khác."


class VideoTooLongError(PipelineError):
    def __init__(self, duration_seconds: float, max_seconds: int):
        self.user_message_vi = (
            f"Video quá dài ({duration_seconds:.0f} giây). "
            f"Tối đa cho phép là {max_seconds} giây."
        )
        super().__init__(self.user_message_vi)


class UnsupportedFormatError(PipelineError):
    user_message_vi = "Định dạng file không được hỗ trợ."


class UploadTooLargeError(PipelineError):
    user_message_vi = "File quá lớn."


class NoSpeechDetectedError(PipelineError):
    user_message_vi = "Không phát hiện được giọng nói trong video này."


class OllamaNotRunningError(PipelineError):
    user_message_vi = (
        "Không thể kết nối tới Ollama. Vui lòng mở ứng dụng Ollama và thử lại."
    )


class OllamaModelMissingError(PipelineError):
    def __init__(self, model_name: str):
        self.user_message_vi = (
            f"Chưa cài model '{model_name}'. Chạy lệnh: ollama pull {model_name}"
        )
        super().__init__(self.user_message_vi)


class ScriptGenerationError(PipelineError):
    user_message_vi = "Không tạo được kịch bản, vui lòng thử lại."
