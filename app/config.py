import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
TEMP_DIR = os.path.join(BASE_DIR, 'temp')
BACKUP_DIR = os.path.join(DATA_DIR, 'backups')
DB_PATH = os.path.join(DATA_DIR, 'oj.db')

SECRET_KEY = os.getenv("OJ_SECRET_KEY", "oj-secret-key-change-in-production")
SESSION_COOKIE_NAME = "session_id"

ADMIN_USERNAME = os.getenv("OJ_ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("OJ_ADMIN_PASSWORD", "admin123456")

MAX_SOURCE_CODE_SIZE = 64 * 1024  # 限制用户最大提交64KB
MAX_LOG_LENGTH = 4000  # 判题输出日志最大4000字符

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)