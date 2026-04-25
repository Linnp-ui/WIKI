#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ingestion script for LLM Wiki.
Reads raw source files and compiles them into Wiki pages.

知识摄入脚本核心流程：
1. 读取原始文件（PDF/DOCX/TXT/MD）
2. 使用LLM提取关键概念、实体和结论
3. 构建页面关联图谱
4. 创建或更新Wiki页面
5. 自动建立页面间的双向链接
"""

import sys
import os
import yaml
import re
import time
from typing import Dict, List, Tuple
import concurrent.futures

# Set default encoding to UTF-8
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Try to load .env from current directory and parent directories
    env_path = None
    for dir_path in ['.', '..', '../..']:
        test_path = os.path.join(dir_path, '.env')
        if os.path.exists(test_path):
            env_path = test_path
            break
    if env_path:
        load_dotenv(env_path)
        print(f"Loaded environment variables from {env_path}")
except ImportError:
    pass

# Try to import MarkItDown
try:
    from markitdown import MarkItDown
    MARKITDOWN_SUPPORTED = True
    md_converter = MarkItDown()
except ImportError:
    MARKITDOWN_SUPPORTED = False
    print("Error: MarkItDown is not installed. Please install it with 'pip install markitdown'")
    sys.exit(1)

# Try to import requests
try:
    import requests
    REQUESTS_SUPPORTED = True
except ImportError:
    REQUESTS_SUPPORTED = False

# 加载配置文件
def load_config() -> Dict:
    """
    加载配置文件config.yaml
    
    返回:
        Dict: 配置信息字典，包含LLM设置、Wiki目录路径等
    """
    config_path = os.path.join(
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..")), "config.yaml"
    )
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# 根据文件格式读取内容
def read_file_content(file_path: str) -> str:
    """
    使用MarkItDown读取不同格式的文件内容
    
    参数:
        file_path: 文件路径
    
    返回:
        str: 转换后的Markdown内容
    
    支持的格式:
        - PDF: .pdf
        - Word: .docx, .doc
        - PowerPoint: .pptx, .ppt
        - Excel: .xlsx, .xls
        - Text: .txt, .md, .csv, .json, .xml
        - HTML: .html, .htm
        - 其他: 支持的格式取决于MarkItDown
    """
    if not os.path.exists(file_path):
        raise ValueError(f"File not found: {file_path}")
    
    try:
        print(f"Using MarkItDown to process {file_path}")
        # 使用MarkItDown转换文件
        result = md_converter.convert(file_path)
        
        # 检查返回类型并提取Markdown内容
        if hasattr(result, 'markdown'):
            # 新版本MarkItDown返回DocumentConverterResult对象
            markdown_content = result.markdown
        else:
            # 旧版本可能直接返回字符串
            markdown_content = result
        
        if not isinstance(markdown_content, str):
            raise ValueError(f"MarkItDown returned non-string type: {type(markdown_content)}")
        
        return markdown_content
    except Exception as e:
        raise ValueError(f"Error processing file {file_path}: {str(e)}")


# 缓存LLM响应
import json
import hashlib

llm_cache = {}
CACHE_FILE = ".llm_cache.json"

# Load cache from file
try:
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            llm_cache = json.load(f)
        print(f"Loaded {len(llm_cache)} cached LLM responses")
except Exception as e:
    print(f"Error loading cache: {e}")

# Save cache to file
def save_cache():
    """Save cache to file"""
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(llm_cache, f, ensure_ascii=False, indent=2)
        print(f"Saved {len(llm_cache)} cached LLM responses")
    except Exception as e:
        print(f"Error saving cache: {e}")


def deduplicate_results(results: Dict) -> Dict:
    """
    去重提取的结果
    
    参数:
        results: 包含concepts、entities、conclusions的字典
    
    返回:
        Dict: 去重后的结果
    """
    # Deduplicate concepts
    seen_concepts = set()
    unique_concepts = []
    for concept in results["concepts"]:
        if isinstance(concept, dict) and "name" in concept:
            name = concept["name"].lower().strip()
            if name not in seen_concepts:
                seen_concepts.add(name)
                unique_concepts.append(concept)
    
    # Deduplicate entities
    seen_entities = set()
    unique_entities = []
    for entity in results["entities"]:
        if isinstance(entity, dict) and "name" in entity:
            name = entity["name"].lower().strip()
            if name not in seen_entities:
                seen_entities.add(name)
                unique_entities.append(entity)
        elif isinstance(entity, str):
            name = entity.lower().strip()
            if name not in seen_entities:
                seen_entities.add(name)
                unique_entities.append(entity)
    
    # Deduplicate conclusions
    seen_conclusions = set()
    unique_conclusions = []
    for conclusion in results["conclusions"]:
        if isinstance(conclusion, dict) and "text" in conclusion:
            text = conclusion["text"].lower().strip()
            if text not in seen_conclusions:
                seen_conclusions.add(text)
                unique_conclusions.append(conclusion)
        elif isinstance(conclusion, str):
            text = conclusion.lower().strip()
            if text not in seen_conclusions:
                seen_conclusions.add(text)
                unique_conclusions.append(conclusion)
    
    return {
        "concepts": unique_concepts,
        "entities": unique_entities,
        "conclusions": unique_conclusions
    }


def process_chunk(chunk: str, provider: str, llm_config: Dict) -> Dict:
    """
    处理单个文件块，提取信息
    
    参数:
        chunk: 文件块内容
        provider: LLM提供商
        llm_config: LLM配置信息
    
    返回:
        Dict: 提取的信息
    """
    if provider == "openai":
        if not OPENAI_SUPPORTED:
            raise ImportError(
                "openai is not installed. Please install it with 'pip install openai'"
            )

        # Set up OpenAI API
        openai.api_key = os.getenv("OPENAI_API_KEY")
        if not openai.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")

        # Prepare prompt
        prompt = f"""
        请分析以下内容并提取：
        1. 关键概念：重要的抽象思想或原理，提供详细的定义和解释
        2. 实体信息：具体的人物、组织、模型、技术或地点，提供描述和相关性
        3. 主要结论：文档中的关键要点和重要见解
        
        内容：
        {chunk}
        
        请按照以下格式输出：
        概念：
        - 概念名称：概念的详细定义和解释
        - 另一个概念：另一个详细的定义和解释
        
        实体：
        - 实体名称：详细描述及其与内容的相关性
        - 另一个实体：另一个详细描述及其与内容的相关性
        
        结论：
        - 关键结论1：结论的详细解释
        - 关键结论2：另一个结论的详细解释
        """

        # Call OpenAI API
        response = openai.chat.completions.create(
            model=llm_config["model"],
            messages=[
                {
                    "role": "system",
                    "content": "您是一位专业的文档分析助手，擅长从文档中提取结构化信息。请使用中文回答所有问题。",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=llm_config["temperature"],
            max_tokens=llm_config["max_tokens"],
        )

        # Parse response
        result = parse_llm_response(response.choices[0].message.content)

    elif provider == "bailing":
        if not REQUESTS_SUPPORTED:
            raise ImportError(
                "requests is not installed. Please install it with 'pip install requests'"
            )

        # Set up Bailing API
        api_base = llm_config.get(
            "api_base", "https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        api_key = os.getenv("BAILING_API_KEY")
        if not api_key:
            raise ValueError("BAILING_API_KEY environment variable is not set")

        # Prepare prompt for Bailing
        prompt = f"""
        请分析以下内容并提取：
        1. 关键概念：重要的抽象思想或原理，提供详细的定义和解释
        2. 实体信息：具体的人物、组织、模型、技术或地点，提供描述和相关性
        3. 主要结论：文档中的关键要点和重要见解
        
        内容：
        {chunk}
        
        请按照以下格式输出：
        概念：
        - 概念名称：概念的详细定义和解释
        - 另一个概念：另一个详细的定义和解释
        
        实体：
        - 实体名称：详细描述及其与内容的相关性
        - 另一个实体：另一个详细描述及其与内容的相关性
        
        结论：
        - 关键结论1：结论的详细解释
        - 关键结论2：另一个结论的详细解释
        """

        # Call Bailing API
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        # Bailing API expects different format
        messages = [
            {
                "role": "system",
                "content": "您是一位专业的文档分析助手，擅长从文档中提取结构化信息。请使用中文回答所有问题。",
            },
            {"role": "user", "content": prompt},
        ]

        payload = {
            "model": llm_config["model"],
            "messages": messages,
            "temperature": llm_config["temperature"],
            "max_tokens": llm_config["max_tokens"],
        }

        response = requests.post(
            f"{api_base}/chat/completions", headers=headers, json=payload
        )
        response.raise_for_status()

        # Parse response
        result = parse_llm_response(response.json()["choices"][0]["message"]["content"])
    elif provider == "cloudflare":
        if not REQUESTS_SUPPORTED:
            raise ImportError(
                "requests is not installed. Please install it with 'pip install requests'"
            )

        # Set up Cloudflare Workers AI API
        api_url = os.getenv("CLOUDFLARE_API_URL")
        api_token = os.getenv("CLOUDFLARE_API_TOKEN")
        
        if not api_token:
            raise ValueError("CLOUDFLARE_API_TOKEN environment variable is not set")

        # Prepare prompt for Cloudflare
        prompt = f"""
        您是一位专业的信息提取专家。请仔细分析以下内容并提取：
        
        1. 关键概念：重要的抽象思想、原理或框架，提供详细的定义和全面的解释。重点关注对理解内容至关重要的核心概念。
        
        2. 实体信息：内容中提到的具体人物、组织、模型、技术、工具或地点。对于每个实体，请提供详细的描述并解释其与整体主题的相关性。
        
        3. 主要结论：文档中的关键要点、重要见解和可操作的建议。这些应该是读者应该记住的最重要的观点。
        
        内容：
        {chunk}
        
        重要要求：请严格按照以下格式输出您的响应，使用指定的部分标题和项目符号。不要在格式之外包含任何额外的文本或解释：
        
        概念：
        - 概念名称：概念的详细定义和解释
        - 另一个概念：另一个详细的定义和解释
        
        实体：
        - 实体名称：详细描述及其与内容的相关性
        - 另一个实体：另一个详细描述及其与内容的相关性
        
        结论：
        - 关键结论1：结论的详细解释
        - 关键结论2：另一个结论的详细解释
        
        请确保提取尽可能多的相关信息，并提供详细的解释，而不仅仅是简要提及。您的分析应该全面而有洞察力。
        """

        # Call Cloudflare Workers AI API
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        }

        # Cloudflare Workers AI uses messages format
        payload = {
            "messages": [
                {
                    "role": "system",
                    "content": "您是一位专业的文档分析助手，擅长从文档中提取结构化信息。请使用中文回答所有问题。",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": llm_config["temperature"],
            "max_tokens": llm_config["max_tokens"]
        }

        model = llm_config["model"]
        response = requests.post(
            f"{api_url}{model}", headers=headers, json=payload
        )
        response.raise_for_status()

        # Parse response
        data = response.json()
        # Extract response content from Cloudflare Workers AI format
        response_content = ""
        if "result" in data:
            result_data = data["result"]
            # Check for choices format (common in OpenAI-compatible APIs)
            if "choices" in result_data and len(result_data["choices"]) > 0:
                for choice in result_data["choices"]:
                    if "message" in choice and choice["message"].get("role") == "assistant":
                        response_content = choice["message"].get("content", "")
                        break
            # Check for messages format
            elif "messages" in result_data and len(result_data["messages"]) > 0:
                for message in result_data["messages"]:
                    if message.get("role") == "assistant" and "content" in message:
                        response_content = message["content"]
                        break
            # Check for direct response format
            elif "response" in result_data:
                response_content = result_data["response"]
        result = parse_llm_response(response_content)
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")
    
    return result


# 使用LLM提取信息
def extract_information(content: str, config: Dict) -> Dict:
    """
    使用LLM从文档内容中提取关键概念、实体和结论
    
    参数:
        content: 文档内容
        config: 配置信息
    
    返回:
        Dict: 提取的信息字典，包含:
            - concepts: 概念列表，每项包含name和definition
            - entities: 实体列表，每项包含name和description
            - conclusions: 结论列表
    
    工作流程:
        1. 生成内容哈希作为缓存键
        2. 检查缓存是否已有结果
        3. 对长文件进行分块处理
        4. 并行对每个块调用相应API
        5. 合并结果并去重
        6. 解析LLM响应并返回结构化数据
    """
    # Generate cache key based on content hash and config
    content_hash = hashlib.md5(content.encode("utf-8")).hexdigest()
    llm_config = config["llm"]["high"]
    cache_key = f"{content_hash}_{llm_config['provider']}_{llm_config['model']}"

    # Check if result is in cache
    if cache_key in llm_cache:
        print("Using cached LLM response")
        return llm_cache[cache_key]

    provider = llm_config.get("provider", "openai")
    chunk_size = 4000
    chunks = []
    
    # Split content into chunks
    if len(content) > chunk_size:
        print(f"Content is long ({len(content)} characters), splitting into chunks...")
        for i in range(0, len(content), chunk_size):
            chunks.append(content[i:i+chunk_size])
        print(f"Split into {len(chunks)} chunks")
    else:
        chunks = [content]
    
    # Process chunks in parallel
    all_results = {"concepts": [], "entities": [], "conclusions": []}
    
    if len(chunks) == 1:
        # Single chunk, process sequentially
        print("Processing single chunk...")
        result = process_chunk(chunks[0], provider, llm_config)
        all_results["concepts"].extend(result["concepts"])
        all_results["entities"].extend(result["entities"])
        all_results["conclusions"].extend(result["conclusions"])
    else:
        # Multiple chunks, process in parallel
        print(f"Processing {len(chunks)} chunks in parallel...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(5, len(chunks))) as executor:
            # Submit all chunk processing tasks
            future_to_chunk = {executor.submit(process_chunk, chunk, provider, llm_config): i for i, chunk in enumerate(chunks)}
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_chunk):
                chunk_index = future_to_chunk[future]
                try:
                    result = future.result()
                    print(f"Completed processing chunk {chunk_index + 1}/{len(chunks)}")
                    all_results["concepts"].extend(result["concepts"])
                    all_results["entities"].extend(result["entities"])
                    all_results["conclusions"].extend(result["conclusions"])
                except Exception as e:
                    print(f"Error processing chunk {chunk_index + 1}: {e}")
    
    # Deduplicate results
    print("Deduplicating results...")
    all_results = deduplicate_results(all_results)
    
    print(f"Final results: {len(all_results['concepts'])} concepts, {len(all_results['entities'])} entities, {len(all_results['conclusions'])} conclusions")
    
    # Cache the result
    llm_cache[cache_key] = all_results
    print("Cached LLM response")
    save_cache()

    return all_results


def parse_llm_response(response: str) -> Dict:
    """
    解析LLM响应为结构化格式
    
    参数:
        response: LLM返回的原始文本
    
    返回:
        Dict: 结构化数据，包含concepts、entities、conclusions三个部分
    
    解析规则:
        - CONCEPTS: 提取"概念名: 定义"格式的行
        - ENTITIES: 提取"实体名: 描述"格式的行
        - CONCLUSIONS: 提取"结论: 解释"格式的行
    """
    sections = {"concepts": [], "entities": [], "conclusions": []}

    # 简化解析逻辑，处理更多格式变化
    lines = response.strip().split("\n")
    current_section = None
    
    for line in lines:
        line = line.strip()
        
        # 检测section标题
        if line.upper() == "CONCEPTS:" or line == "概念：":
            current_section = "concepts"
        elif line.upper() == "ENTITIES:" or line == "实体：":
            current_section = "entities"
        elif line.upper() == "CONCLUSIONS:" or line == "结论：":
            current_section = "conclusions"
        # 处理列表项
        elif line.startswith("-") and current_section:
            # 移除前缀"- "
            content = line[2:].strip()
            if ":" in content:
                # 分割名称和描述
                parts = content.split(":", 1)
                if len(parts) == 2:
                    name = parts[0].strip()
                    description = parts[1].strip()
                    
                    if current_section == "concepts":
                        # 移除序号前缀（如 "1. "、"2. " 等）
                        clean_name = re.sub(r'^\d+\.\s*', '', name)
                        sections[current_section].append({"name": clean_name, "definition": description})
                    elif current_section == "entities":
                        # 移除序号前缀
                        clean_name = re.sub(r'^\d+\.\s*', '', name)
                        sections[current_section].append({"name": clean_name, "description": description})
                    elif current_section == "conclusions":
                        # 移除序号前缀
                        clean_text = re.sub(r'^\d+\.\s*', '', name)
                        sections[current_section].append({"text": clean_text, "explanation": description})
            else:
                # 如果没有冒号，将整个内容作为项
                if current_section == "concepts":
                    # 移除序号前缀
                    clean_content = re.sub(r'^\d+\.\s*', '', content)
                    sections[current_section].append({"name": clean_content, "definition": ""})
                elif current_section == "entities":
                    # 移除序号前缀
                    clean_content = re.sub(r'^\d+\.\s*', '', content)
                    sections[current_section].append({"name": clean_content, "description": ""})
                elif current_section == "conclusions":
                    # 移除序号前缀
                    clean_content = re.sub(r'^\d+\.\s*', '', content)
                    sections[current_section].append({"text": clean_content, "explanation": ""})

    return sections


# 检查Wiki页面是否存在
def page_exists(page_name: str, wiki_dir: str) -> bool:
    """
    检查指定名称的Wiki页面是否已存在
    
    参数:
        page_name: 页面名称
        wiki_dir: Wiki根目录
    
    返回:
        bool: 页面是否存在
    """
    page_name_lower = page_name.lower().replace(" ", "-")
    for root, _, files in os.walk(wiki_dir):
        for file in files:
            if file.endswith(".md"):
                relative_path = os.path.relpath(os.path.join(root, file), wiki_dir)
                file_page_name = os.path.splitext(
                    relative_path.replace(os.path.sep, "/")
                )[0]
                if file_page_name == page_name_lower:
                    return True
    return False


def extract_wiki_links(content: str) -> List[str]:
    """
    从内容中提取Wiki链接
    
    Wiki链接格式: [[页面名称]]
    
    参数:
        content: 页面内容
    
    返回:
        List[str]: 页面名称列表
    """
    pattern = r'\[\[([^\]]+)\]\]'
    matches = re.findall(pattern, content)
    return matches


def get_all_wiki_pages(wiki_dir: str) -> Dict[str, Dict]:
    """
    获取所有Wiki页面及其元数据
    
    参数:
        wiki_dir: Wiki根目录
    
    返回:
        Dict[str, Dict]: 页面字典，键为规范化页面名，值为页面数据
            包含: name, type, path, frontmatter, content, raw_content
    
    页面分类:
        - concepts/: 概念页面
        - entities/: 实体页面
        - summaries/: 摘要页面
        - 其他: 未知类型
    """
    pages = {}

    for root, _, files in os.walk(wiki_dir):
        for file in files:
            if not file.endswith(".md"):
                continue

            file_path = os.path.join(root, file)
            relative_path = os.path.relpath(file_path, wiki_dir)

            dir_name = os.path.dirname(relative_path)
            page_name_with_ext = os.path.splitext(relative_path.replace(os.path.sep, "/"))[0]

            if dir_name == "concepts" or "concepts" in dir_name:
                page_type = "concept"
                page_name = page_name_with_ext.replace("concepts/", "").replace("concepts\\", "")
            elif dir_name == "entities" or "entities" in dir_name:
                page_type = "entity"
                page_name = page_name_with_ext.replace("entities/", "").replace("entities\\", "")
            elif dir_name == "summaries" or "summaries" in dir_name:
                page_type = "summary"
                page_name = page_name_with_ext.replace("summaries/", "").replace("summaries\\", "")
            else:
                page_type = "unknown"
                page_name = page_name_with_ext

            page_name_normalized = page_name.lower()

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception:
                continue

            frontmatter = {}
            body_content = content
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    frontmatter_text = parts[1]
                    body_content = parts[2].strip()
                    for line in frontmatter_text.split("\n"):
                        line = line.strip()
                        if line and ":" in line:
                            key, value = line.split(":", 1)
                            frontmatter[key.strip()] = value.strip()

            pages[page_name_normalized] = {
                "name": page_name,
                "type": page_type,
                "path": file_path,
                "frontmatter": frontmatter,
                "content": body_content,
                "raw_content": content
            }

    return pages


def build_association_map(wiki_dir: str) -> Dict[str, Dict]:
    """
    构建Wiki页面之间的关联图谱
    
    这是实现知识图谱的核心函数，建立页面间的双向链接关系：
    - forward_links: 记录每个页面指向哪些其他页面
    - back_links: 记录每个页面被哪些页面指向（反向引用）
    
    参数:
        wiki_dir: Wiki根目录
    
    返回:
        Dict: 包含三个键的字典:
            - pages: 所有页面数据
            - forward_links: 正向链接映射
            - back_links: 反向链接映射
    """
    pages = get_all_wiki_pages(wiki_dir)

    forward_links: Dict[str, List[str]] = {}
    back_links: Dict[str, List[str]] = {}

    for page_name, page_data in pages.items():
        forward_links[page_name] = []

    for page_name, page_data in pages.items():
        content = page_data["raw_content"]
        wiki_links = extract_wiki_links(content)

        for link in wiki_links:
            link_normalized = link.lower()

            if link_normalized in pages:
                if link_normalized not in forward_links[page_name]:
                    forward_links[page_name].append(link_normalized)

                if page_name not in back_links:
                    back_links[page_name] = []
                if link_normalized not in back_links:
                    back_links[link_normalized] = []

                if page_name not in back_links[link_normalized]:
                    back_links[link_normalized].append(page_name)

    return {
        "pages": pages,
        "forward_links": forward_links,
        "back_links": back_links
    }


def read_existing_page(page_path: str) -> str:
    """Read existing page content"""
    if os.path.exists(page_path):
        with open(page_path, "r", encoding="utf-8") as f:
            return f.read()
    return ""


def merge_content(existing_content: str, new_content: str, source_file: str) -> str:
    """
    智能合并新旧内容，保留有价值的信息
    
    参数:
        existing_content: 现有页面内容
        new_content: 新内容
        source_file: 源文件名
    
    返回:
        str: 合并后的内容
    
    合并策略:
        1. 提取并合并frontmatter的source字段
        2. 更新freshness时间戳
        3. 按标题节合并内容，保留所有章节
        4. 现有内容优先，新内容补充
    """
    import re
    
    # Extract frontmatter from existing content
    existing_frontmatter = {}
    existing_body = ""
    
    if existing_content.startswith("---"):
        parts = existing_content.split("---", 2)
        if len(parts) >= 3:
            frontmatter = parts[1]
            for line in frontmatter.split("\n"):
                line = line.strip()
                if line and ":" in line:
                    key, value = line.split(":", 1)
                    existing_frontmatter[key.strip()] = value.strip()
            existing_body = parts[2].strip()
    else:
        existing_body = existing_content.strip()
    
    # Extract frontmatter from new content
    new_frontmatter = {}
    new_body = ""
    
    if new_content.startswith("---"):
        parts = new_content.split("---", 2)
        if len(parts) >= 3:
            frontmatter = parts[1]
            for line in frontmatter.split("\n"):
                line = line.strip()
                if line and ":" in line:
                    key, value = line.split(":", 1)
                    new_frontmatter[key.strip()] = value.strip()
            new_body = parts[2].strip()
    else:
        new_body = new_content.strip()
    
    # Merge sources
    sources = []
    
    # Add existing sources
    if "source" in existing_frontmatter:
        existing_sources = existing_frontmatter["source"]
        if isinstance(existing_sources, str):
            # Handle comma-separated sources
            for source in existing_sources.split(","):
                source = source.strip()
                if source:
                    sources.append(source)
    
    # Add new source
    source_file_basename = os.path.basename(source_file)
    if source_file_basename and source_file_basename not in sources:
        sources.append(source_file_basename)
    
    # Merge frontmatter
    merged_frontmatter = {**existing_frontmatter, **new_frontmatter}
    merged_frontmatter["source"] = ", ".join(sources)
    merged_frontmatter["updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
    
    # Smart merge body content
    # 1. Extract sections from existing and new content
    def extract_sections(content):
        sections = {}
        current_section = ""
        current_content = []
        
        for line in content.split("\n"):
            if line.startswith("# "):
                if current_section:
                    sections[current_section] = "\n".join(current_content).strip()
                current_section = line[2:].strip()
                current_content = []
            elif line.startswith("## "):
                if current_section:
                    sections[current_section] = "\n".join(current_content).strip()
                current_section = line[3:].strip()
                current_content = []
            else:
                current_content.append(line)
        
        if current_section:
            sections[current_section] = "\n".join(current_content).strip()
        
        return sections
    
    existing_sections = extract_sections(existing_body)
    new_sections = extract_sections(new_body)
    
    # 2. Merge sections: keep existing content, add new sections, update existing sections with new information
    merged_sections = {**existing_sections, **new_sections}
    
    # 3. Rebuild body
    merged_body_lines = []
    for section, section_content in merged_sections.items():
        merged_body_lines.append(f"# {section}")
        merged_body_lines.append("")
        merged_body_lines.append(section_content)
        merged_body_lines.append("")
    
    merged_body = "\n".join(merged_body_lines).strip()
    
    # 4. Rebuild frontmatter
    frontmatter_lines = []
    for key, value in merged_frontmatter.items():
        frontmatter_lines.append(f"{key}: {value}")
    
    frontmatter = "\n".join(frontmatter_lines)
    
    # 5. Return merged content
    return f"---\n{frontmatter}\n---\n{merged_body}"


# Create or update Wiki page
def create_or_update_page(
    page_name: str, content: str, page_type: str, config: Dict, source_file: str = "",
    associations: Dict = None
) -> str:
    """Create or update a Wiki page with merge support and associations"""
    if associations is None:
        associations = {}

    if page_type == "concept":
        dir_path = config["wiki"]["concepts_dir"]
    elif page_type == "entity":
        dir_path = config["wiki"]["entities_dir"]
    elif page_type == "summary":
        dir_path = config["wiki"]["summaries_dir"]
    else:
        raise ValueError(f"Invalid page type: {page_type}")

    os.makedirs(dir_path, exist_ok=True)

    import re
    # Create safe filename: only letters, numbers, and hyphens
    safe_page_name = re.sub(r'[^a-zA-Z0-9\-]', '-', page_name.lower().replace(' ', '-'))
    # Remove multiple consecutive hyphens
    safe_page_name = re.sub(r'-+', '-', safe_page_name)
    # Remove leading/trailing hyphens
    safe_page_name = safe_page_name.strip('-')
    
    # Prevent empty filename
    if not safe_page_name:
        safe_page_name = "untitled"
        print(f"Warning: Empty page name after sanitization, using default: {safe_page_name}")
    
    filename = f"{safe_page_name}.md"
    page_path = os.path.join(dir_path, filename)

    if os.path.exists(page_path):
        existing_content = read_existing_page(page_path)
        merged_content = merge_content_with_associations(existing_content, content, source_file or "", associations)
        with open(page_path, "w", encoding="utf-8") as f:
            f.write(merged_content)
    else:
        final_content = add_associations_to_content(content, associations, page_type)
        with open(page_path, "w", encoding="utf-8") as f:
            f.write(final_content)

    return page_path


def merge_content_with_associations(existing_content: str, new_content: str, source_file: str, associations: Dict) -> str:
    """Merge content with association information"""
    existing_frontmatter = {}
    existing_body = ""

    if existing_content.startswith("---"):
        parts = existing_content.split("---", 2)
        if len(parts) >= 3:
            frontmatter = parts[1]
            for line in frontmatter.split("\n"):
                line = line.strip()
                if line and ":" in line:
                    key, value = line.split(":", 1)
                    existing_frontmatter[key.strip()] = value.strip()
            existing_body = parts[2].strip()
    else:
        existing_body = existing_content.strip()

    new_frontmatter = {}
    new_body = ""

    if new_content.startswith("---"):
        parts = new_content.split("---", 2)
        if len(parts) >= 3:
            frontmatter = parts[1]
            for line in frontmatter.split("\n"):
                line = line.strip()
                if line and ":" in line:
                    key, value = line.split(":", 1)
                    new_frontmatter[key.strip()] = value.strip()
            new_body = parts[2].strip()
    else:
        new_body = new_content.strip()

    sources = []
    if "source" in existing_frontmatter:
        existing_sources = existing_frontmatter["source"]
        if isinstance(existing_sources, str):
            for source in existing_sources.split(","):
                source = source.strip()
                if source:
                    sources.append(source)

    source_file_basename = os.path.basename(source_file)
    if source_file_basename and source_file_basename not in sources:
        sources.append(source_file_basename)

    merged_frontmatter = {**existing_frontmatter, **new_frontmatter}
    merged_frontmatter["source"] = ", ".join(sources)
    merged_frontmatter["updated"] = time.strftime("%Y-%m-%d %H:%M:%S")

    for key, value in associations.items():
        if value:
            if key in merged_frontmatter:
                existing_values = merged_frontmatter[key].split(", ")
                if isinstance(value, list):
                    for v in value:
                        v_stripped = v.strip()
                        if v_stripped and v_stripped not in existing_values:
                            existing_values.append(v_stripped)
                else:
                    value_str = str(value).strip()
                    if value_str and value_str not in existing_values:
                        existing_values.append(value_str)
                merged_frontmatter[key] = ", ".join(existing_values)
            else:
                merged_frontmatter[key] = value if isinstance(value, str) else ", ".join(value)

    def extract_sections(content):
        sections = {}
        current_section = ""
        current_content = []

        for line in content.split("\n"):
            if line.startswith("# "):
                if current_section:
                    sections[current_section] = "\n".join(current_content).strip()
                current_section = line[2:].strip()
                current_content = []
            elif line.startswith("## "):
                if current_section:
                    sections[current_section] = "\n".join(current_content).strip()
                current_section = line[3:].strip()
                current_content = []
            else:
                current_content.append(line)

        if current_section:
            sections[current_section] = "\n".join(current_content).strip()

        return sections

    existing_sections = extract_sections(existing_body)
    new_sections = extract_sections(new_body)
    merged_sections = {**existing_sections, **new_sections}

    merged_body_lines = []
    for section, section_content in merged_sections.items():
        merged_body_lines.append(f"# {section}")
        merged_body_lines.append("")
        merged_body_lines.append(section_content)
        merged_body_lines.append("")

    merged_body = "\n".join(merged_body_lines).strip()

    final_content = add_associations_to_content(f"---\n" + "\n".join([f"{k}: {v}" for k, v in merged_frontmatter.items()]) + f"\n---\n{merged_body}", associations, merged_frontmatter.get("type", "unknown"))

    return final_content


def add_associations_to_content(content: str, associations: Dict, page_type: str) -> str:
    """Add association metadata to frontmatter and content"""
    related_concepts = associations.get("related_concepts", [])
    related_entities = associations.get("related_entities", [])
    referenced_by = associations.get("referenced_by", [])

    frontmatter_lines = []
    body_lines = []
    in_frontmatter = False
    frontmatter_done = False

    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            frontmatter_text = parts[1]
            body_lines.append(parts[2])

            for line in frontmatter_text.split("\n"):
                line_stripped = line.strip()
                if not line_stripped:
                    continue
                if ":" in line_stripped:
                    key, _ = line_stripped.split(":", 1)
                    key = key.strip()
                    if key in ("related_concepts", "related_entities", "referenced_by"):
                        continue
                frontmatter_lines.append(line)

            frontmatter_done = True
    else:
        body_lines.append(content)

    if related_concepts:
        if isinstance(related_concepts, str):
            related_concepts = [c.strip() for c in related_concepts.split(",") if c.strip()]
        frontmatter_lines.append(f"related_concepts: {', '.join(related_concepts)}")

    if related_entities:
        if isinstance(related_entities, str):
            related_entities = [e.strip() for e in related_entities.split(",") if e.strip()]
        frontmatter_lines.append(f"related_entities: {', '.join(related_entities)}")

    if referenced_by:
        if isinstance(referenced_by, str):
            referenced_by = [r.strip() for r in referenced_by.split(",") if r.strip()]
        frontmatter_lines.append(f"referenced_by: {', '.join(referenced_by)}")

    frontmatter = "\n".join(frontmatter_lines).rstrip()
    body = "\n".join(body_lines)

    if not body.strip():
        body = "\n\n"

    body_sections = []
    in_related_section = False
    related_section_lines = []
    non_related_lines = []

    for line in body.split("\n"):
        if line.strip() == "## Related Concepts" or line.strip() == "## Related Entities" or line.strip() == "## Referenced By":
            in_related_section = True
            related_section_lines = [line]
            continue

        if in_related_section:
            if line.startswith("## ") and not line.startswith("### "):
                body_sections.append("\n".join(related_section_lines))
                related_section_lines = [line]
            elif line.startswith("### "):
                related_section_lines.append(line)
            else:
                related_section_lines.append(line)
        else:
            non_related_lines.append(line)

    if related_section_lines:
        body_sections.append("\n".join(related_section_lines))

    final_body_lines = []
    if non_related_lines:
        final_body_lines.extend(non_related_lines)
        final_body_lines.append("")

    if page_type == "concept":
        if related_entities:
            final_body_lines.append("## Related Entities")
            final_body_lines.append("")
            for entity in related_entities:
                entity_name = entity.strip().replace("**", "")
                if entity_name:
                    final_body_lines.append(f"- [[{entity_name}]]")
            final_body_lines.append("")

        if referenced_by:
            final_body_lines.append("## Referenced By")
            final_body_lines.append("")
            for ref in referenced_by:
                ref_name = ref.strip().replace("**", "")
                if ref_name:
                    final_body_lines.append(f"- [[{ref_name}]]")
            final_body_lines.append("")

    elif page_type == "entity":
        if related_concepts:
            final_body_lines.append("## Related Concepts")
            final_body_lines.append("")
            for concept in related_concepts:
                concept_name = concept.strip().replace("**", "")
                if concept_name:
                    final_body_lines.append(f"- [[{concept_name}]]")
            final_body_lines.append("")

        if referenced_by:
            final_body_lines.append("## Referenced By")
            final_body_lines.append("")
            for ref in referenced_by:
                ref_name = ref.strip().replace("**", "")
                if ref_name:
                    final_body_lines.append(f"- [[{ref_name}]]")
            final_body_lines.append("")

    elif page_type == "summary":
        if related_concepts:
            final_body_lines.append("## Related Concepts")
            final_body_lines.append("")
            for concept in related_concepts:
                concept_name = concept.strip().replace("**", "")
                if concept_name:
                    final_body_lines.append(f"- [[{concept_name}]]")
            final_body_lines.append("")

        if related_entities:
            final_body_lines.append("## Related Entities")
            final_body_lines.append("")
            for entity in related_entities:
                entity_name = entity.strip().replace("**", "")
                if entity_name:
                    final_body_lines.append(f"- [[{entity_name}]]")
            final_body_lines.append("")

    final_body = "\n".join(final_body_lines).strip()

    fm = frontmatter.strip()
    if fm:
        return f"---\n{fm}\n---\n{final_body}\n"
    else:
        return f"{final_body}\n"


# 为内容添加Wiki链接
def add_wiki_links(content: str, related_pages: List[str]) -> str:
    """
    自动为内容中的相关页面添加Wiki链接
    
    参数:
        content: 原始内容
        related_pages: 相关页面名称列表
    
    返回:
        str: 添加Wiki链接后的内容
    
    实现逻辑:
        1. 按名称长度降序排列，避免短名称先匹配导致问题
        2. 使用正则表达式查找未链接的页面名
        3. 将匹配的文本替换为[[页面名]]格式
        4. 避免重复链接（不会链接已存在于[[]]中的文本）
    """
    import re
    
    # Sort pages by length descending to handle longer names first
    sorted_pages = sorted(related_pages, key=len, reverse=True)
    
    for page in sorted_pages:
        if not page:
            continue
        
        # Create regex pattern that matches the page name but not inside existing links
        # This pattern looks for the page name that is not inside [[...]]
        pattern = re.compile(
            r'(?<!\[\[)\b' + re.escape(page) + r'\b(?!\]\])',
            re.IGNORECASE
        )
        
        # Replace matches with WikiLink
        content = pattern.sub(lambda m: f"[[{m.group(0)}]]", content)
    
    # Remove any nested links (e.g., [[[[Link]]]])
    while re.search(r'\[\[\[\[.*?\]\]\]\]', content):
        content = re.sub(r'\[\[\[\[(.*?)\]\]\]\]', r'[[\1]]', content)
    
    return content


# 简单的无LLM提取
def simple_extract(content: str) -> Dict:
    """
    简单的信息提取（无LLM降级方案）
    
    当LLM不可用时，使用简单启发式方法提取信息:
        - 前2000字符作为摘要
        - 标题行作为概念
        - 文档统计信息作为结论
    
    参数:
        content: 文档内容
    
    返回:
        Dict: 提取的信息字典
    """
    # Extract first 2000 characters as summary
    summary = content[:2000] + ("..." if len(content) > 2000 else "")
    
    # Try to find some key terms (simple heuristics)
    lines = content.split("\n")
    concepts = []
    entities = []
    
    # Look for headings as potential concepts
    for line in lines:
        line = line.strip()
        if line.startswith("#"):
            concept_name = line.lstrip("#").strip()
            if concept_name:
                concepts.append({"name": concept_name, "definition": "From document heading"})
    
    conclusions = [
        f"Document contains {len(content)} characters",
        f"Document has {len(lines)} lines"
    ]
    
    return {
        "concepts": concepts[:5],  # Limit to 5 concepts
        "entities": entities,
        "conclusions": conclusions,
        "summary": summary
    }


# 摄入单个源文件
def ingest_file(source_file: str, config: Dict) -> None:
    """
    摄入单个源文件到知识库
    
    这是知识摄入的核心函数，协调整个摄入流程:
        1. 读取源文件内容
        2. 使用LLM提取概念、实体、结论
        3. 构建关联图谱
        4. 为每个概念创建/更新Wiki页面
        5. 为每个实体创建/更新Wiki页面
        6. 创建摘要页面并添加Wiki链接
        7. 更新所有页面的关联信息
    
    参数:
        source_file: 源文件路径
        config: 配置信息
    """
    print(f"Ingesting: {source_file}")

    try:
        content = read_file_content(source_file)
        print(f"Successfully read {len(content)} characters")
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    try:
        extracted = extract_information(content, config)
        print("Successfully extracted information using LLM")
    except Exception as e:
        print(f"Error extracting information with LLM: {e}")
        print("Falling back to simple extraction without LLM")
        extracted = simple_extract(content)

    wiki_dir = os.path.dirname(config["wiki"]["concepts_dir"]) if config["wiki"]["concepts_dir"] else "wiki"
    association_map = build_association_map(wiki_dir)

    concept_names = [concept["name"].replace("**", "") for concept in extracted["concepts"]]
    entity_names = []
    for entity in extracted["entities"]:
        if isinstance(entity, dict):
            entity_name = entity.get("name", "").replace("**", "")
        else:
            if ":" in entity:
                entity_name = entity.split(":", 1)[0].strip().replace("**", "")
            else:
                entity_name = entity.replace("**", "")
        if entity_name:
            entity_names.append(entity_name)

    for concept in extracted["concepts"]:
        concept_name = concept["name"].replace("**", "")
        concept_safe_name = concept_name.lower().replace(" ", "-")

        referenced_by = association_map["back_links"].get(concept_safe_name, [])

        associations = {
            "related_concepts": [c.replace("**", "") for c in concept_names],
            "related_entities": [e.replace("**", "") for e in entity_names],
            "referenced_by": referenced_by
        }

        concept_content = f"""---
