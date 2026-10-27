# 多格式文档知识库检索问答系统

面向校园通知查询的 RAG（Retrieval-Augmented Generation，检索增强生成）应用。系统将文档与图片中的文本建立为可检索知识库，结合大模型生成回答，并返回对应的来源信息。

本项目由个人独立开发，作为本科毕业设计。实现覆盖文档接入、文本切分、向量索引、检索生成、流式响应和知识库管理，可用于展示大模型应用后端与 RAG 工程实践。

**当前代码状态：**后端主要源码与前端构建产物已包含在目录中；`frontend/src/` 尚缺少 `main.tsx` 及页面组件，当前文件集合不能直接重新构建前端。后端可以按下文单独配置与运行，前端开发启动步骤需在补齐源码后使用。

## 核心功能

### 文档接入与知识库构建

- 解析 PDF、DOCX、TXT 文本，使用 EasyOCR 提取图片中的中英文内容。
- 使用 LangChain 的 `RecursiveCharacterTextSplitter` 进行递归切分，支持中文标点与段落分隔。
- 分批调用 Embedding 接口，将片段向量及文本持久化至 Chroma。
- 为片段关联文档 ID 与片段序号，支持按文档删除对应向量。
- 使用 SQLite 保存用户、文档信息、问答历史、会话和收藏等业务数据。

### 检索与回答

- 对问题进行向量化，执行 Top-K 余弦相似度检索，并通过阈值过滤低相关片段。
- 组合带来源编号的上下文，引导模型根据知识库内容回答。
- 返回来源标题、原文链接、描述及检索相关分数，便于用户回查。
- 支持普通响应和基于 SSE 的流式文本输出。
- 检索未命中时返回提示；模型调用失败时返回相关检索片段作为降级结果。

### 管理与交互

- 文档上传、列表、元信息修改、删除，以及文档数和片段数统计。
- 调用文本模型或视觉模型，辅助提取通知标题与摘要。
- 网页正文采集、清洗及 DOCX 转换，转换结果可再通过上传接口入库。
- JWT 登录、密码哈希及管理员接口角色校验。
- 问答历史、会话保存与管理、收藏及原会话定位。
- 提供本机截图接口：截图对象是后端所在机器的桌面，适用于本地演示。

## 技术栈

| 层次 | 技术与用途 |
| --- | --- |
| 后端服务 | Python、FastAPI、Uvicorn、Pydantic |
| 文本切分 | LangChain Text Splitters |
| 模型接入 | OpenAI Python SDK，调用兼容 OpenAI 协议的模型服务 |
| 向量检索 | Chroma，持久化存储与余弦相似度检索 |
| 业务存储 | SQLAlchemy、SQLite |
| 文档解析 | python-docx、PyPDF2、pdfplumber |
| 图片文本提取 | EasyOCR，当前代码使用 CPU 模式 |
| 网页采集 | HTTPX、Beautiful Soup |
| 认证 | JWT、bcrypt |
| 前端工程 | React、TypeScript、Vite、Tailwind CSS、Axios |

实际应用使用 Qwen 语言模型与视觉模型；模型名称和服务地址可通过环境变量调整。模型推理与 Embedding 通过外部 API 完成，本项目不包含模型训练或本地推理引擎实现。

LangChain 在当前实现中主要用于文本切分，检索与生成链路由项目代码组织。

## 系统流程

```text
知识库构建

PDF / DOCX / TXT / 图片
          │
          ▼
   文本提取 / 图片 OCR
          │
          ▼
      递归文本切分
          │
          ▼
    分批调用 Embedding
          │
          ▼
  Chroma 片段与向量存储

SQLite 保存文档信息与业务记录，通过文档 ID 与向量片段关联。
```

```text
检索问答

用户问题 → 问题 Embedding → Top-K 向量检索 → 相关分数过滤
                                                   │
                                      ┌────────────┴────────────┐
                                      ▼                         ▼
                                未命中提示             查询文档信息与拼接上下文
                                                                │
                                                                ▼
                                                           大模型生成
                                                                │
                                                                ▼
                                                   普通回答 / SSE 文本与来源
```

图片入库使用 OCR 后的文本；视觉模型用于辅助生成图片标题与摘要。当前实现不包含图像向量与文本向量的跨模态联合检索。

## 项目结构

```text
.
├── backend/
│   ├── main.py                 # FastAPI 入口与路由注册
│   ├── config.py               # 环境变量与配置
│   ├── database.py             # 数据模型与数据库会话
│   ├── auth.py                 # 密码哈希、JWT 与角色校验
│   ├── document_processor.py   # 文件解析、OCR 与文本切分
│   ├── vector_store.py         # Embedding、Chroma 索引与查询
│   ├── rag_service.py          # 提示词、生成、来源与流式响应
│   ├── seed.py                 # 本地演示账号初始化
│   ├── requirements.txt
│   └── routes/
│       ├── auth.py             # 登录、注册与当前用户
│       ├── admin.py            # 文档管理、采集与统计
│       └── qa.py               # 问答、会话、历史与收藏
├── frontend/
│   ├── src/                   # 当前仅包含部分源码，待补齐页面组件
│   ├── dist/                  # 已有前端构建产物
│   ├── package.json
│   └── vite.config.ts         # 开发端口 3000，代理 /api 到 8000
├── run_backend.bat
├── run_frontend.bat
└── start.bat
```

