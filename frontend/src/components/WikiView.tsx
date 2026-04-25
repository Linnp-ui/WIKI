import React, { useMemo, useState } from 'react';
import { WikiPage } from '../types';
import { WIKI_FOLDER_CONFIG } from '../lib/config';
import { MarkdownRenderer } from './MarkdownRenderer';
import { Folder, FileText, Trash2, ChevronDown, ChevronRight, BookOpen, Users, FileClock, ArrowLeft } from 'lucide-react';
import { cn } from '../lib/utils';

interface WikiViewProps {
  pages: WikiPage[];
  currentPath: string;
  onNavigate: (path: string) => void;
  onDeletePage?: (pageId: string) => void;
  onGoBack?: () => void;
  canGoBack?: boolean;
}

type TreeNode = {
  name: string;
  path: string;
  type: 'file' | 'folder';
  children?: Record<string, TreeNode>;
};

export function WikiView({ pages, currentPath, onNavigate, onDeletePage, onGoBack, canGoBack }: WikiViewProps) {
  const currentPage = pages.find(p => p.path === currentPath);
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set(['concepts', 'entities', 'summaries']));

  const fileTree = useMemo(() => {
    const root: Record<string, TreeNode> = {
      concepts: {
        name: 'concepts',
        path: 'concepts',
        type: 'folder',
        children: {}
      },
      entities: {
        name: 'entities',
        path: 'entities',
        type: 'folder',
        children: {}
      },
      summaries: {
        name: 'summaries',
        path: 'summaries',
        type: 'folder',
        children: {}
      }
    };

    pages.forEach(page => {
      const parts = page.path.split('/');
      
      // Handle pages in subdirectories
      if (parts.length >= 2) {
        const folderName = parts[0];
        const fileName = parts[1];
        
        // Only process pages in explicitly allowed folders (not backend folders like raw_sources)
        if (WIKI_FOLDER_CONFIG.allowedFolders.includes(folderName as any)) {
          if (!root[folderName].children) {
            root[folderName].children = {};
          }
          
          root[folderName].children![fileName] = {
            name: fileName,
            path: page.path,
            type: 'file'
          };
        }
      }
    });

    return root;
  }, [pages]);

  const toggleFolder = (folderPath: string) => {
    setExpandedFolders(prev => {
      const newSet = new Set(prev);
      if (newSet.has(folderPath)) {
        newSet.delete(folderPath);
      } else {
        newSet.add(folderPath);
      }
      return newSet;
    });
  };

  const getFolderIcon = (folderName: string) => {
    switch (folderName) {
      case 'concepts':
        return <BookOpen className="w-4 h-4" />;
      case 'entities':
        return <Users className="w-4 h-4" />;
      case 'summaries':
        return <FileClock className="w-4 h-4" />;
      default:
        return <Folder className="w-4 h-4" />;
    }
  };

  const getFolderLabel = (folderName: string) => {
    switch (folderName) {
      case 'concepts':
        return '概念';
      case 'entities':
        return '实体';
      case 'summaries':
        return '摘要';
      default:
        return folderName;
    }
  };

  const renderTree = (nodes: Record<string, TreeNode>, level = 0) => {
    return Object.values(nodes).map(node => {
      const isExpanded = expandedFolders.has(node.path);
      
      return (
        <div key={node.path} className={cn(level > 0 && "ml-3 border-l border-gray-200 pl-3 mt-1")}>
          <div className="flex items-center">
            {node.type === 'folder' && (
              <button
                onClick={() => toggleFolder(node.path)}
                className="mr-1 p-1 rounded-md hover:bg-gray-100 transition-colors"
              >
                {isExpanded ? (
                  <ChevronDown className="w-3 h-3 text-gray-600" />
                ) : (
                  <ChevronRight className="w-3 h-3 text-gray-600" />
                )}
              </button>
            )}
            <button
              onClick={() => node.type === 'file' ? onNavigate(node.path) : toggleFolder(node.path)}
              className={cn(
                "flex-1 text-left px-2 py-1.5 rounded-md flex items-center gap-2 transition-colors text-sm",
                currentPath === node.path 
                  ? "bg-blue-50 text-blue-700 font-semibold" 
                  : "text-gray-700 hover:bg-gray-50",
                node.type === 'folder' ? "font-medium" : ""
              )}
            >
              {node.type === 'folder' ? (
                <div className="flex items-center gap-2">
                  {getFolderIcon(node.name)}
                  <span className="truncate">{getFolderLabel(node.name)}</span>
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <FileText className="w-4 h-4 text-gray-500" />
                  <span className="truncate">{node.name.replace(/\.md$/, '')}</span>
                </div>
              )}
            </button>
            {node.type === 'file' && (
              <button
                onClick={(e) => handleDeletePage(e, getPageIdFromPath(node.path), node.name.replace(/\.md$/, ''))}
                className="p-1 text-gray-400 hover:text-red-500 transition-colors"
                title="Delete page"
              >
                <Trash2 className="w-3 h-3" />
              </button>
            )}
          </div>
          {node.children && isExpanded && (
            <div className="mt-1">
              {renderTree(node.children, level + 1)}
            </div>
          )}
        </div>
      );
    });
  };

  const handleWikiLinkClick = (pageName: string) => {
    console.log('Looking for page:', pageName); // Debug log
    
    // 1. 首先尝试精确匹配（检查是否存在完全匹配的页面）
    let targetPage = pages.find(p => {
      // 如果 pageName 包含路径分隔符，尝试完整路径匹配
      if (pageName.includes('/')) {
        const pagePathWithoutExt = p.path.replace(/\.md$/, '');
        if (pagePathWithoutExt.toLowerCase() === pageName.toLowerCase()) return true;
      }
      // 否则只匹配文件名
      const pageBaseName = p.path.split('/').pop()?.replace(/\.md$/, '');
      return pageBaseName?.toLowerCase() === pageName.toLowerCase();
    });
    
    // 2. 如果没有找到，尝试模糊匹配（检查路径中是否包含关键词）
    if (!targetPage) {
      // 提取关键词（去除常见修饰词）
      const keywords = pageName
        .replace(/的|了|和|与|或|是|在|有|为|以|我|他|她|它|们|这|那|你|您|能|可以|应该|必须|需要|如何|什么|为什么|怎样|哪里|何时|多少|哪些|哪个/g, ' ')
        .split(/\s+/)
        .filter(word => word.length > 1);
      
      if (keywords.length > 0) {
        // 计算每个页面的匹配分数
        const scoredPages = pages.map(page => {
          let score = 0;
          const pageText = (page.path + ' ' + page.title + ' ' + page.content).toLowerCase();
          
          keywords.forEach(keyword => {
            if (pageText.includes(keyword.toLowerCase())) {
              score += 1;
              // 如果在路径中匹配，加分
              if (page.path.toLowerCase().includes(keyword.toLowerCase())) {
                score += 2;
              }
              // 如果在标题中匹配，加分
              if (page.title.toLowerCase().includes(keyword.toLowerCase())) {
                score += 1;
              }
            }
          });
          
          return { page, score };
        }).filter(({ score }) => score > 0);
        
        // 按分数排序，选择最高分的页面
        if (scoredPages.length > 0) {
          scoredPages.sort((a, b) => b.score - a.score);
          targetPage = scoredPages[0].page;
        }
      }
    }
    
    // 3. 如果还是没有找到，尝试按类型搜索（优先搜索概念页面）
    if (!targetPage) {
      const conceptPages = pages.filter(p => p.path.startsWith('concepts/'));
      targetPage = conceptPages.find(p => {
        const pageText = (p.path + ' ' + p.title + ' ' + p.content).toLowerCase();
        return pageText.includes(pageName.toLowerCase());
      });
    }
    
    if (targetPage) {
      console.log('Found page:', targetPage.path); // Debug log
      onNavigate(targetPage.path);
    } else {
      console.warn(`Wiki page not found: ${pageName}`);
    }
  };

  const handleDeletePage = async (e: React.MouseEvent, pageId: string, pageTitle: string) => {
    e.stopPropagation();
    if (!confirm(`Delete page "${pageTitle}"?`)) return;
    
    try {
      const res = await fetch(`/api/pages/${encodeURIComponent(pageId)}`, { method: 'DELETE' });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        alert(`Delete failed: ${err.detail || res.status}`);
        return;
      }
      
      const data = await res.json();
      let msg = 'Page deleted successfully';
      if (data.referencing_pages && data.referencing_pages.length > 0) {
        const refs = data.referencing_pages.map((p: any) => p.title).join(', ');
        msg += `\n\n已清理 ${data.cleaned_links} 个死链接。\n引用页面: ${refs}`;
      }
      alert(msg);
      
      if (typeof onDeletePage === 'function') {
        onDeletePage(pageId);
      }
    } catch (err) { 
      console.error('Delete failed', err); 
      alert('Delete failed: network error'); 
    }
  };

  const getPageIdFromPath = (path: string) => path.replace(/\.md$/, '');

  return (
    <div className="flex h-full bg-gray-50">
      {/* Sidebar Tree */}
      <div className="w-[260px] border-r border-gray-200 overflow-y-auto bg-white p-4 shrink-0 shadow-sm">
        <div className="mb-6">
          <h2 className="text-xs font-bold uppercase text-gray-500 tracking-wider mb-3 px-2">
            2.2 Wiki 知识层
          </h2>
          <div className="flex flex-col gap-1">
            {renderTree(fileTree)}
          </div>
        </div>
        <div className="mt-auto pt-4 border-t border-gray-200">
          <div className="text-xs text-gray-500 px-2">
            {Object.keys(fileTree).map(folder => {
              const folderNode = fileTree[folder];
              const fileCount = folderNode.children ? Object.keys(folderNode.children).length : 0;
              return (
                <div key={folder} className="flex justify-between py-1">
                  <span>{getFolderLabel(folder)}</span>
                  <span className="font-mono">{fileCount}</span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto bg-white flex flex-col">
        {currentPage ? (
          <>
            <div className="px-8 pt-6 pb-3 border-b border-gray-200 shrink-0">
              <div className="flex items-center gap-4 mb-2">
                {canGoBack && onGoBack && (
                  <button
                    onClick={onGoBack}
                    className="flex items-center gap-1 text-blue-600 hover:text-blue-800 transition-colors text-sm"
                  >
                    <ArrowLeft className="w-4 h-4" />
                    <span>返回上一页</span>
                  </button>
                )}
                <div className="text-sm text-gray-500 flex-1">
                  Wiki 知识层 / {currentPage.path.split('/').map((p, i) => (
                    <React.Fragment key={i}>
                      {i > 0 && ' / '}
                      {i === 0 ? getFolderLabel(p) : p.replace(/\.md$/, '')}
                    </React.Fragment>
                  ))}
                </div>
              </div>
              <h1 className="text-2xl font-bold text-gray-900 mb-3">
                {currentPage.path.split('/').pop()?.replace(/\.md$/, '')}
              </h1>
              <div className="text-xs bg-yellow-50 border border-yellow-200 text-yellow-800 px-2 py-1 rounded-md inline-block">
                最后修改: {new Date(currentPage.lastModified).toLocaleDateString()}
              </div>
            </div>
            <div className="p-8 overflow-y-auto">
              <MarkdownRenderer content={currentPage.content} onWikiLinkClick={handleWikiLinkClick} />
            </div>
          </>
        ) : (
          <div className="h-full flex items-center justify-center text-gray-400 flex-col gap-3">
            <FileText className="w-12 h-12 opacity-50" />
            <p className="text-sm">选择一个页面查看</p>
            <div className="mt-2 text-xs text-gray-300">
              从左侧选择概念、实体或摘要页面
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
