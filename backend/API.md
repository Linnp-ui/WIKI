# 后端 API 文档

## 概述

LLM Wiki 后端 API 提供了一系列端点，用于管理 Wiki 内容、系统状态和文档摄入。API 基于 FastAPI 构建，提供了 RESTful 接口。

## 基础 URL

所有 API 端点的基础 URL 为：`http://localhost:3000/api`

## 系统状态和配置

### GET /system/status

获取系统状态信息。

**响应**：

```json
{
  "status": "ok",
  "version": "1.0.0",
  "wiki_pages": 42
}
```

### GET /system/config

获取系统配置信息。

**响应**：

```json
{
  "wiki_dir": "wiki",
  "raw_sources_dir": "raw_sources",
  "schema_dir": "schema"
}
```

### POST /system/ingest

上传并摄入文档到系统。

**参数**：
- `file` (multipart/form-data)：要上传的文件

**响应**：

```json
{
  "message": "Document ingested successfully",
  "file": "example.pdf"
}
```

### POST /system/lint

运行系统检查，包括查找孤立页面、损坏链接、逻辑矛盾和未建立的术语。

**响应**：

```json
{
  "orphan_pages": ["path/to/orphan"],
  "broken_links": ["path/to/broken/link"],
  "contradictions": ["path/to/contradiction"],
  "unestablished_terms": ["term1", "term2"]
}
```

## Wiki 页面管理

### GET /wiki/pages

获取所有 Wiki 页面。

**响应**：

```json
[
  {
    "id": "concepts/transformer-architecture",
    "title": "Transformer Architecture",
    "path": "concepts/transformer-architecture.md",
    "frontmatter": {
      "source": "original-source"
    },
    "content": "# Transformer Architecture\n..."
  },
  ...
]
```

### GET /wiki/pages/{page_id}

根据 ID 获取特定 Wiki 页面。

**参数**：
- `page_id` (路径参数)：页面 ID，例如 "concepts/transformer-architecture"

**响应**：

```json
{
  "id": "concepts/transformer-architecture",
  "title": "Transformer Architecture",
  "path": "concepts/transformer-architecture.md",
  "frontmatter": {
    "source": "original-source"
  },
  "content": "# Transformer Architecture\n..."
}
```

### POST /wiki/pages

创建新的 Wiki 页面。

**请求体**：

```json
{
  "id": "concepts/new-concept",
  "content": "# New Concept\n..."
}
```

**响应**：

```json
{
  "id": "concepts/new-concept",
  "title": "New Concept",
  "path": "concepts/new-concept.md",
  "frontmatter": {},
  "content": "# New Concept\n..."
}
```

### PUT /wiki/pages/{page_id}

更新现有的 Wiki 页面。

**参数**：
- `page_id` (路径参数)：页面 ID

**请求体**：

```json
{
  "content": "# Updated Concept\n..."
}
```

**响应**：

```json
{
  "id": "concepts/transformer-architecture",
  "title": "Transformer Architecture",
  "path": "concepts/transformer-architecture.md",
  "frontmatter": {},
  "content": "# Updated Concept\n..."
}
```

### DELETE /wiki/pages/{page_id}

删除 Wiki 页面。

**参数**：
- `page_id` (路径参数)：页面 ID

**响应**：

```json
{
  "message": "Page deleted successfully"
}
```

## 搜索功能

### GET /search

搜索 Wiki 页面内容。

**参数**：
- `query` (查询参数)：搜索关键词

**响应**：

```json
{
  "results": [
    {
      "id": "concepts/transformer-architecture",
      "title": "Transformer Architecture",
      "snippet": "# Transformer Architecture\nThis is a snippet of the content..."
    },
    ...
  ],
  "count": 2
}
```

## 根端点

### GET /

API 根端点，返回基本信息。

**响应**：

```json
{
  "message": "LLM Wiki API",
  "version": "1.0.0"
}
```

## 错误处理

API 使用标准 HTTP 状态码来表示错误：

- `400 Bad Request`：请求参数错误
- `404 Not Found`：资源不存在
- `500 Internal Server Error`：服务器内部错误

错误响应格式：

```json
{
  "detail": "Error message describing the issue"
}
```
