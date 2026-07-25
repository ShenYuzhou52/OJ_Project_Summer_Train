# OJ 在线评测系统 — 第二次大作业实验报告

## 1. 项目概述

### 项目目标
实现一个在线评测（OJ）系统，支持题目管理、代码提交、自动评测、用户权限管理、日志审计和数据持久化等功能。

### 已完成功能
- 编程题目CRUD (教师/管理员) 、题目列表及详情展示、学生权限控制、题目数据持久化
- 学生题目提交、后台异步评测（独立子进程中运行）、多测试点计算得分、结构化返回评测结果。可正确识别不同错误及评测器异常情况，且及时清理了评测器。
- 用户注册、登录、登出（Cookie-Session 认证）、角色管理和学生、教师、管理员的后端权限控制。持久化层保存密码哈希但未通过接口返回。保证用户名和密码的合法性及错误输出的准确性。保证用户信息及修改的持久化。
- 题目提交实现了合法状态流转。学生可查询自己的提交，教师和管理员可查询任何提交，支持分字段筛选。支持重新评测。
- 包含提交级评测摘要、测试点级评测日志、审计日志三类记录。严格遵循各日志数据结构。不在返回给学生的日志中暴露服务器绝对路径、数据库地址、环境变量、完整异常堆栈或其他用户信息，实现了数据脱敏。严格根据用户角色控制权限。支持分字段筛选。
- 使用 SQLite 实现了数据持久化、备份与恢复，建立了用户、题目、测试点、提交、评测日志和审计日志表，服务重启后能够恢复全部主要数据。管理员可以备份与恢复数据库。
- 学生前端界面包括登录、题目浏览、题目详情页及代码提交、“我的提交”中的评测状态、结果和过往提交的查询。教师前端界面还包括题目管理、所有提交的管理界面、测试点日志界面、查重界面。管理员前端界面还包括管理面板界面，支持用户管理、备份管理和审计日志查询。处理了未登录、权限不足等异常状况。
- 进阶模块中，实现了Special Judge和Similarity Check。
- 已开源至个人仓库 https://github.com/ShenYuzhou52/OJ_Project_Summer_Train.git

### 未完成功能
- 进阶模块中的安全隔离部分

### 选择的持久化方式
- SQLite，使用 aiosqlite 异步访问。

### 是否完成进阶模块
- 实现了Adv1: Special Judge 和 Adv3：Similarity Check. 
- 拓展了评测模式。实现教师或管理员上传、替换和删除 SPJ。SPJ 与题目一一绑定。学生不得查看 SPJ 源码。遵循 SPJ 调用约定进行特殊测试编写。
- 通过对 Python 代码进行 AST 分析这一技术降低变量名不同对结果的影响。支持对同一道题的多份 Python 提交进行相似度分析。不自动将学生标记为作弊。

## 2. 系统架构

### 路由层（app/routers/）
负责 HTTP 请求处理、参数校验和响应格式化。包括：
- `auth.py`：认证相关路由（注册、登录、登出、当前用户）
- `problems.py`：题目 CRUD 路由
- `submissions.py`：提交和重测路由
- `logs.py`：评测日志和教师日志检索路由
- `audit_logs.py`：审计日志查询路由
- `admin.py`：用户管理和备份恢复路由
- `similarity.py`：相似度监测及报告生成路由

### 业务层（app/services/）
负责核心业务逻辑。包括：
- `auth_service.py`：用户注册、登录验证、密码哈希
- `submission_service.py`：提交创建、状态管理、异步评测调度
- `backup_service.py`：异步创建、列出、恢复备份
- `similarity_service.py`：代码相似度检测（AST 分析与相似度计算），数据库操作委托给 `similarity_repo`

### 数据访问层（app/repositories/）
负责数据库操作，使用 aiosqlite 访问 SQLite。包括：
- `database.py`：数据库初始化、连接管理和表结构迁移
- `user_repo.py`、`problem_repo.py`、`submission_repo.py`、`test_case_repo.py`
- `judge_log_repo.py`、`audit_log_repo.py`
- `similarity_repo.py`：相似度报告的存储和查询
- 所有 repo 模块直接接触数据库，实现各数据实体的 CRUD

