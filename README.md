# SQM 供应商与质量管理系统 (Supplier Quality Management)

> 基于 **Python FastAPI + Vue 3 + TypeScript + Element Plus** 构建的完全独立、解耦、轻量级供应商质量管理系统。采用零鉴权免密直进设计理念，面向智能制造与人形机器人研发制造全流程。

---

## 🌟 核心架构与设计特性

### 1. 前后端物理彻底解耦与功能分类规范
- **一级分类与中文编号体系**：
  - `1. MainData（主数据）`：`1.1 供应商清单` (`SupplierList.vue`)、`1.2 零件清单` (`PartList.vue`)、`1.3 项目清单` (`ProjectList.vue`)
  - `2. SQM（供应商质量管理）`：`2.1 零件开发管理` (`PartDevList.vue`)、`2.2 质量问题清单` (`QualityIssueList.vue`)
  - `3. CTQ（关键质量特性）`：`3.1 关键特征清单` (`CTQList.vue`)
- **Feature Folders 物理解耦**：列表视图 (`*List.vue`) 与抽屉表单 (`*Form.vue`) 分治放置于各业务子目录，坚决拒绝巨石单文件与高耦合逻辑。

### 2. 前端 70% 宽幅沉浸式抽屉与 Dirty Check 防呆套件
- 所有新增/编辑动作统一由全局 `<DrawerContainer>`（70% 视窗宽度）以平滑抽屉承载。
- 集成 `useDirtyCheck` 状态比对钩子：在表单打开时捕获初始快照，若用户在未保存状态下点击遮罩或右上角关闭，**强制弹出 Element Plus 二次警示确认框**，有效阻止一线工程师误关丢失输入数据。

### 3. 开发态 AI 提词器 (Teleprompter)
- 全局挂载 `components/dev/teleprompter/` 套件。
- 键盘按下快捷键 **Alt+X** 随时唤起，接管鼠标并高亮页面任意 DOM 元素，一键提取信标元数据并生成投递提示词复制至剪贴板。

### 4. 动态流式附件存储与自包含组件包
- **后端通用存储引擎** (`r_storage.py` + `sys_attachment`)：采用 `storage/files/{biz_type}/{YYYYMM}/{uuid}.ext` 动态分片流式落盘与防路径穿透安全校验，彻底废弃写死分类。
- **前端独立上传组件** (`components/uploader/`)：支持拖拽上传、文件格式图标渲染、流式直传进度条与业务外键两阶段延迟绑定 (`bindToBizId`)。
- **前端独立富文本组件** (`components/editor/`)：集成 WangEditor 5，内置图片直接上传至后端动态存储通道。

### 5. Alembic 纯增量零删表平滑演进
- 严格遵循生产级增量演进规范，全量数据表支持增量迁移脚本，绝不执行任何 `DROP TABLE` 或强行推平数据库的行为，确保既有数据与历史表资产 100% 完好无损。

---

## 📁 物理工程结构目录