## 本地运行

以下命令以 **Windows PowerShell** 为例，从项目根目录执行。需要本地 Python、Node.js/npm，以及可访问的文本模型与 Embedding 服务。图片摘要另需可用的视觉模型服务。

依赖清单暂未锁定全部版本，当前不提供已经验证的跨环境兼容性矩阵。

### 1. 安装后端依赖

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r .\backend\requirements.txt
```

图片 OCR 依赖 EasyOCR 及其模型文件，首次使用可能需要下载。服务器环境应提前准备对应资源。

### 2. 配置模型与数据路径

在 `backend/` 下新建 `.env` 文件，将以下占位值替换为实际配置。请勿提交包含真实密钥的 `.env`。

```dotenv
SECRET_KEY=REPLACE_WITH_A_LONG_RANDOM_SECRET

# 文本与视觉模型使用同一组客户端地址和凭据。
LLM_API_KEY=YOUR_MODEL_API_KEY
LLM_BASE_URL=YOUR_OPENAI_COMPATIBLE_BASE_URL
LLM_MODEL=YOUR_CHAT_MODEL_ID
VISION_MODEL=YOUR_VISION_MODEL_ID

# Embedding 可以使用独立服务。
EMBEDDING_API_KEY=YOUR_EMBEDDING_API_KEY
EMBEDDING_BASE_URL=YOUR_EMBEDDING_BASE_URL
EMBEDDING_MODEL=YOUR_EMBEDDING_MODEL_ID

DATABASE_URL=sqlite:///./campus_rag.db
CHROMA_PERSIST_DIR=./chroma_db
CHROMA_COLLECTION_NAME=campus_notifications
UPLOAD_DIR=./uploads

CHUNK_SIZE=500
CHUNK_OVERLAP=50
RETRIEVAL_TOP_K=5
RETRIEVAL_MIN_SCORE=0.5
```

注意：

- `BASE_URL` 应填写模型服务商提供的完整 API 基础地址，不能保留占位文本。
- 当前 `config.py` 的文本模型默认名称仍为 `gpt-3.5-turbo`。使用 Qwen 时须显式设置对应地址、凭据与模型标识。
- 视觉模型与文本模型共享客户端，应确认所配置的服务同时支持所选模型与图片消息格式。
- 相对数据路径与 `.env` 读取依赖启动工作目录，因此后续从 `backend/` 启动服务。
- 切换到不同向量维度或不兼容的 Embedding 模型时，应使用新的 collection 并重新建立索引，避免混用旧向量。

### 3. 初始化并启动后端

```powershell
Set-Location .\backend

# 可选：创建本地演示账号，账号信息见 seed.py。
..\.venv\Scripts\python.exe seed.py

..\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

启动后访问：

- 接口文档：<http://127.0.0.1:8000/docs>
- 健康检查：<http://127.0.0.1:8000/api/health>

`seed.py` 中的固定演示账号仅用于本地测试。首次启动也会自动创建数据库表，初始化演示用户不是建表的必要条件。

现有 `start.bat` 和 `run_backend.bat` 中包含开发机器的固定 Python 路径，其他环境应按上述命令启动，或先修改脚本中的解释器路径。

### 4. 前端启动条件

当前目录缺少 `frontend/src/main.tsx` 及页面组件，请先补齐完整前端源码。补齐后，在新终端从项目根目录执行：

```powershell
Set-Location .\frontend
npm ci
npm run dev
```

开发页面默认位于 <http://localhost:3000>，Vite 将 `/api` 请求代理至本机 8000 端口。

`frontend/dist/` 是构建产物，不能替代可维护的前端源码；当前后端没有直接挂载该静态目录。

## 使用流程

1. 调用登录接口取得令牌，后续请求在 `Authorization` 头中携带 `Bearer <token>`。
2. 管理员上传通知文档；可先调用分析接口辅助生成标题与摘要。
3. 系统提取文本、切分并写入向量索引，保存文档信息。
4. 用户提交自然语言问题，获取回答与来源；流式接口逐段返回生成内容。
5. 按需保存会话、查看历史或收藏回答，管理员维护知识库内容。

示例问题可围绕已上传的通知，例如：“奖学金申请的截止时间是什么？”或“这份活动通知要求提交哪些材料？”回答范围取决于实际知识库内容。

## 主要接口