### 评测层（app/judge/）
负责代码执行和结果判定。包括：
- `runner.py`：子进程运行用户代码，超时控制和资源限制
- `judge_service.py`：评测流程编排（多测试点循环、日志写入、结果汇总），调用 `comparator` 进行输出比较
- `comparator.py`：统一管理所有评测比较方式——standard（规范化比较）、strict（严格比较）、spj（Special Judge 子进程调用）

### 日志层
- `app/utils/sanitize.py`：日志脱敏和截断（`to_student_log_view`、`to_teacher_log_view`、`sanitize_error_message`、`truncate_text`）
- `app/judge_log.py`：评测日志记录

### 前端层（frontend/）
原生 HTML/CSS/JavaScript 单页应用，通过 fetch API 调用后端接口。

### 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (HTML/JS)                         │
│   index.html — 学生/教师/管理员 SPA，通过 fetch 调用后端 API      │
└────────────────────────────────┬────────────────────────────────┘
                                 │ HTTP (Cookie-Session)
┌────────────────────────────────▼────────────────────────────────┐
│                     FastAPI Application (app/main.py)             │
├──────────────────────────────────────────────────────────────────┤
│  路由层 (app/routers/)                                            │
│  auth | problems | submissions | logs | audit_logs | admin |      │
│  similarity                                                       │
├──────────────────────────────────────────────────────────────────┤
│  业务层 (app/services/)                                           │
│  auth_service | submission_service | backup_service |              │
│  similarity_service                                               │
├──────────────────────────────────────────────────────────────────┤
│  评测层 (app/judge/)                                              │
│  judge_service → comparator (standard/strict/spj)                 │
│               → runner (子进程执行)                                │
├──────────────────────────────────────────────────────────────────┤
│  数据访问层 (app/repositories/)                                   │
│  user_repo | problem_repo | submission_repo | test_case_repo |    │
│  judge_log_repo | audit_log_repo | similarity_repo                │
├──────────────────────────────────────────────────────────────────┤
│  工具层 (app/utils/)                                              │
│  sanitize | deps | response | time_utils                          │
└────────────────────────────────┬────────────────────────────────┘
                                 │ aiosqlite
                    ┌────────────▼────────────┐
                    │   SQLite (data/oj.db)    │
                    │   + data/backups/        │
                    └─────────────────────────┘
