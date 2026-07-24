"""
评测输出比较模块
统一管理所有评测方式：standard（规范化比较）、strict（严格比较）、spj（Special Judge）
"""
import asyncio
import json
import os
import sys
import shutil
import tempfile

from app.utils.sanitize import sanitize_error_message

SPJ_TIMEOUT = 10  # SPJ 超时时间（秒）
SPJ_MAX_OUTPUT = 4000  # SPJ 输出长度限制


def normalize_output(text: str) -> str:
    """规范化输出：统一换行符、去除行末空白、去除末尾空行"""
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip(" \t") for line in text.split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


def compare_output(actual: str, expected: str) -> bool:
    """standard 模式：规范化后比较"""
    return normalize_output(actual) == normalize_output(expected)


def compare_strict(actual: str, expected: str) -> bool:
    """strict 模式：原始字符串完全一致"""
    return actual == expected


async def run_spj(spj_code: str, input_data: str, expected_output: str, actual_output: str) -> dict:
    """
    运行 SPJ 判题器。
    SPJ 是一个 Python 脚本，需定义 judge(input_data, expected_output, actual_output) 函数。
    返回 dict: {"accepted": bool, "score": int, "message": str}
    失败时额外包含 "result": "SE"
    """
    tmp_dir = tempfile.mkdtemp(prefix="spj_")
    input_file = os.path.join(tmp_dir, "input.txt")
    expected_file = os.path.join(tmp_dir, "expected.txt")
    actual_file = os.path.join(tmp_dir, "actual.txt")
    spj_file = os.path.join(tmp_dir, "spj_run.py")

    try:
        # 写入数据文件
        with open(input_file, "w", encoding="utf-8") as f:
            f.write(input_data)
        with open(expected_file, "w", encoding="utf-8") as f:
            f.write(expected_output)
        with open(actual_file, "w", encoding="utf-8") as f:
            f.write(actual_output)

        # 构造 SPJ 运行脚本（从文件读取数据，避免转义问题）
        spj_script = f'''import sys, json, os

# 读取数据
with open({json.dumps(input_file)}, "r", encoding="utf-8") as f:
    input_data = f.read()
with open({json.dumps(expected_file)}, "r", encoding="utf-8") as f:
    expected_output = f.read()
with open({json.dumps(actual_file)}, "r", encoding="utf-8") as f:
    actual_output = f.read()

# SPJ code begins
{spj_code}
# SPJ code ends

# 调用 SPJ 的 judge 函数
try:
    result = judge(input_data, expected_output, actual_output)
    if not isinstance(result, dict):
        print(json.dumps({{"accepted": False, "score": 0, "message": "SPJ must return a dict"}}))
        sys.exit(1)
    print(json.dumps(result, ensure_ascii=False))
except Exception as e:
    print(json.dumps({{"accepted": False, "score": 0, "message": f"SPJ exception: {{str(e)[:200]}}"}}, ensure_ascii=False))
    sys.exit(1)
'''
        with open(spj_file, "w", encoding="utf-8") as f:
            f.write(spj_script)

        # 使用同步 subprocess 在线程池中运行，避免 Windows 事件循环兼容问题
        import subprocess
        loop = asyncio.get_running_loop()
        spj_run_result = await loop.run_in_executor(
            None, _run_spj_subprocess_sync, sys.executable, spj_file, tmp_dir
        )
        return spj_run_result

    except Exception as e:
        return {"accepted": False, "score": 0, "message": f"SPJ system error: {str(e)[:100]}", "result": "SE"}
    finally:
        try:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass


def _run_spj_subprocess_sync(python_executable: str, spj_file: str, cwd: str) -> dict:
    """同步运行 SPJ 子进程，在线程池中调用以避免 Windows 事件循环问题。"""
    import subprocess

    try:
        proc = subprocess.run(
            [python_executable, spj_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            timeout=SPJ_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return {"accepted": False, "score": 0, "message": "SPJ timeout", "result": "SE"}
    except Exception as e:
        return {"accepted": False, "score": 0, "message": f"SPJ system error: {str(e)[:100]}", "result": "SE"}

    stdout_str = proc.stdout.decode("utf-8", errors="replace").strip()
    stderr_str = proc.stderr.decode("utf-8", errors="replace").strip()

    if len(stdout_str) > SPJ_MAX_OUTPUT:
        stdout_str = stdout_str[:SPJ_MAX_OUTPUT]

    if not stdout_str:
        if proc.returncode != 0:
            err_msg = stderr_str[:200] if stderr_str else "SPJ runtime error"
            err_msg = sanitize_error_message(err_msg)
            return {"accepted": False, "score": 0, "message": f"SPJ error: {err_msg}", "result": "SE"}
        return {"accepted": False, "score": 0, "message": "SPJ produced no output", "result": "SE"}

    # 尝试解析 stdout 的最后一行作为 JSON 结果
    # （SPJ 脚本最终 print 的 JSON 总是在最后一行）
    stdout_lines = stdout_str.strip().split("\n")
    json_line = stdout_lines[-1].strip()

    try:
        spj_result = json.loads(json_line)
    except json.JSONDecodeError:
        # 如果最后一行也不是 JSON，才判定为 SE
        if proc.returncode != 0:
            err_msg = stderr_str[:200] if stderr_str else "SPJ runtime error"
            err_msg = sanitize_error_message(err_msg)
            return {"accepted": False, "score": 0, "message": f"SPJ error: {err_msg}", "result": "SE"}
        return {"accepted": False, "score": 0, "message": "SPJ output is not valid JSON", "result": "SE"}

    # 校验 SPJ 返回值类型
    if not isinstance(spj_result, dict):
        return {"accepted": False, "score": 0, "message": "SPJ output is not a JSON object", "result": "SE"}
    if "accepted" not in spj_result:
        return {"accepted": False, "score": 0, "message": "SPJ output missing 'accepted' field", "result": "SE"}
    if not isinstance(spj_result["accepted"], bool):
        return {"accepted": False, "score": 0, "message": "SPJ 'accepted' field must be boolean", "result": "SE"}

    # 脱敏：限制 message 长度并去除路径信息
    if "message" in spj_result:
        msg = str(spj_result["message"])
        msg = sanitize_error_message(msg)
        if len(msg) > 200:
            msg = msg[:200] + "..."
        spj_result["message"] = msg

    return spj_result