除登录、注册和健康检查外，业务接口需要登录令牌；管理员接口另有角色检查。

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/api/health` | 服务健康检查 |
| POST | `/api/auth/register` | 注册 |
| POST | `/api/auth/login` | 登录，JSON 请求体 |
| GET | `/api/auth/me` | 查询当前用户 |
| POST | `/api/admin/documents/analyze` | 辅助提取标题与摘要 |
| POST | `/api/admin/documents/upload` | 文档上传与索引 |
| GET | `/api/admin/documents` | 文档列表 |
| PUT / DELETE | `/api/admin/documents/{doc_id}` | 修改元信息或删除文档 |
| GET | `/api/admin/stats` | 知识库统计 |
| POST | `/api/admin/scrape` | 网页采集与 DOCX 转换 |
| POST | `/api/admin/screenshot` | 后端机器截图 |
| POST | `/api/qa/ask` | 普通问答 |
| POST | `/api/qa/ask/stream` | SSE 流式问答 |
| GET | `/api/qa/history` | 问答历史 |
| GET / POST | `/api/qa/conversations` | 会话列表与保存 |
| GET / PUT / DELETE | `/api/qa/conversations/{conversation_id}` | 单个会话管理 |
| GET / POST | `/api/qa/bookmarks` | 收藏列表与新增 |

详细请求字段与其余历史、收藏操作见后端自动生成的接口文档。

流式接口使用 `POST` 请求，返回 `text/event-stream`，事件由 `data:` 行承载 JSON，包含 `thinking`、`answer`、`sources` 类型，最后发送 `[DONE]`。`thinking` 是界面状态提示，不是模型内部推理过程。

## 默认参数与实现边界

| 配置项 | 默认值 | 含义 |
| --- | --- | --- |
| `CHUNK_SIZE` | 500 | 文本切分长度配置，按字符计量 |
| `CHUNK_OVERLAP` | 50 | 相邻文本块重叠长度配置 |
| `RETRIEVAL_TOP_K` | 5 | 初始检索数量 |
| `RETRIEVAL_MIN_SCORE` | 0.5 | 检索相关分数过滤阈值 |

这些是初始配置，不代表经过评测得到的最优参数。相关分数根据余弦距离换算，不能当作答案可信概率。

- 当前实现采用文本向量检索，尚未实现 BM25 混合检索、重排序、知识图谱多跳检索。
- 会话记录可以保存和恢复，但生成请求当前没有传入历史消息，不等同于支持多轮上下文推理。
- PDF 路径用于文本提取，扫描版 PDF 暂未自动执行 OCR；DOCX 主要提取段落，未专门解析表格。
- 接口虽然接受 `.doc` 扩展名，但解析器实际使用 `python-docx`，旧版二进制 DOC 建议先转换成 DOCX。
- 来源编号依赖提示词约束，尚未实现逐条引用内容的一致性校验。
- 尚未提供准确率、引用准确率、首字延迟或并发吞吐的可复现测试结果。

## 已知待完善项

当前版本用于本地演示与工程实践。在对外部署前，需要处理以下已知问题：

- 注册接口目前接受客户端选择 `admin` 角色，需限制管理员创建流程。
- SQLite 文档写入与 Chroma 索引写入之间尚无完整失败补偿机制。
- 流式问答返回来源，但历史记录中的来源字段尚未完整保存。
- 部分异步路由内部仍调用同步解析、模型与索引接口，尚未进行专门的并发治理。
- 网页采集需要补充目标地址访问限制；截图接口需要根据部署环境关闭或限制。
- 当前 CORS 为宽泛配置，对外部署时应限制可信前端来源，并替换默认签名密钥与演示账号。

## 后续计划

- [ ] 补齐前端页面源码、配置样例与依赖版本记录。
- [ ] 建立包含答案与来源标注的评测集，评估检索命中、回答正确性和引用准确性。
- [ ] 对比切分长度、重叠长度、Top-K 与过滤阈值的影响。
- [ ] 测量检索耗时、首个答案文本到达时间、总响应时间及不同并发下的 p95 与成功率。
- [ ] 完善异步调用、失败重试、索引一致性与流式请求取消处理。
- [ ] 修复角色分配与历史来源保存问题，增加自动化测试。

## 上传仓库前

请将真实 API 密钥、环境文件、用户数据、上传原件和本地索引留在本地。配置示例使用占位符，演示资料使用允许公开的样本。

建议在项目根目录添加以下 `.gitignore` 规则：

```gitignore
# 环境变量与本地配置
.env
.env.*
!.env.example

# Python
.venv/
venv/
__pycache__/
*.py[cod]
.pytest_cache/

# 本地业务数据、上传原件与向量索引
backend/*.db
backend/*.db-*
backend/uploads/
backend/chroma_db/

# 前端依赖与编辑器文件
node_modules/
.idea/
.vscode/

# 系统文件
.DS_Store
Thumbs.db
```

自定义的数据路径也需加入忽略规则。`frontend/dist/` 是否纳入版本控制可按部署方式决定，不能用它替代源码；`package-lock.json` 建议保留。