```

## 3. 数据设计
### users 表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT | UUID 主键 |
| username | TEXT | 唯一用户名 |
| password_hash | TEXT | bcrypt 哈希 |
| role | TEXT | student/teacher/admin |
| is_active | INTEGER | 是否启用（0/1） |
| created_at | TEXT | 创建时间 |
| updated_at | TEXT | 更新时间 |

### problems 表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT | 题目编号（主键） |
| title | TEXT | 标题 |
| description | TEXT | 描述 |
| input_description | TEXT | 输入说明 |
| output_description | TEXT | 输出说明 |
| samples | TEXT | 公开样例（JSON） |
| constraints | TEXT | 约束条件 |
| test_cases | TEXT | 测试点（JSON，含 input/output/score/is_hidden） |
| difficulty | TEXT | easy/medium/hard |
| tags | TEXT | 标签（JSON 数组） |
| time_limit | REAL | 超时秒数 |
| memory_limit | INTEGER | 内存限制（MB） |
| judge_mode | TEXT | 评测模式：standard/strict/spj |
| spj_code | TEXT | Special Judge 代码（仅 spj 模式） |
| created_at | TEXT | 创建时间 |
| updated_at | TEXT | 更新时间 |

### submissions 表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT | UUID 主键 |
| user_id | TEXT | 提交用户 |
| problem_id | TEXT | 题目编号 |
| language | TEXT | 编程语言 |
| source_code | TEXT | 源代码 |
| status | TEXT | pending/running/finished/failed |
| result | TEXT | AC/WA/RE/TLE/SE |
| score | INTEGER | 总得分 |
| total_time | REAL | 总运行时间 |
| created_at | TEXT | 创建时间 |
| updated_at | TEXT | 更新时间 |

### judge_logs 表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT | UUID 主键 |
| submission_id | TEXT | 关联提交 |
| case_id | TEXT | 测试点编号 |
| result | TEXT | AC/WA/RE/TLE/SE |
| score | INTEGER | 得分 |
| time_used | REAL | 运行时间 |
| memory_used | INTEGER | 内存使用 |
| exit_code | INTEGER | 退出码 |
| stdout | TEXT | 标准输出 |
| stderr | TEXT | 标准错误 |
| input_data | TEXT | 输入数据 |
| expected_output | TEXT | 期望输出 |
| message | TEXT | 错误信息 |
| is_hidden | INTEGER | 是否隐藏 |
| created_at | TEXT | 创建时间 |

### audit_logs 表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT | UUID 主键 |
| operator_id | TEXT | 操作者 |
| action | TEXT | 操作类型 |
| target_type | TEXT | 目标类型 |
| target_id | TEXT | 目标 ID |
| success | INTEGER | 是否成功 |
| detail | TEXT | 详情 |
| created_at | TEXT | 创建时间 |

### test_cases 表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT | UUID 主键 |
| problem_id | TEXT | 关联题目 |
| case_id | TEXT | 测试点编号 |
| input | TEXT | 输入数据 |
| expected_output | TEXT | 期望输出 |
| score | INTEGER | 分值 |
| is_hidden | INTEGER | 是否对学生隐藏 |

### similarity_reports 表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT | UUID 主键 |
| problem_id | TEXT | 关联题目 |
| submission_a | TEXT | 提交 A 的 ID |
| submission_b | TEXT | 提交 B 的 ID |
| similarity | REAL | 相似度（0~1） |
| method | TEXT | 检测方法（ast） |
| created_at | TEXT | 创建时间 |

### backups 表
| 字段 | 类型 | 说明 |
|------|------|------|
| backup_id | TEXT | 备份 ID（主键） |
| created_at | TEXT | 创建时间 |

### 备份记录
存储在 `data/backups/` 目录，每个备份包含数据库文件快照和 manifest.json。

## 4. 核心实现

### 异步评测
提交代码后，`create_and_judge` 函数先创建 pending 状态的提交记录，然后通过 FastAPI 的 `BackgroundTasks.add_task` 启动后台评测任务，立即返回 202 给客户端。评测任务在后台执行，不阻塞提交接口。

### 运行和终止学生代码
使用同步 `subprocess.run` 通过 `asyncio.run_in_executor` 在线程池中运行 `python main.py`（避免 Windows 事件循环兼容问题）。通过 `subprocess.run` 的 `timeout` 参数设置超时，并结合 `time.perf_counter()` 双重检查运行时间，超时后判定 TLE。评测完成后自动清理临时目录。

### 判断 AC、WA、RE、TLE、SE
- **TLE**：子进程运行超时
- **SE**：子进程启动失败（如系统错误）
- **RE**：子进程退出码非 0
- **WA**：输出与期望不匹配（经规范化比较）
- **AC**：输出与期望匹配
- 遇到 TLE/RE/SE 时停止后续测试点

### 输出比较
`compare_output` 函数执行规范化比较：
1. 统一换行符（`\r\n` 和 `\r` 统一为 `\n`）
2. 按 `\n` 分割为行
3. 去除每行尾部空白（空格和制表符）
4. 去除末尾空行
5. 逐行比较

### 提交状态管理
状态机：`pending → running → finished/failed`
- pending：已创建，等待评测
- running：正在评测
- finished：评测完成
- failed：评测系统错误
- 重测时：finished/failed → pending（通过 status 冲突检测防止并发问题）

### 权限校验
通过 FastAPI 的 Depends 依赖注入实现：
- `get_current_user`：从 Session 获取用户，检查登录状态、用户存在性和启用状态
- `RequireRole`：在 `get_current_user` 基础上检查角色
- 路由内额外检查资源所有权（如学生只能查看自己的提交）

### 隐藏测试点处理
- `to_student_log_view`：测试点数据结构中存储 `is_hidden: bool`
  - 对**所有测试点**返回 stdout（学生需要看到自己的输出）
  - 对**隐藏测试点不返回** expected_output（保护答案）
  - 对**非隐藏测试点返回** stdout 和 expected_output
- `to_teacher_log_view`：返回全部字段

### 脱敏和截断
- `sanitize_error_message`：将临时目录绝对路径替换为 `<submission>/`
- `truncate_text`：超长文本截断为 4000 字符并添加 `...[truncated]`
- 所有输出字段（stdout、expected_output、stderr、message）均进行截断
- 学生视角的 stderr 和 message 额外经过脱敏处理

### 持久化和恢复
- 使用 SQLite 文件数据库，所有数据写入磁盘
- 备份：复制数据库文件，创建 manifest.json
- 恢复：校验 manifest 和备份文件，先保存当前数据为安全副本，再替换数据库文件
- 损坏备份恢复失败时，当前数据不受影响

### 前端登录状态
- 使用 Cookie-Session，浏览器自动管理 Cookie
- 页面加载时调用 `GET /api/auth/me` 检查登录状态
- 登录失效时显示登录页面和错误提示
- 凭据模式：`credentials: 'include'`

### 前端调用后端接口，展示提交成果
- 封装统一的 `api(method, path, body)` 函数，使用 `fetch` API 发起请求，所有请求携带 `credentials: 'include'` 以传递 Cookie
- 后端返回的 FastAPI 默认错误格式（`{detail: ...}`）和项目自定义格式（`{code, message, data}`）统一转换处理
- 提交详情页使用 `Promise.all` 并发请求提交信息（`GET /api/submissions/{id}`）和评测日志（`GET /api/submissions/{id}/logs`）
- 评测中（pending/running）的提交通过 `setTimeout` 每 2 秒自动轮询刷新，直到评测完成
- 网络错误统一捕获并返回友好提示信息

## 5. API 说明

### 认证
| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | /api/auth/register | 无 | 用户注册，返回 201 |
| POST | /api/auth/login | 无 | 用户登录，被禁用返回 403 |
| POST | /api/auth/logout | 已登录 | 用户登出 |
| GET | /api/auth/me | 无 | 获取当前用户，未登录返回 401 |

### 用户管理
| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | /api/users | admin | 用户列表（分页） |
| GET | /api/users/{user_id} | admin | 用户详情 |
| PUT | /api/users/{user_id} | admin | 修改用户角色/状态 |

### 题目
| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | /api/problems | 无 | 题目列表（不含 test_cases） |
| GET | /api/problems/{problem_id} | 无 | 题目详情（学生不含 test_cases） |
| POST | /api/problems | teacher/admin | 创建题目，返回 201 |
| PUT | /api/problems/{problem_id} | teacher/admin | 修改题目 |
| DELETE | /api/problems/{problem_id} | teacher/admin | 删除题目 |

### 提交
| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | /api/submissions | 已登录 | 提交代码，返回 202 |
| GET | /api/submissions | 已登录 | 提交列表（学生仅自己的） |
| GET | /api/submissions/{submission_id} | 已登录 | 提交详情（学生仅自己的） |
| POST | /api/submissions/{submission_id}/rejudge | teacher/admin | 重新评测 |

### 日志
| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | /api/submissions/{submission_id}/logs | 已登录 | 评测日志（学生脱敏视图） |
| GET | /api/logs | teacher/admin | 日志检索（分页筛选） |
| GET | /api/audit-logs | admin | 审计日志查询 |

### 备份
| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | /api/admin/backups | admin | 创建备份，返回 201 |
| GET | /api/admin/backups | admin | 查询备份列表 |
| POST | /api/admin/backups/{backup_id}/restore | admin | 恢复备份 |

### 相似度检测（进阶模块）
| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | /api/problems/{problem_id}/similarity-check | teacher/admin | 对指定题目的多份提交进行相似度检测 |
| GET | /api/problems/{problem_id}/similarity-reports | teacher/admin | 获取指定题目的相似度报告列表 |

### Special Judge（进阶模块）
- SPJ 代码随题目一起通过 `spj_code` 字段创建/更新（`POST/PUT /api/problems`）
- 题目 `judge_mode` 设为 `"spj"` 时启用 Special Judge
- SPJ 是一个 Python 脚本，需定义 `judge(input_data, expected_output, actual_output)` 函数，返回 `{"accepted": bool, "message": str}` 字典。评测时系统将测试数据写入临时文件，由 SPJ 脚本读取后调用 judge 函数判定结果

### 统一错误响应
所有错误返回统一格式：`{"code": <HTTP状态码>, "message": "<错误信息>", "data": null}`

常见错误码：400（请求错误）、401（未登录）、403（权限不足）、404（资源不存在）、409（状态冲突）、422（参数校验失败）

## 6. 测试结果

使用 pytest + pytest-asyncio 进行异步测试。共51个测试项，全部通过。

### 题目管理测试
- 创建、查询、修改、删除题目
- 重复编号返回 409
- 字段校验（标题非空、测试点分数总和为 100）
- 隐藏测试点对学生不可见
- 权限控制（学生无法创建/修改/删除）

### 自动评测测试
- AC：正确输出
- WA：输出不匹配
- RE：运行时错误
- TLE：超时
- SE：评测器异常
- 多测试点分别计分
- 输出规范化（行末空格、末尾空行不影响判定）
- 临时文件评测后清理

### 用户权限测试
- 注册和登录
- 学生、教师、管理员各自可访问的接口
- 禁用用户登录返回 403
- 未登录访问受保护接口返回 401

### 提交状态测试
- 创建提交返回 202
- 状态流转：pending → running → finished
- 非法状态冲突（如对 running 状态的提交重测返回 409）
- 学生只能查看自己的提交
- 重新评测

### 日志测试
- 隐藏测试点字段裁剪
- 路径脱敏
- 输出截断
- 教师查看日志产生审计记录

### 持久化测试
- 服务重启后数据仍然存在
- 创建备份
- 恢复成功
- 损坏备份恢复失败且不破坏现有数据

## 7. 问题与解决过程

### 问题一：Cookie-Session 认证机制的跨域配置

**问题描述：** 初始实现时，前端通过 `fetch` 调用后端接口，登录成功后服务端将 `user_id` 写入 session（`request.session["user_id"] = result["id"]`），并通过 `SessionMiddleware` 自动设置 session cookie。然而后续请求中 `request.session.get("user_id")` 始终返回 `None`，导致所有需要登录的接口均返回 401 未授权错误。

**排查过程：** 
1. 检查后端 `SessionMiddleware` 配置，确认 `secret_key` 已正确设置
2. 通过浏览器开发者工具检查响应头，发现登录接口确实返回了 `Set-Cookie` 头
3. 检查后续请求的请求头，发现 Cookie 没有被自动携带

问题根源在于前端 `fetch` 的默认行为：**出于安全考虑，`fetch` 不会自动发送或保存 Cookie**，即使是同源请求。

**解决方案：** 在所有 `fetch` 请求中添加 `credentials: 'include'` 配置：

```javascript
// frontend/js/api.js
async function api(method, path, body = null) {
    const options = {
        method,
        credentials: 'include',  // 关键配置：允许发送和接收 Cookie
        headers: {'Content-Type': 'application/json'}
    };
    if (body) options.body = JSON.stringify(body);
    const resp = await fetch(`http://localhost:8000${path}`, options);
    // ...
}
```

这样配置后，浏览器会在每次请求中自动携带 session cookie，后端才能通过 cookie 中的 session_id 查找到对应的 session 数据，从而获取 `user_id` 完成身份验证。


### 问题二：评测全部返回 SE

**问题描述：** 某天打开 OJ 系统，发现所有评测提交均返回 SE（System Error），判题系统完全无法工作。起初怀疑是异步评测调度的问题，将评测方式改为 FastAPI 的 `BackgroundTasks` 后仍然无效。

**排查过程：** 通过在 `runner.py` 和 `judge_service.py` 中逐步添加断点和阶段性日志输出，逐层缩小 bug 范围，最终定位到 `runner.py` 中 `subprocess.run()` 的调用方式：

```python
# 错误写法：stdin 和 input 不能同时使用
result = subprocess.run(
    cmd, stdin=subprocess.PIPE,
    input=input_data.encode("utf-8"), ...
)
```

Python 文档明确指出 `input` 参数与 `stdin=subprocess.PIPE` 不能同时传入，否则会抛出 `ValueError`，导致所有提交的子进程启动失败，评测结果统一为 SE。

**解决方案：** 移除 `stdin=subprocess.PIPE`，仅保留 `input` 参数——当提供 `input` 时，Python 会自动将 stdin 设为 PIPE 并写入数据。



## 8. AI 工具使用说明

- 使用了 Cline编程工具，接了中转站API (模型为opus 4.6) 辅助开发
- AI 参与的工作：代码架构设计、部分函数实现（如pytest、前端界面、部分路由文件）、错误排查
- 验证方式：逐文件审查 AI 生成的代码，确保与规范一致；手动测试所有接口；运行 pytest 测试
- 本人修改和确认：所有核心逻辑均经本人审查和修改，确保安全性和正确性