source: {os.path.basename(source_file)}
created: {time.strftime('%Y-%m-%d %H:%M:%S')}
type: concept
---

# {concept_name}

## Definition

{concept['definition']}

## Source

This concept was extracted from: **{os.path.basename(source_file)}**

"""
        page_path = create_or_update_page(
            concept_name, concept_content, "concept", config, source_file, associations
        )
        print(f"Created/updated concept page: {page_path}")

    for entity in extracted["entities"]:
        if isinstance(entity, dict):
            entity_name = entity.get("name", "")
            entity_description = entity.get("description", "")
        else:
            if ":" in entity:
                entity_parts = entity.split(":", 1)
                entity_name = entity_parts[0].strip()
                entity_description = entity_parts[1].strip()
            else:
                entity_name = entity
                entity_description = ""

        if entity_name:
            entity_name_clean = entity_name.replace("**", "")
            entity_safe_name = entity_name_clean.lower().replace(" ", "-")
            referenced_by = association_map["back_links"].get(entity_safe_name, [])

            associations = {
                "related_concepts": [c.replace("**", "") for c in concept_names],
                "related_entities": [e.replace("**", "") for e in entity_names],
                "referenced_by": referenced_by
            }

            entity_content = f"""---
source: {os.path.basename(source_file)}
created: {time.strftime('%Y-%m-%d %H:%M:%S')}
type: entity
---

