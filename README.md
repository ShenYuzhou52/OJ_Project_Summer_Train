# OJ 在线评测系统

## Python 版本
- Python 3.11+

## 安装依赖命令
```bash
pip install -r requirements.txt
```

## 后端启动命令

```bash
uvicorn app.main:app --reload
```

**注意：** 如果修改代码后出现异常行为，请先清理 Python 缓存：
```bash
# Windows PowerShell
Get-ChildItem -Recurse -Filter __pycache__ | Remove-Item -Recurse -Force
```

## 测试命令
```bash
pytest
```

## 初始管理员账号
- 用户名：`admin`
- 密码：`admin123456`
- 首次启动时自动创建，配置项位于 `app/config.py` 中的 `ADMIN_USERNAME` 和 `ADMIN_PASSWORD`

## 使用的持久化方式
- SQLite（方式 B），使用 aiosqlite 异步访问

## 数据文件位置
- 数据库文件：`data/oj.db`

## 备份文件位置
- 备份目录：`data/backups/`

## 前端安装与启动命令
- 前端为原生 HTML/CSS/JavaScript，无需额外安装
- 前端文件位于 `frontend/` 目录，由 FastAPI 静态文件服务自动提供
- 启动后端后，访问 http://localhost:8000 即可使用前端

## 项目结构
```
oj_project/
├── app/
│   ├── main.py              # FastAPI 应用入口
│   ├── config.py            # 配置项
│   ├── models/              # Pydantic 模型定义
│   ├── repositories/        # 数据访问层
│   ├── services/            # 业务逻辑层
│   ├── routers/             # API 路由
│   ├── judge/               # 评测引擎
│   └── utils/               # 工具函数
├── frontend/                # 前端静态文件
│   ├── index.html
│   ├── css/style.css
│   └── js/
├── data/                    # 运行时数据（.gitignore）
│   ├── oj.db               # SQLite 数据库
│   └── backups/            # 数据库备份
├── temp/                    # 评测临时文件（.gitignore）
├── report/                  # 实验报告
├── tests/                   # 测试
└── requirements.txt
```

## 限制
- 仅支持 Python 语言评测
- 评测未使用完整沙箱隔离
- 前端为简单单页应用，未使用前端框架