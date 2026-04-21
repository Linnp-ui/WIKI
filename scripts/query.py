#!/usr/bin/env python3
"""
Query script for LLM Wiki.
Searches Wiki pages and generates answers based on context.
"""

import sys
import os
import yaml
import re
import json
from typing import Dict, List, Tuple

# Try to import necessary libraries
try:
    import openai
    OPENAI_SUPPORTED = True
except ImportError:
    OPENAI_SUPPORTED = False

try:
    from sentence_transformers import SentenceTransformer
    import chromadb
    CHROMADB_SUPPORTED = True
except ImportError:
    CHROMADB_SUPPORTED = False

# Load configuration
def load_config() -> Dict:
    """
    加载配置文件
    
    返回:
        Dict: 配置信息字典
    """
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

# Read Wiki page content
def read_wiki_page(page_path: str) -> str:
    """
    读取Wiki页面内容
    
    参数:
        page_path: Wiki页面文件路径
    
    返回:
        str: 页面内容
    """
    with open(page_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()

# Extract frontmatter from Wiki page
def extract_frontmatter(content: str) -> Dict:
    """
    从Wiki页面内容中提取前置信息
    
    参数:
        content: 页面内容
    
    返回:
        Dict: 前置信息字典
    """
    frontmatter_match = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
    if frontmatter_match:
        frontmatter_str = frontmatter_match.group(1)
        frontmatter = {}
        for line in frontmatter_str.strip().split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                frontmatter[key.strip()] = value.strip()
        return frontmatter
    return {}

# Extract content without frontmatter
def extract_content(content: str) -> str:
    """
    提取不包含前置信息的页面内容
    
    参数:
        content: 完整页面内容
    
    返回:
        str: 去除前置信息后的内容
    """
    frontmatter_match = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
    if frontmatter_match:
        return content[frontmatter_match.end():]
    return content

# 读取索引文件
def read_index_file(wiki_dir: str) -> str:
    """
    读取index.md文件内容
    
    参数:
        wiki_dir: Wiki目录路径
    
    返回:
        str: 索引文件内容
    """
    index_path = os.path.join(wiki_dir, "index.md")
    if os.path.exists(index_path):
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            print(f"Error reading index file: {e}")
    return ""

# 从索引中提取分类信息
def extract_index_categories(index_content: str) -> Dict[str, List[str]]:
    """
    从索引内容中提取分类信息
    
    参数:
        index_content: 索引文件内容
    
    返回:
        Dict[str, List[str]]: 分类到页面的映射
    """
    categories = {"concepts": [], "entities": [], "summaries": []}
    
    # 提取概念列表
    concept_match = re.search(r"### Concepts.*?(?=###|##|$)", index_content, re.DOTALL)
    if concept_match:
        concept_section = concept_match.group(0)
        links = re.findall(r"\[\[([^\]]+)\]\]", concept_section)
        categories["concepts"] = links
    
    # 提取实体列表
    entity_match = re.search(r"### Entities.*?(?=###|##|$)", index_content, re.DOTALL)
    if entity_match:
        entity_section = entity_match.group(0)
        links = re.findall(r"\[\[([^\]]+)\]\]", entity_section)
        categories["entities"] = links
    
    # 提取摘要列表
    summary_match = re.search(r"### Summaries.*?(?=###|##|$)", index_content, re.DOTALL)
    if summary_match:
        summary_section = summary_match.group(0)
        links = re.findall(r"\[\[([^\]]+)\]\]", summary_section)
        categories["summaries"] = links
    
    return categories

# Search Wiki pages by keyword
def search_by_keyword(query: str, wiki_dir: str) -> List[Tuple[str, str, float]]:
    """
    通过关键词搜索Wiki页面
    
    参数:
        query: 查询关键词
        wiki_dir: Wiki目录路径
    
    返回:
        List[Tuple[str, str, float]]: 搜索结果列表，每个元素包含(标题, 文件路径, 相关度分数)
    """
    results = []
    query_lower = query.lower()
    
    # 递归搜索wiki目录中的所有markdown文件
    for root, dirs, files in os.walk(wiki_dir):
        for file in files:
            if file.endswith(".md"):
                file_path = os.path.join(root, file)
                try:
                    content = read_wiki_page(file_path)
                    content_lower = content.lower()
                    
                    # 计算相关度分数（简单关键词匹配）
                    score = 0
                    for word in query_lower.split():
                        score += content_lower.count(word)
                    
                    if score > 0:
                        # 提取页面标题
                        title_match = re.search(r"^# (.*?)$", content, re.MULTILINE)
                        title = title_match.group(1) if title_match else os.path.splitext(file)[0]
                        
                        results.append((title, file_path, score))
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
    
    # 按相关度分数排序
    results.sort(key=lambda x: x[2], reverse=True)
    return results

# Initialize vector store
def initialize_vector_store(wiki_dir: str) -> Tuple[List[str], List[str], any]:
    """
    初始化向量存储
    
    参数:
        wiki_dir: Wiki目录路径
    
    返回:
        Tuple[List[str], List[str], any]: (页面内容列表, 页面路径列表, ChromaDB集合)
    """
    if not CHROMADB_SUPPORTED:
        raise ImportError("sentence-transformers and chromadb are not installed. Please install them with 'pip install sentence-transformers chromadb'")
    
    # 加载模型
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    # 收集所有Wiki页面
    pages = []
    page_paths = []
    page_ids = []
    
    for root, dirs, files in os.walk(wiki_dir):
        for file in files:
            if file.endswith(".md"):
                file_path = os.path.join(root, file)
                try:
                    content = read_wiki_page(file_path)
                    # 提取不包含前置信息的内容
                    page_content = extract_content(content)
                    pages.append(page_content)
                    page_paths.append(file_path)
                    page_ids.append(str(len(page_ids)))
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
    
    # 初始化ChromaDB
    chroma_client = chromadb.PersistentClient(path=".vector_store")
    collection = chroma_client.get_or_create_collection(name="wiki_pages")
    
    # 生成嵌入向量并添加到ChromaDB
    if pages:
        embeddings = model.encode(pages).tolist()
        collection.upsert(
            documents=pages,
            metadatas=[{"path": path} for path in page_paths],
            ids=page_ids
        )
    
    return pages, page_paths, collection

# Search Wiki pages by vector similarity
def search_by_vector(query: str, wiki_dir: str) -> List[Tuple[str, str, float]]:
    """
    通过向量相似度搜索Wiki页面
    
    参数:
        query: 查询文本
        wiki_dir: Wiki目录路径
    
    返回:
        List[Tuple[str, str, float]]: 搜索结果列表，每个元素包含(标题, 文件路径, 相关度分数)
    """
    if not CHROMADB_SUPPORTED:
        # 如果不支持向量搜索，回退到关键词搜索
        return search_by_keyword(query, wiki_dir)
    
    # 初始化向量存储
    pages, page_paths, collection = initialize_vector_store(wiki_dir)
    
    # 加载模型
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    # 编码查询
    query_embedding = model.encode([query]).tolist()
    
    # 搜索
    k = 5  # 返回结果数量
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=k,
        include=['metadatas', 'distances']
    )
    
    # 格式化结果
    formatted_results = []
    for i, (metadata, distance) in enumerate(zip(results['metadatas'][0], results['distances'][0])):
        file_path = metadata['path']
        # 提取页面标题
        content = read_wiki_page(file_path)
        title_match = re.search(r"^# (.*?)$", content, re.MULTILINE)
        title = title_match.group(1) if title_match else os.path.splitext(os.path.basename(file_path))[0]
        
        # 计算相似度分数（距离的倒数）
        score = 1.0 / (1.0 + distance)
        formatted_results.append((title, file_path, score))
    
    return formatted_results

