#!/usr/bin/env python3
"""
Backend server for LLM Wiki
"""

import os
import sys
import time
import yaml
import uvicorn
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
from contextlib import asynccontextmanager

# Add scripts directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "scripts"))

# Import functions from scripts
from ingest import ingest_file
from lint import find_orphan_pages, find_broken_links, find_logical_contradictions, find_frequent_unestablished_terms

# Global variables
wiki_pages_cache = None
cache_timestamp = 0


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    global config, WIKI_DIR, RAW_SOURCES_DIR, BASE_DIR
    
    # Load configuration
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    config_path = os.path.join(BASE_DIR, "config.yaml")
    
    if not os.path.exists(config_path):
        # Create default config if not exists
        default_config = {
            "wiki_dir": "wiki",
            "raw_sources_dir": "raw_sources",
            "llm": {
                "high": {
                    "model": "qwen-max-2025-07-28",
                    "temperature": 0.7,
                    "max_tokens": 4096
                },
                "medium": {
                    "model": "qwen-flash-2025-07-28",
                    "temperature": 0.7,
                    "max_tokens": 2048
                },
                "low": {
                    "model": "qwen-flash-2025-07-28",
                    "temperature": 0.5,
                    "max_tokens": 1024
                },
                "provider": "bailing",
                "api_key": "your_api_key_here"
            },
            "vector_store": {
                "type": "chromadb",
                "persist_directory": ".vector_store"
            }
        }
        
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(default_config, f, default_flow_style=False)
        
        config = default_config
    else:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
    
    # Set paths
    WIKI_DIR = os.path.join(BASE_DIR, config.get("wiki_dir", "wiki"))
    RAW_SOURCES_DIR = os.path.join(BASE_DIR, config.get("raw_sources_dir", "raw_sources"))
    
    # Create directories if they don't exist
    os.makedirs(WIKI_DIR, exist_ok=True)
    os.makedirs(RAW_SOURCES_DIR, exist_ok=True)
    
    # Create wiki subdirectories
    subdirs = ["concepts", "entities", "summaries"]
    for subdir in subdirs:
        os.makedirs(os.path.join(WIKI_DIR, subdir), exist_ok=True)
    
    yield
    
    # Shutdown
    pass


# Initialize FastAPI app
app = FastAPI(
    title="LLM Wiki API",
    description="API for LLM Wiki system",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models
class QueryRequest(BaseModel):
    query: str
    provider: Optional[str] = "bailing"
    api_key: Optional[str] = ""


class ChatResponse(BaseModel):
    response: str
    relevant_pages: List[Dict[str, Any]]
    can_save_as_page: bool = True
    save_prompt: str = "这段回答是否值得保存为 Wiki 页面？如需保存，请调用 /api/save-page 接口。"


class SavePageRequest(BaseModel):
    title: str
    content: str


class SavePageResponse(BaseModel):
    success: bool
    page_path: str
    message: str


class SearchResponse(BaseModel):
    results: List[Dict[str, Any]]
    count: int


# Helper functions
def get_wiki_pages(force_refresh=False) -> List[Dict[str, Any]]:
    """Get all wiki pages with caching"""
    global wiki_pages_cache, cache_timestamp

    # Check if cache is valid (not expired and not forced refresh)
    current_time = time.time()
    if (
        not force_refresh
        and wiki_pages_cache is not None
        and (current_time - cache_timestamp) < 300
    ):  # 5 minutes cache
        return wiki_pages_cache

    pages = []
    for root, _, files in os.walk(WIKI_DIR):
        for file in files:
            if file.endswith(".md"):
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, WIKI_DIR)
                page_id = os.path.splitext(relative_path.replace(os.path.sep, "/"))[0]

                # Read file content
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()

                    # Extract frontmatter if present
                    frontmatter = {}
                    if content.startswith("---"):
                        parts = content.split("---", 2)
                        if len(parts) >= 2:
                            frontmatter_lines = parts[1].strip().split("\n")
                            for line in frontmatter_lines:
                                if ":" in line:
                                    key, value = line.split(":", 1)
                                    frontmatter[key.strip()] = value.strip()

                    pages.append(
                        {
                            "id": page_id,
                            "title": os.path.splitext(file)[0]
                            .replace("-", " ")
                            .title(),
                            "path": relative_path,
                            "frontmatter": frontmatter,
                            "content": content,
                            "lastModified": os.path.getmtime(file_path),
                        }
                    )
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")

    # Update cache
    wiki_pages_cache = pages
    cache_timestamp = current_time
    return pages


