# 智能合同审查核心链路

基于 LangGraph 的四 Agent 合同审查演示项目：

`登录 -> 上传合同 -> 条款提取 -> 风险识别/合规检查并行 -> 修改建议 -> 网页报告/PDF`

## 技术栈

- 前端：React 19、TypeScript、Vite、Tailwind CSS、Nginx
- 后端：FastAPI、LangGraph、SQLAlchemy Async、PostgreSQL
- 模型：OpenAI 兼容接口（通义千问、DeepSeek、MiniMax、OpenAI 或本地 vLLM）

## 一键启动

需要 Docker Desktop 或 Docker Engine（含 Compose）：

```powershell
docker compose up -d --build
```

启动完成后访问：

- Web 控制台：<http://localhost:5173>
- Swagger：<http://localhost:8000/docs>
- 健康检查：<http://localhost:8000/api/v1/health>

默认账号：

```text
admin / admin123
```

数据库为空时，后端会在启动阶段调用 `Base.metadata.create_all` 创建 `users`、`reviews`、`clauses`、`risk_findings`、`compliance_findings`、`suggestions` 表，并加载默认账号。

## 配置模型

不配置模型 Key 也能跑通完整流程：四个 Agent 会使用规则和启发式结果降级，并在界面和 PDF 中标注降级步骤。

启用真实模型调用：

```powershell
Copy-Item .env.example .env
```

然后编辑根目录 `.env`，填写任一模型配置。Compose 会自动读取根目录 `.env`。

## 接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/v1/auth/login` | 登录并获取 JWT |
| POST | `/api/v1/review/upload` | 上传单个合同，异步返回 `review_id` |
| GET | `/api/v1/review/{id}` | 查询进度和完整审查结果 |
| GET | `/api/v1/review/{id}/report` | 下载 PDF 报告，需要 Bearer Token |
| GET | `/api/v1/health` | 健康检查 |

支持 TXT、PDF、DOCX，默认最大 20 MB。

## 本地测试

```powershell
cd python
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
```

前端构建：

```powershell
cd frontend
npm ci
npm run build
```

## 运行约束

- 审查任务在当前后端进程中异步执行，因此 Docker 后端固定为单 worker。
- 容器重启会终止尚未完成的审查；已完成报告保存在 PostgreSQL 中。
- 仅保留单文件上传，不包含注册、历史列表、批量审查、人工复核、RAG、BadCase 或规则/模板管理。
- 生产环境必须替换 `JWT_SECRET_KEY` 和 PostgreSQL 默认密码。
