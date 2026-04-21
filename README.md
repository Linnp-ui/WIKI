# WIKI 系统

一个基于 React 19 和 Python 的知识库管理系统，支持文档 ingestion、查询、可视化和管理。

## 项目结构

```
WIKI/
├── frontend/            # React 19 + Vite 前端 (Ant Design, Redux Toolkit)
├── backend/             # Python 后端 API
├── wiki/                # Wiki 内容 (Markdown 文件)
│   ├── concepts/        # 概念定义
│   ├── entities/        # 实体信息
│   └── summaries/       # 源摘要
├── scripts/             # Python CLI 脚本
├── schema/              # 系统提示和模板
├── raw_sources/         # 只读原始文档
├── config.yaml          # 配置
└── PRD.md               # 项目规范
```

## 快速开始

### 前端开发

```bash
cd frontend
npm install
npm run dev      # 启动开发服务器
```

### 后端开发

```bash
cd backend
pip install -r requirements.txt
python main.py   # 启动后端服务器
```

## 核心功能

- **文档摄入**：添加文件到 `raw_sources/`，然后运行 `python scripts/ingest.py <file>`
- **查询**：使用 `python scripts/query.py "question"` 进行查询
- **检查**：使用 `python scripts/lint.py` 检查系统状态
- **前端界面**：提供直观的 Web 界面进行内容管理和查询

## 技术栈

- **前端**：React 19, Vite, Ant Design, Redux Toolkit
- **后端**：Python, FastAPI
- **存储**：Markdown 文件系统
- **部署**：支持容器化部署

## 系统要求

- Node.js 18+
- Python 3.10+
- pip 包管理器

## 贡献指南

1. Fork 项目
2. 创建特性分支
3. 提交更改
4. 推送到分支
5. 开启 Pull Request

## 许可证

MIT License