def get_page_by_id(page_id: str) -> Dict[str, Any]:
    """Get a wiki page by ID with caching"""
    # First try to find in cache
    global wiki_pages_cache
    if wiki_pages_cache is not None:
        for page in wiki_pages_cache:
            if page["id"] == page_id:
                return page

    # If not in cache, read from file
    file_path = os.path.join(WIKI_DIR, f"{page_id.replace('/', os.path.sep)}.md")

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Page not found")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Extract frontmatter if present
        frontmatter = {}
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 2:
                frontmatter_lines = parts[1].strip().split("\n")
                for line in frontmatter_lines:
                    if ":" in line:
                        key, value = line.split(":", 1)
                        frontmatter[key.strip()] = value.strip()

        page = {
            "id": page_id,
            "title": os.path.splitext(os.path.basename(file_path))[0]
            .replace("-", " ")
            .title(),
            "path": os.path.relpath(file_path, WIKI_DIR).replace(os.path.sep, "/"),
            "frontmatter": frontmatter,
            "content": content,
        }

        # Update cache if it exists
        if wiki_pages_cache is not None:
            # Remove old version if exists
            wiki_pages_cache = [p for p in wiki_pages_cache if p["id"] != page_id]
            # Add new version
            wiki_pages_cache.append(page)

        return page
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading page: {str(e)}")