# {entity_name_clean}

## Description

{entity_description}

## Source

This entity was extracted from: **{os.path.basename(source_file)}**

"""
            page_path = create_or_update_page(
                entity_name, entity_content, "entity", config, source_file, associations
            )
            print(f"Created/updated entity page: {page_path}")

    summary_content = f"""---
source: {os.path.basename(source_file)}
created: {time.strftime('%Y-%m-%d %H:%M:%S')}
type: summary
---

# Summary: {os.path.splitext(os.path.basename(source_file))[0]}

## Source Information

- **File**: {os.path.basename(source_file)}
- **Size**: {len(content)} characters
- **Extracted on**: {time.strftime('%Y-%m-%d %H:%M:%S')}

## Key Concepts

"""
    for concept in extracted["concepts"]:
        concept_name_clean = concept['name'].replace("**", "")
        summary_content += f"- [[{concept_name_clean}]]: {concept['definition'][:100]}...\n"

    summary_content += "\n## Entities\n"
    for entity in extracted["entities"]:
        if isinstance(entity, dict):
            entity_name = entity.get("name", "").replace("**", "")
        else:
            if ":" in entity:
                entity_name = entity.split(":", 1)[0].strip().replace("**", "")
            else:
                entity_name = entity.replace("**", "")
        if entity_name:
            summary_content += f"- [[{entity_name}]]\n"

    summary_content += "\n## Key Conclusions\n"
    for conclusion in extracted["conclusions"]:
        if isinstance(conclusion, dict):
            summary_content += f"- **{conclusion.get('text', '')}**: {conclusion.get('explanation', '')}\n"
        else:
            summary_content += f"- {conclusion}\n"

    if "summary" in extracted:
        summary_content += "\n## Document Preview\n"
        summary_content += extracted["summary"] + "\n"

    summary_content += "\n## Navigation\n"
    summary_content += "- [[index]]: Back to home\n"

    # Skip adding wiki links to summary content - the links are already properly formatted
    # related_pages = concept_names + entity_names
    # summary_content = add_wiki_links(summary_content, related_pages)

    summary_safe_name = os.path.splitext(os.path.basename(source_file))[0].lower().replace(" ", "-")
    summary_referenced_by = association_map["back_links"].get(summary_safe_name, [])

    summary_associations = {
        "related_concepts": [c.replace("**", "") for c in concept_names],
        "related_entities": [e.replace("**", "") for e in entity_names],
        "referenced_by": summary_referenced_by
    }

    summary_name = os.path.splitext(os.path.basename(source_file))[0].replace("**", "")
    
    # 防止创建空文件名的文件
    if not summary_name:
        summary_name = "untitled-summary"
        print(f"Warning: Empty source file name, using default: {summary_name}")
    
    page_path = create_or_update_page(
        summary_name, summary_content, "summary", config, source_file, summary_associations
    )
    print(f"Created/updated summary page: {page_path}")

    wiki_dir_path = os.path.dirname(config["wiki"]["concepts_dir"]) if config["wiki"]["concepts_dir"] else "wiki"
    if os.path.exists(wiki_dir_path):
        all_associations = build_association_map(wiki_dir_path)
        update_all_page_associations(all_associations, config)


def update_all_page_associations(association_map: Dict, config: Dict) -> None:
    """
    更新所有页面的关联信息
    
    在完成新内容摄入后，遍历所有页面并更新:
        - related_concepts: 页面关联的概念列表
        - related_entities: 页面关联的实体列表
        - referenced_by: 引用该页面的其他页面列表
    
    参数:
        association_map: 关联图谱数据
        config: 配置信息
    """
    pages = association_map["pages"]
    back_links = association_map["back_links"]

    for page_name, page_data in pages.items():
        page_type = page_data["type"]
        page_path = page_data["path"]

        associations = {
            "related_concepts": [],
            "related_entities": [],
            "referenced_by": back_links.get(page_name, [])
        }

        for linked_page in association_map["forward_links"].get(page_name, []):
            if linked_page in pages:
                linked_page_type = pages[linked_page]["type"]
                if linked_page_type == "concept":
                    associations["related_concepts"].append(pages[linked_page]["name"])
                elif linked_page_type == "entity":
                    associations["related_entities"].append(pages[linked_page]["name"])

        if not associations["referenced_by"] and not associations["related_concepts"] and not associations["related_entities"]:
            continue

        try:
            with open(page_path, "r", encoding="utf-8") as f:
                existing_content = f.read()

            updated_content = add_associations_to_content(existing_content, associations, page_type)

            with open(page_path, "w", encoding="utf-8") as f:
                f.write(updated_content)

            try:
                print(f"Updated associations for: {page_data['name']}")
            except UnicodeEncodeError:
                # Handle Unicode encoding error by printing the page name as repr
                print(f"Updated associations for: {repr(page_data['name'])}")
        except Exception as e:
            try:
                print(f"Error updating associations for {page_data['name']}: {e}")
            except UnicodeEncodeError:
                # Handle Unicode encoding error by printing the page name as repr
                print(f"Error updating associations for {repr(page_data['name'])}: {e}")


# 主函数
def main():
    """
    程序入口函数
    
    使用方式: python ingest.py <源文件路径>
    
    工作流程:
        1. 检查命令行参数
        2. 验证文件存在性
        3. 加载配置文件
        4. 执行文件摄入
    """
    if len(sys.argv) < 2:
        print("Usage: python ingest.py <source_file>")
        sys.exit(1)

    source_file = sys.argv[1]
    if not os.path.exists(source_file):
        print(f"Error: File not found: {source_file}")
        sys.exit(1)

    # Load configuration
    try:
        config = load_config()
    except Exception as e:
        print(f"Error loading config: {e}")
        sys.exit(1)

    # Ingest the file
    ingest_file(source_file, config)

    # 导入更新索引模块（在函数内部避免循环导入）
    try:
        import subprocess
        update_script = os.path.join(os.path.dirname(__file__), "update_index.py")
        if os.path.exists(update_script):
            print("\n自动更新索引...")
            subprocess.run([sys.executable, update_script], check=False)
    except Exception as e:
        print(f"更新索引时出错: {e}")


if __name__ == "__main__":
    main()
