import asyncio
import os
import sys
import shutil
import subprocess
import tempfile
import time
from app.judge.comparator import compare_output
from app.utils.sanitize import truncate_text, sanitize_error_message
from app.config import TEMP_DIR


def _set_memory_limit_posix(memory_limit_mb: float):
    """Linux/macOS: 用 resource 模块限制内存"""
    import resource
    limit_bytes = int(memory_limit_mb * 1024 * 1024)
    resource.setrlimit(resource.RLIMIT_AS, (limit_bytes, limit_bytes))


async def run_single_case(source_code: str, input_data: str, time_limit: float,
                          memory_limit_mb: float = 256) -> dict:
    """运行单个测试用例，使用同步 subprocess 避免 Windows 事件循环兼容问题。"""
    temp_dir = tempfile.mkdtemp(dir=TEMP_DIR)
    try:
        # 对源代码进行保存
        code_path = os.path.join(temp_dir, "main.py")
        with open(code_path, "w", encoding="utf-8") as f:
            f.write(source_code)
        python_executable = sys.executable or "python"

        try:
            # 使用同步 subprocess.run 在线程池中执行，避免 Windows 事件循环问题
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None,
                _run_subprocess_sync,
                python_executable, code_path, input_data, time_limit, memory_limit_mb, temp_dir
            )
            return result
        except Exception as e:
            import traceback
            err_detail = traceback.format_exc()
            with open(os.path.join(TEMP_DIR, "judge_error.log"), "a", encoding="utf-8") as ef:
                ef.write(f"run_single_case error: {e}\n{err_detail}\n")
            return {
                "result": "SE",
                "exit_code": -1,
                "stdout": "",
                "stderr": sanitize_error_message(str(e)),
                "time_used": 0.0,
            }
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def _run_subprocess_sync(python_executable: str, code_path: str, input_data: str,
                         time_limit: float, memory_limit_mb: float, cwd: str) -> dict:
    """同步运行子进程，在线程池中调用。"""
    try:
        kwargs = dict(
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            timeout=time_limit + 0.5,  # 给一点额外时间用于进程启动
        )

        if sys.platform != "win32":
            import functools
            kwargs["preexec_fn"] = functools.partial(_set_memory_limit_posix, memory_limit_mb)
        else:
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

        start_time = time.perf_counter()
        try:
            proc = subprocess.run(
                [python_executable, code_path],
                input=input_data.encode("utf-8"),
                **kwargs,
            )
            time_used = round(time.perf_counter() - start_time, 3)
        except subprocess.TimeoutExpired:
            time_used = round(time.perf_counter() - start_time, 3)
            return {
                "result": "TLE",
                "exit_code": -1,
                "stdout": "",
                "stderr": "Time Limit Exceeded",
                "time_used": time_limit,
            }

        exit_code = proc.returncode

        # 检查是否超过时间限制（进程本身可能没超 subprocess.timeout 但超过了 OJ 的时间限制）
        if time_used > time_limit:
            return {
                "result": "TLE",
                "exit_code": exit_code,
                "stdout": "",
                "stderr": "Time Limit Exceeded",
                "time_used": time_limit,
            }

        try:
            stdout = proc.stdout.decode("utf-8")
        except UnicodeDecodeError:
            return {
                "result": "RE",
                "exit_code": exit_code,
                "stdout": "",
                "stderr": "output cannot be decoded as UTF-8",
                "time_used": time_used,
            }

        try:
            stderr = proc.stderr.decode("utf-8", errors="replace")
        except Exception:
            stderr = ""

        # 检查是否因为内存超限被 kill（Linux 下 exit_code = -9）
        if exit_code == -9 or (sys.platform != "win32" and exit_code < 0):
            if "MemoryError" in stderr or exit_code == -9:
                return {
                    "result": "MLE",
                    "exit_code": exit_code,
                    "stdout": "",
                    "stderr": "Memory Limit Exceeded",
                    "time_used": time_used,
                }

        return {
            "result": "",
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
            "time_used": time_used,
        }
    except subprocess.TimeoutExpired:
        return {
            "result": "TLE",
            "exit_code": -1,
            "stdout": "",
            "stderr": "Time Limit Exceeded",
            "time_used": time_limit,
        }
    except Exception as e:
        import traceback
        with open(os.path.join(os.path.dirname(cwd), "judge_debug.log"), "a", encoding="utf-8") as dbg:
            dbg.write(f"EXCEPTION in _run_subprocess_sync: {type(e).__name__}: {e}\n{traceback.format_exc()}\n")
        return {
            "result": "SE",
            "exit_code": -1,
            "stdout": "",
            "stderr": sanitize_error_message(str(e)),
            "time_used": 0.0,
        }