def save_page(page_id: str, page_data: Dict[str, Any]) -> Dict[str, Any]:
    """Save a wiki page"""
    # Convert page_id to file path
    file_path = os.path.join(WIKI_DIR, f"{page_id.replace('/', os.path.sep)}.md")

    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    # Prepare content
    content = page_data.get("content", "")

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        # Clear cache to ensure consistency
        global wiki_pages_cache, cache_timestamp
        wiki_pages_cache = None
        cache_timestamp = 0

        return get_page_by_id(page_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving page: {str(e)}")


def find_pages_by_source(source: str) -> List[Dict[str, Any]]:
    """Find wiki pages linked to a specific source file"""
    pages = get_wiki_pages()
    matching_pages = []
    for page in pages:
        frontmatter = page.get("frontmatter", {})
        page_source = frontmatter.get("source", "")
        sources_list = [s.strip() for s in page_source.split(",")]
        if source in sources_list:
            matching_pages.append(
                {"id": page["id"], "title": page["title"], "path": page["path"]}
            )
    return matching_pages


def mark_pages_as_orphan(file_id: str) -> List[str]:
    """Mark wiki pages linked to a source file as orphan"""
    pages = find_pages_by_source(file_id)
    marked_pages = []

    for page in pages:
        page_path_rel = page.get("path")
        if not page_path_rel:
            continue

        page_path = os.path.join(WIKI_DIR, page_path_rel)
        if not os.path.exists(page_path):
            continue

        try:
            with open(page_path, "r", encoding="utf-8") as f:
                content = f.read()

            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    frontmatter_text = parts[1]
                    body_content = parts[2]

                    frontmatter = {}
                    for line in frontmatter_text.strip().split("\n"):
                        if ":" in line:
                            key, value = line.split(":", 1)
                            frontmatter[key.strip()] = value.strip()

                    frontmatter["orphan"] = "true"
                    frontmatter["orphan_reason"] = "source_file_deleted"
                    frontmatter["orphaned_at"] = time.strftime("%Y-%m-%d %H:%M:%S")

                    if "source" in frontmatter:
                        sources = [s.strip() for s in frontmatter["source"].split(",")]
                        sources = [s for s in sources if s != file_id]
                        if sources:
                            frontmatter["source"] = ", ".join(sources)
                        else:
                            del frontmatter["source"]

                    new_frontmatter_lines = []
                    for key, value in frontmatter.items():
                        new_frontmatter_lines.append(f"{key}: {value}")
                    new_frontmatter = "\n".join(new_frontmatter_lines)

                    orphan_section = """
## Orphan Notice

> ⚠️ **This page is marked as orphan** - its source file has been deleted.
> The knowledge content remains available but may need manual review.

"""
                    new_body = orphan_section + body_content
                    new_content = f"---\n{new_frontmatter}\n---\n{new_body}"

                    with open(page_path, "w", encoding="utf-8") as f:
                        f.write(new_content)

                    marked_pages.append(page["id"])
                    print(f"[ORPHAN] Marked page as orphan: {page_path}")
        except Exception as e:
            print(f"[ORPHAN] Error marking page {page_path}: {e}")

    return marked_pages


def find_referencing_pages(page_id: str) -> List[Dict[str, Any]]:
    """Find pages that reference the given page via WikiLinks"""
    pages = get_wiki_pages()
    page_id_normalized = page_id.lower().replace("-", " ").replace("/", " ")
    referencing = []
    for page in pages:
        if page["id"] == page_id:
            continue
        content_lower = page["content"].lower()
        title_variants = [
            page_id.lower().replace("-", " "),
            page_id.lower().replace("/", "-"),
            page["content"].lower().split("[[")[-1].split("]]")[0]
            if "[[" in page["content"]
            else "",
        ]
        if any(variant in content_lower for variant in title_variants if variant):
            referencing.append(
                {"id": page["id"], "title": page["title"], "path": page["path"]}
            )
    return referencing


def clean_broken_links(page_id: str) -> int:
    """Remove broken WikiLinks pointing to deleted page"""
    pages = get_wiki_pages()
    cleaned_count = 0
    page_id_lower = page_id.lower()
    page_id_variants = [
        page_id.lower().replace("-", " "),
        page_id.lower().replace("/", "-"),
    ]
    for page in pages:
        if page["id"] == page_id:
            continue
        if any(variant in page["content"].lower() for variant in page_id_variants):
            content = page["content"]
            import re

            for variant in page_id_variants:
                pattern = r"\[\[" + re.escape(variant) + r"\]\]"
                if re.search(pattern, content, re.IGNORECASE):
                    content = re.sub(
                        pattern,
                        f"[[{variant} (deleted)]]",
                        content,
                        flags=re.IGNORECASE,
                    )
                    cleaned_count += 1
            if content != page["content"]:
                file_path = os.path.join(
                    WIKI_DIR, f"{page['id'].replace('/', os.path.sep)}.md"
                )
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
    return cleaned_count


def delete_page(page_id: str, auto_clean_links: bool = True) -> Dict[str, Any]:
    """Delete a wiki page"""
    file_path = os.path.join(WIKI_DIR, f"{page_id.replace('/', os.path.sep)}.md")
    print(f"[DELETE PAGE] page_id={page_id}, file_path={file_path}, exists={os.path.exists(file_path)}, WIKI_DIR={WIKI_DIR}")

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Page not found")

    # Find referencing pages before deletion
    referencing_pages = find_referencing_pages(page_id)
    cleaned_count = 0
    if auto_clean_links and referencing_pages:
        cleaned_count = clean_broken_links(page_id)

    try:
        os.remove(file_path)

        global wiki_pages_cache, cache_timestamp
        wiki_pages_cache = None
        cache_timestamp = 0

        result = {"message": "Page deleted successfully", "deleted_page_id": page_id}
        if referencing_pages:
            result["referencing_pages"] = referencing_pages
            result["cleaned_links"] = cleaned_count
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting page: {str(e)}")


def get_relevant_wiki_pages(query: str, limit: int = 3) -> List[Dict[str, Any]]:
    """Get relevant wiki pages for context enhancement using vector search"""
    try:
        from sentence_transformers import SentenceTransformer
        import chromadb
        
        pages = get_wiki_pages()
        
        if not pages:
            return []
        
        # 初始化ChromaDB
        chroma_client = chromadb.PersistentClient(path=".vector_store")
        collection = chroma_client.get_or_create_collection(name="wiki_pages")
        
        # 检查集合是否为空
        if collection.count() == 0:
            # 生成嵌入并添加到集合
            model = SentenceTransformer('all-MiniLM-L6-v2')
            
            page_ids = []
            documents = []
            metadatas = []
            
            for i, page in enumerate(pages):
                page_ids.append(str(i))
                documents.append(page["content"])
                metadatas.append({"id": page["id"], "title": page["title"]})
            
            embeddings = model.encode(documents).tolist()
            collection.add(
                ids=page_ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings
            )
        
        # 搜索相关页面
        model = SentenceTransformer('all-MiniLM-L6-v2')
        query_embedding = model.encode([query]).tolist()
        
        results = collection.query(
            query_embeddings=query_embedding,
            n_results=limit
        )
        
        # 构建结果
        relevant_pages = []
        for i, metadatas in enumerate(results['metadatas'][0]):
            page_id = metadatas['id']
            for page in pages:
                if page['id'] == page_id:
                    relevant_pages.append(page)
                    break
        
        return relevant_pages
    except Exception as e:
        print(f"Vector search error: {e}")
        # 回退到关键词搜索
        return keyword_search(query, limit)


def keyword_search(query: str, limit: int = 3) -> List[Dict[str, Any]]:
    """Keyword-based search as fallback"""
    try:
        import jieba
        
        pages = get_wiki_pages()
        query_terms = list(jieba.cut(query))
        
        results = []
        for page in pages:
            score = 0
            title_lower = page["title"].lower()
            content_lower = page["content"].lower()
            
            for term in query_terms:
                if len(term) < 2:
                    continue
                if term.lower() in title_lower:
                    score += 3
                if term.lower() in content_lower:
                    score += 1
            
            if score > 0:
                results.append((score, page))
        
        # Sort and return top results
        results.sort(key=lambda x: x[0], reverse=True)
        return [page for _, page in results[:limit]]
    except Exception as e:
        print(f"Jieba search error: {e}")
        # Ultimate fallback: simple substring match
        pages = get_wiki_pages()
        results = []
        query_lower = query.lower()
        
        for page in pages:
            score = 0
            if query_lower in page["title"].lower():
                score += 3
            if query_lower in page["content"].lower():
                score += 1
            
            if score > 0:
                results.append((score, page))
        
        results.sort(key=lambda x: x[0], reverse=True)
        return [page for _, page in results[:limit]]

def call_llm_api(prompt: str, provider: str, api_key: str, level: str = "medium") -> str:
    """Call LLM API (bailing, openai, or zhipu)"""
    import requests

    # 根据level获取配置
    llm_config = config["llm"][level]
    model = llm_config["model"]
    temperature = llm_config["temperature"]
    max_tokens = llm_config["max_tokens"]

    if provider == "bailing":
        api_url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key or config['llm']['api_key']}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
    elif provider == "openai":
        api_url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key or config['llm']['api_key']}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
    elif provider == "zhipu":
        api_url = "https://open.bigmodel.cn/api/mt/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key or config['llm']['api_key']}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
    else:
        raise ValueError(f"Unsupported provider: {provider}")

    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        raise Exception(f"Error calling LLM API: {str(e)}")