```text
d:/AIAPP/Tars/
├── backend/                  # Python FastAPI 后端服务根目录
│   ├── alembic/              # Alembic 增量版本迁移目录 (4个增量修订链)
│   ├── app/
│   │   ├── core/             # 数据库引擎与 Pydantic 设置
│   │   ├── models/           # SQLAlchemy ORM 实体数据模型
│   │   │   ├── attachment.py # sys_attachment 通用附件表
│   │   │   ├── main_data.py  # sqm_supplier, sqm_project, sqm_part
│   │   │   ├── sqm_quality.py# sqm_part_dev, sqm_quality_issue
│   │   │   └── ctq.py        # sqm_ctq 关键特性表
│   │   ├── routers/          # FastAPI 业务路由端点 (RESTful API)
│   │   │   ├── r_storage.py  # 动态存储分发与富文本上传
│   │   │   ├── r_maindata.py # 供应商、项目、零件 CRUD
│   │   │   ├── r_sqm.py      # 零件开发看板、质量问题台账
│   │   │   └── r_ctq.py      # CTQ 关键质量特性规格配置
│   │   ├── schemas/          # Pydantic 输入输出契约定义
│   │   └── main.py           # FastAPI 服务主入口与中间件
│   ├── requirements.txt      # 后端生产依赖清单
│   └── tests/                # 自动化测试套件 (覆盖全链路与迁移安全)
│
├── frontend/                 # Vue 3 前端工程
│   ├── src/
│   │   ├── components/       # 独立自包含通用组件包
│   │   │   ├── common/       # DrawerContainer.vue, useDirtyCheck.ts
│   │   │   ├── dev/          # teleprompter/ AI 提词器组件
│   │   │   ├── editor/       # WangEditor 5 富文本组件包
│   │   │   └── uploader/     # 流式拖拽文件上传组件包
│   │   ├── layout/           # LeftSidebar.vue 中文编号导航
│   │   ├── router/           # 前端免密直进路由配置
│   │   └── views/            # 功能业务目录 (物理彻底解耦)
│   │       ├── 1_maindata/   # 1.1_supplier, 1.2_part, 1.3_project
│   │       ├── 2_sqm/        # 2.1_part_dev, 2.2_quality_issue
│   │       └── 3_ctq/        # 3.1_ctq
│   └── package.json
│
├── storage/                  # 顶级动态流式存储目录
│   └── files/                # files/{biz_type}/{YYYYMM}/{uuid}.ext
│
├── .env                      # 本地运行环境动态配置 (gitignored)
├── .env.example              # 目标机部署模版 (密码已对齐 Tars123451)
├── 任务清单.csv               # 任务全生命周期主控表 (UTF-8-BOM)
├── 任务清单.html              # 任务交互式大屏看板
└── start_dev.bat             # Windows 一键启动开发环境脚本
```

---

## 🚀 快速启动与操作指南

### 1. 环境准备
- **操作系统**：Windows 10 / 11 / Server
- **Python**：3.10+
- **Node.js**：18.0+
- **MySQL**：8.0+ / 9.0+（端口 3306，数据库编码 `utf8mb4`）

### 2. 数据库与配置说明
在根目录确认或创建 `.env` 文件：
```ini
# 数据库配置
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
# 本地开发机器密码为 Zhang19830310；目标部署机器密码为 Tars123451
DB_PASSWORD=Zhang19830310
DB_NAME=sqm

# 动态附件存储相对或绝对路径
STORAGE_ROOT_PATH=../storage

# 后端服务监听
SERVER_HOST=0.0.0.0
SERVER_PORT=8010
```

### 3. 便捷启动脚本 (根目录下提供)
- **一键启动全部（前后端并行）**：双击根目录 `start_dev.bat`，自动打开独立窗口拉起前后端服务；
- **单独启动后端**：双击 `start_backend.bat`（FastAPI 服务，监听端口 `8010`）；
- **单独启动前端**：双击 `start_frontend.bat`（Vue 3 + Vite，监听端口 `3001`）。

**访问地址**：
- **前端免密直进工作台**：`http://localhost:3001`
- **后端交互式 Swagger 文档**：`http://localhost:8010/docs`
- **服务健康体检端点**：`http://localhost:8010/api/health`

### 4. 增量热升级迁移命令 (Alembic)
在需要更新数据结构或迁移至目标部署机时，在 `backend/` 目录下执行：
```bash
python -m alembic upgrade head
```
系统将自动按版本序列平滑升级，现有业务表与历史测试数据保持完好无损。

---

## 🔮 二期维护与功能插槽设计

1. **8D 复杂质量改善工作流插槽**：
   - 当前已在 `sqm_quality_issue` 中实现轻量化登记、现象富文本描述、整改措施富文本与报告归档。
   - 二期可在此基础上挂接 D0~D8 节点审批状态流与责任人签核流。
2. **SPC 过程能力自动计算插槽**：
   - `sqm_ctq` 已规范定义 KPC/KCC 特征、公差规格、检验工具与检验频次。
   - 二期可无缝挂载实测样本量测数据收集表，直接生成 Xbar-R、Xbar-S 控制图与 CPK 计算报表。
3. **企业微信 / 钉钉待办消息推送插槽**：
   - 在 `r_sqm.py` 的问题单据创建与状态流转回调钩子中，预留了 Webhook 消息通知插槽。