# Assemble context from search results
def assemble_context(results: List[Tuple[str, str, float]], max_chars: int = 4000) -> str:
    """
    从搜索结果组装上下文
    
    参数:
        results: 搜索结果列表
        max_chars: 最大字符数限制
    
    返回:
        str: 组装后的上下文内容
    """
    context = ""
    for title, file_path, score in results:
        try:
            content = read_wiki_page(file_path)
            # 提取不包含前置信息的内容
            page_content = extract_content(content)
            # 添加到上下文
            context += f"# {title}\n\n{page_content}\n\n"
            # 检查是否达到最大字符限制
            if len(context) > max_chars:
                break
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
    return context

# 组装上下文（包含索引信息）
def assemble_context_with_index(results: List[Tuple[str, str, float]], wiki_dir: str, max_chars: int = 4000) -> str:
    """
    组装上下文，包含索引信息作为指导
    
    参数:
        results: 搜索结果列表
        wiki_dir: Wiki目录路径
        max_chars: 最大字符数限制
    
    返回:
        str: 组装后的上下文内容
    """
    # 读取索引文件
    index_content = read_index_file(wiki_dir)
    index_categories = extract_index_categories(index_content)
    
    # 构建上下文
    context = "# Knowledge Base Index\n\n"
    
    # 添加索引中的分类信息
    if index_categories["concepts"]:
        context += "## Concepts\n"
        context += "\n".join([f"- [[{c}]]" for c in index_categories["concepts"]])
        context += "\n\n"
    
    if index_categories["entities"]:
        context += "## Entities\n"
        context += "\n".join([f"- [[{e}]]" for e in index_categories["entities"]])
        context += "\n\n"
    
    if index_categories["summaries"]:
        context += "## Summaries\n"
        context += "\n".join([f"- [[{s}]]" for s in index_categories["summaries"]])
        context += "\n\n"
    
    context += "# Relevant Pages\n\n"
    
    # 组装搜索结果的上下文
    search_context = assemble_context(results, max_chars - len(context))
    context += search_context
    
    return context

# Generate answer using LLM
def generate_answer(query: str, context: str, config: Dict) -> str:
    """
    使用LLM生成回答
    
    参数:
        query: 查询问题
        context: 上下文内容
        config: 配置信息
    
    返回:
        str: 生成的回答
    """
    # 使用中级别模型
    llm_config = config["llm"]["medium"]
    provider = llm_config.get("provider", "openai")
    
    # 准备提示词
    prompt = f"""
    You are a helpful assistant that answers questions based on the provided context.
    
    Context:
    {context[:4000]}  # Limit context to avoid token issues
    
    Question:
    {query}
    
    Please provide a comprehensive and accurate answer based on the context. If the context doesn't contain enough information to answer the question, please state that.
    """
    
    if provider == "openai":
        if not OPENAI_SUPPORTED:
            raise ImportError("openai is not installed. Please install it with 'pip install openai'")
        
        # 设置OpenAI API
        openai.api_key = os.getenv("OPENAI_API_KEY")
        if not openai.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        
        # 调用OpenAI API
        response = openai.chat.completions.create(
            model=llm_config["model"],
            messages=[
                {"role": "system", "content": "You are a helpful assistant that answers questions based on provided context."},
                {"role": "user", "content": prompt}
            ],
            temperature=llm_config["temperature"],
            max_tokens=llm_config["max_tokens"]
        )
        
        return response.choices[0].message.content
    elif provider == "cloudflare":
        try:
            import requests
        except ImportError:
            raise ImportError("requests is not installed. Please install it with 'pip install requests'")
        
        # 设置Cloudflare Workers AI API
        api_url = os.getenv("CLOUDFLARE_API_URL")
        api_token = os.getenv("CLOUDFLARE_API_TOKEN")
        
        if not api_token:
            raise ValueError("CLOUDFLARE_API_TOKEN environment variable is not set")
        
        # 调用Cloudflare Workers AI API
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        }
        
        # Cloudflare Workers AI uses messages format
        payload = {
            "messages": [
                {"role": "system", "content": "You are a helpful assistant that answers questions based on provided context."},
                {"role": "user", "content": prompt}
            ],
            "temperature": llm_config["temperature"],
            "max_tokens": llm_config["max_tokens"]
        }
        
        model = llm_config["model"]
        response = requests.post(
            f"{api_url}{model}", headers=headers, json=payload
        )
        response.raise_for_status()
        
        # 解析响应
        data = response.json()
        return data.get("result", {}).get("response", "")
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")

# Save answer as new Wiki page
def save_answer_as_page(answer: str, query: str, config: Dict) -> str:
    """
    将回答保存为新的Wiki页面
    
    参数:
        answer: 生成的回答
        query: 查询问题
        config: 配置信息
    
    返回:
        str: 保存的页面路径
    """
    # 从查询生成页面名称
    page_name = query[:50].lower().replace(" ", "-")
    # 移除除连字符外的非字母数字字符
    page_name = re.sub(r"[^a-z0-9-]", "", page_name)
    
    # 创建带前置信息的内容
    content = f"---\nsource: generated\n---\n\n# {query}\n\n{answer}\n"
    
    # 保存到summaries目录
    dir_path = config["wiki"]["summaries_dir"]
    os.makedirs(dir_path, exist_ok=True)
    
    # 生成文件名
    filename = f"{page_name}.md"
    page_path = os.path.join(dir_path, filename)
    
    # 写入内容
    with open(page_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    return page_path

# Main query function
def query_wiki(query: str, config: Dict) -> str:
    """
    查询Wiki并生成回答
    
    参数:
        query: 查询问题
        config: 配置信息
    
    返回:
        str: 生成的回答
    """
    print(f"Querying Wiki for: {query}")
    
    # 搜索Wiki页面
    wiki_dir = config["wiki_dir"]
    results = search_by_vector(query, wiki_dir)
    
    if not results:
        print("No results found.")
        return "No relevant information found in the Wiki."
    
    print(f"Found {len(results)} relevant pages:")
    for title, _, score in results[:3]:  # 显示前3个结果
        print(f"- {title} (score: {score:.2f})")
    
    # 组装上下文，包含索引信息作为指导
    context = assemble_context_with_index(results, wiki_dir)
    print(f"Assembled context of {len(context)} characters")
    
    # 生成回答
    try:
        answer = generate_answer(query, context, config)
        print("Generated answer")
    except Exception as e:
        print(f"Error generating answer: {e}")
        return f"Error generating answer: {e}"
    
    # 将回答保存为新的Wiki页面
    page_path = save_answer_as_page(answer, query, config)
    print(f"Saved answer as Wiki page: {page_path}")
    
    return answer

# Main function
def main():
    """
    主函数
    """
    if len(sys.argv) < 2:
        print("Usage: python query.py \"question\"")
        sys.exit(1)

    query = sys.argv[1]
    
    # 加载配置
    try:
        config = load_config()
    except Exception as e:
        print(f"Error loading config: {e}")
        sys.exit(1)
    
    # 查询Wiki
    answer = query_wiki(query, config)
    print("\nAnswer:")
    print(answer)

if __name__ == "__main__":
    main()