# API endpoints


@app.get("/api/system/status")
def get_system_status():
    """Get system status"""
    return {"status": "ok", "version": "1.0.0", "wiki_pages": len(get_wiki_pages())}


@app.get("/api/system/config")
def get_system_config():
    """Get system configuration"""
    return config


@app.post("/api/system/ingest")
async def ingest_document(file: UploadFile = File(...)):
    """Ingest a document and generate wiki pages"""
    # Save uploaded file
    file_path = os.path.join(RAW_SOURCES_DIR, file.filename)
    os.makedirs(RAW_SOURCES_DIR, exist_ok=True)

    try:
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # Run ingest script directly to process the specific file
        import subprocess
        ingest_script = os.path.join(BASE_DIR, "scripts", "ingest.py")
        
        # Set UTF-8 encoding for subprocess on Windows
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        
        result = subprocess.run(
            [sys.executable, ingest_script, file_path],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            env=env
        )

        # Check if ingest succeeded
        if result.returncode != 0:
            error_msg = result.stderr if result.stderr else "Unknown error during ingestion"
            raise Exception(f"Ingest failed: {error_msg}")

        # Clear wiki pages cache to ensure new pages are loaded
        global wiki_pages_cache, cache_timestamp
        wiki_pages_cache = None
        cache_timestamp = 0

        # Get newly created pages
        new_pages = []
        for line in result.stdout.split('\n'):
            if 'Created/updated' in line and 'page:' in line:
                page_path = line.split('page:')[-1].strip()
                new_pages.append(page_path)

        return {
            "message": "Document ingested successfully",
            "file": file.filename,
            "pages_created": new_pages,
            "ingest_output": result.stdout
        }
    except ValueError as ve:
        # Unsupported file format or other validation errors
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"Error ingesting document: {str(e)}"
        )


