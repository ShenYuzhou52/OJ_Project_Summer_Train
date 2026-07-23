import aiosqlite
import app.config as _cfg

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'student',
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS problems (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    input_description TEXT NOT NULL,
    output_description TEXT NOT NULL,
    samples TEXT NOT NULL,
    constraints TEXT DEFAULT '',
    time_limit REAL NOT NULL,
    memory_limit INTEGER NOT NULL,
    difficulty TEXT NOT NULL,
    tags TEXT NOT NULL DEFAULT '[]',
    test_cases TEXT NOT NULL,
    judge_mode TEXT NOT NULL DEFAULT 'standard',
    spj_code TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS submissions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    problem_id TEXT NOT NULL,
    language TEXT NOT NULL DEFAULT 'python',
    source_code TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    result TEXT,
    score INTEGER NOT NULL DEFAULT 0,
    total_time REAL,
    created_at TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT
);

CREATE TABLE IF NOT EXISTS judge_logs (
    id TEXT PRIMARY KEY,
    submission_id TEXT NOT NULL,
    case_id TEXT NOT NULL,
    result TEXT NOT NULL,
    score INTEGER NOT NULL DEFAULT 0,
    time_used REAL NOT NULL,
    memory_used REAL,
    exit_code INTEGER NOT NULL DEFAULT 0,
    input_data TEXT,
    stdout TEXT,
    stderr TEXT,
    expected_output TEXT,
    message TEXT,
    is_hidden INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id TEXT PRIMARY KEY,
    operator_id TEXT NOT NULL,
    action TEXT NOT NULL,
    target_type TEXT,
    target_id TEXT,
    success INTEGER NOT NULL DEFAULT 1,
    detail TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS test_cases (
    id TEXT PRIMARY KEY,
    problem_id TEXT NOT NULL,
    case_id TEXT NOT NULL,
    input TEXT NOT NULL,
    expected_output TEXT NOT NULL,
    score INTEGER NOT NULL DEFAULT 0,
    is_hidden INTEGER NOT NULL DEFAULT 0,
    UNIQUE(problem_id, case_id)
);

CREATE TABLE IF NOT EXISTS backups (
    backup_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS similarity_reports (
    id TEXT PRIMARY KEY,
    problem_id TEXT NOT NULL,
    submission_a TEXT NOT NULL,
    submission_b TEXT NOT NULL,
    similarity REAL NOT NULL,
    method TEXT NOT NULL DEFAULT 'ast',
    created_at TEXT NOT NULL
);
"""

MIGRATION_SQL = [
    "ALTER TABLE problems ADD COLUMN judge_mode TEXT NOT NULL DEFAULT 'standard'",
    "ALTER TABLE problems ADD COLUMN spj_code TEXT",
    """CREATE TABLE IF NOT EXISTS similarity_reports (
        id TEXT PRIMARY KEY,
        problem_id TEXT NOT NULL,
        submission_a TEXT NOT NULL,
        submission_b TEXT NOT NULL,
        similarity REAL NOT NULL,
        method TEXT NOT NULL DEFAULT 'ast',
        created_at TEXT NOT NULL
    )""",
]

async def get_db() -> aiosqlite.Connection:
    db = await aiosqlite.connect(_cfg.DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db

async def _migrate_test_cases(db: aiosqlite.Connection):
    """将 problems.test_cases JSON 字段中的数据迁移到独立 test_cases 表"""
    import json
    import uuid
    # 检查 test_cases 表是否已有数据，有则跳过
    cursor = await db.execute("SELECT COUNT(*) FROM test_cases")
    count = (await cursor.fetchone())[0]
    if count > 0:
        return
    # 读取所有 problems 的 test_cases JSON
    cursor = await db.execute("SELECT id, test_cases FROM problems WHERE test_cases IS NOT NULL AND test_cases != '[]'")
    rows = await cursor.fetchall()
    for row in rows:
        problem_id = row[0]
        try:
            cases = json.loads(row[1])
        except (json.JSONDecodeError, TypeError):
            continue
        for tc in cases:
            tc_id = str(uuid.uuid4())
            case_id = tc.get("case_id", tc_id)
            input_data = tc.get("input", "")
            expected_output = tc.get("output", "")
            score = tc.get("score", 0)
            is_hidden = 1 if tc.get("is_hidden") else 0
            try:
                await db.execute(
                    "INSERT OR IGNORE INTO test_cases (id, problem_id, case_id, input, expected_output, score, is_hidden) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (tc_id, problem_id, case_id, input_data, expected_output, score, is_hidden)
                )
            except Exception:
                pass
    await db.commit()


async def init_db():
    db = await get_db()
    try:
        await db.executescript(CREATE_TABLES_SQL)
        await db.commit()
        # Run migrations for existing databases
        for sql in MIGRATION_SQL:
            try:
                await db.execute(sql)
                await db.commit()
            except Exception:
                pass  # Column/table already exists
        # Migrate test_cases from JSON field to independent table
        await _migrate_test_cases(db)
    finally:
        await db.close()
