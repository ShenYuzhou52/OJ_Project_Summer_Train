import re
from app.config import MAX_LOG_LENGTH

def truncate_text(text: str, max_length: int = MAX_LOG_LENGTH):  # 截断长文本
    if text is None:
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "...[truncated]"

def sanitize_error_message(message: str) -> str:  # 脱敏绝对路径
    if message is None:
        return ""
    # Linux/Unix路径脱敏
    message = re.sub(r'/home/[^\s]+/temp/[^\s/]+/', '<submission>/', message)
    message = re.sub(r'/tmp/[^\s/]+/', '<submission>/', message)
    message = re.sub(r'/var/[^\s]+/', '<system>/', message)
    # Windows路径脱敏 - 匹配类似 C:\path\to\temp\xxx\
    message = re.sub(r'[A-Za-z]:[^\s]+\\temp\\[^\s\\]+\\', r'<submission>/', message)
    return message

def to_student_log_view(log: dict) -> dict:
    view = {
        "case_id": log["case_id"],
        "result": log["result"],
        "score": log["score"],
        "time_used": log["time_used"],
    }
    if log.get("message"):
        view["message"] = sanitize_error_message(truncate_text(log["message"]))
    
    is_hidden = bool(log.get("is_hidden", 0))

    if not is_hidden:
        view["stdout"] = truncate_text(log.get("stdout", ""))
        view["expected_output"] = truncate_text(log.get("expected_output", ""))
    
    if log.get("stderr"):
        view["stderr"] = sanitize_error_message(truncate_text(log["stderr"]))
    
    return view

def to_teacher_log_view(log: dict) -> dict:
    view = {
        "submission_id": log.get("submission_id", ""),
        "case_id": log["case_id"],
        "result": log["result"],
        "score": log["score"],
        "time_used": log["time_used"],
        "memory_used": log.get("memory_used"),
        "exit_code": log.get("exit_code", 0),
        "input_data": truncate_text(log.get("input_data", "")),
        "stdout": truncate_text(log.get("stdout", "")),
        "stderr": truncate_text(log.get("stderr", "")),
        "expected_output": truncate_text(log.get("expected_output", "")),
        "message": truncate_text(log.get("message", "")),
        "is_hidden": bool(log.get("is_hidden", 0)),
        "created_at": log.get("created_at", ""),
    }
    return view