@app.post("/api/system/lint")
def run_lint():
    """Run lint checks"""
    try:
        orphans = find_orphan_pages(WIKI_DIR)
        broken_links = find_broken_links(WIKI_DIR)
        contradictions = find_logical_contradictions(WIKI_DIR)
        unestablished_terms = find_frequent_unestablished_terms(WIKI_DIR)

        return {
            "orphan_pages": orphans,
            "broken_links": broken_links,
            "contradictions": contradictions,
            "unestablished_terms": unestablished_terms,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error running lint: {str(e)}")


@app.get("/api/system/raw-sources")
def get_raw_sources():
    """Get all raw source files"""
    try:
        sources = []
        if os.path.exists(RAW_SOURCES_DIR):
            for filename in os.listdir(RAW_SOURCES_DIR):
                file_path = os.path.join(RAW_SOURCES_DIR, filename)
                if os.path.isfile(file_path):
                    # 获取文件扩展名作为类型
                    ext = os.path.splitext(filename)[1].lower().lstrip('.')
                    file_type = ext if ext else 'txt'
                    
                    # 读取文件内容（限制大小）
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read(10000)  # 只读取前10000字符
                    except:
                        content = "[Binary file or encoding error]"
                    
                    sources.append({
                        "id": filename,
                        "name": filename,
                        "title": filename,
                        "type": file_type,
                        "content": content,
                        "lastModified": os.path.getmtime(file_path),
                        "dateAdded": os.path.getctime(file_path)
                    })
        return sources
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading raw sources: {str(e)}")


@app.get("/api/system/raw-sources/{source_id:path}/preview-delete")
def preview_delete_raw_source(source_id: str):
    """Preview the impact of deleting a raw source file"""
    try:
        # 查找关联的 Wiki 页面
        linked_pages = find_pages_by_source(source_id)
        
        return {
            "linked_count": len(linked_pages),
            "linked_wiki_pages": linked_pages
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error previewing delete: {str(e)}")


@app.delete("/api/system/raw-sources/{source_id:path}")
def delete_raw_source(source_id: str):
    """Delete a raw source file and mark related wiki pages as orphan"""
    try:
        file_path = os.path.join(RAW_SOURCES_DIR, source_id)
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Source file not found")
        
        # 标记关联的 Wiki 页面为孤立页面
        marked_pages = mark_pages_as_orphan(source_id)
        
        # 删除源文件
        os.remove(file_path)
        
        return {
            "message": "Source file deleted successfully",
            "deleted_file": source_id,
            "marked_orphan_pages": marked_pages
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting source: {str(e)}")


@app.get("/api/pages")
def get_pages():
    """Get all wiki pages"""
    pages = get_wiki_pages()
    # Convert paths to use forward slashes
    for page in pages:
        page["path"] = page["path"].replace(os.path.sep, "/")
    return pages


@app.get("/api/wiki/pages")
def get_wiki_pages_api():
    """Get all wiki pages (alias for /api/pages)"""
    return get_pages()


@app.get("/api/pages/{page_id:path}")
def get_page(page_id: str):
    """Get a specific wiki page"""
    return get_page_by_id(page_id)


@app.get("/api/wiki/pages/{page_id:path}")
def get_wiki_page(page_id: str):
    """Get a specific wiki page (alias for /api/pages/{page_id})"""
    return get_page_by_id(page_id)


@app.put("/api/pages/{page_id:path}")
def update_page(page_id: str, page_data: Dict[str, Any]):
    """Update a wiki page"""
    return save_page(page_id, page_data)


@app.delete("/api/pages/{page_id:path}")
def delete_wiki_page(page_id: str, auto_clean_links: bool = True):
    """Delete a wiki page"""
    return delete_page(page_id, auto_clean_links)


@app.post("/api/chat")
def chat(request: QueryRequest):
    """Chat with the LLM about wiki content"""
    try:
        # Get relevant wiki pages
        relevant_pages = get_relevant_wiki_pages(request.query)
        
        # Build context
        context = ""
        for page in relevant_pages:
            context += f"# {page['title']}\n\n"
            # Remove frontmatter if present
            content = page['content']
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    content = parts[2]
            context += content[:1000] + "\n\n"  # Limit each page to 1000 chars
        
        # Generate prompt
        prompt = f"""You are a helpful assistant that answers questions based on the provided context.

Context:
{context[:4000]}  # Limit total context to 4000 chars

Question:
{request.query}

Please provide a comprehensive and accurate answer based on the context. If the context doesn't contain enough information to answer the question, please state that clearly."""
        
        # Call LLM API
        response = call_llm_api(
            prompt, 
            request.provider, 
            request.api_key, 
            "medium"
        )
        
        # Return response
        return {
            "response": response,
            "relevant_pages": [
                {"id": page["id"], "title": page["title"]} 
                for page in relevant_pages
            ],
            "can_save_as_page": True,
            "save_prompt": "这段回答是否值得保存为 Wiki 页面？如需保存，请调用 /api/save-page 接口。"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing chat: {str(e)}")


@app.post("/api/save-page")
def save_chat_page(request: SavePageRequest):
    """Save chat response as a wiki page"""
    try:
        # Create a safe page ID
        import re
        page_id = "summaries/" + re.sub(r'[^a-zA-Z0-9\\s]', '-', request.title.lower())
        page_id = re.sub(r'-+', '-', page_id).strip('-')
        
        # Create page content with frontmatter
        content = f"""---
source: generated
created_at: {time.strftime('%Y-%m-%d %H:%M:%S')}
---

# {request.title}

{request.content}
"""
        
        # Save the page
        saved_page = save_page(page_id, {"content": content})
        
        return {
            "success": True,
            "page_path": saved_page["path"],
            "message": f"Page saved successfully: {saved_page['title']}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving page: {str(e)}")


@app.get("/api/search")
def search(q: str, limit: int = 10):
    """Search wiki pages"""
    try:
        # Get relevant pages
        relevant_pages = get_relevant_wiki_pages(q, limit)
        
        # Format results
        results = []
        for page in relevant_pages:
            # Create snippet
            content = page['content']
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    content = parts[2]
            
            # Find query in content
            query_lower = q.lower()
            content_lower = content.lower()
            start_idx = content_lower.find(query_lower)
            
            if start_idx >= 0:
                # Extract snippet around the match
                start = max(0, start_idx - 50)
                end = min(len(content), start_idx + len(q) + 50)
                snippet = content[start:end]
                # Highlight the match
                snippet = snippet.replace(q, f"<mark>{q}</mark>")
            else:
                # Use beginning of content if no match
                snippet = content[:100]
            
            results.append({
                "id": page["id"],
                "title": page["title"],
                "snippet": snippet
            })
        
        return {"results": results, "count": len(results)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )