import React, { useState, useEffect } from 'react';
import { RawDocument, RawDocumentType } from '../types';
import { FileUploader } from './FileUploader';
import { FileText, File, Globe, Users, Trash2, Link2 } from 'lucide-react';
import { cn } from '../lib/utils';

interface RawDataViewProps {
  onUploadSuccess?: () => void;
  refreshTrigger?: number;
  onNavigateWiki?: (path: string) => void;
}

interface WikiPage {
  id: string;
  title: string;
  path: string;
}

export function RawDataView({ onUploadSuccess, refreshTrigger, onNavigateWiki }: RawDataViewProps) {
  const [docs, setDocs] = useState<RawDocument[]>([]);
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [linkedPages, setLinkedPages] = useState<WikiPage[]>([]);
  const [loadingPages, setLoadingPages] = useState(false);

  useEffect(() => {
    fetch('/api/system/raw-sources')
      .then(res => res.json())
      .then(data => {
        const list = data.map((d: any) => {
          let dateAdded = new Date().toISOString();
          try {
            if (d.lastModified) {
              dateAdded = new Date(d.lastModified).toISOString();
            } else if (d.dateAdded) {
              dateAdded = new Date(d.dateAdded * 1000).toISOString();
            }
          } catch (error) {
            console.error('Invalid date value:', d.dateAdded || d.lastModified);
          }
          return {
            id: d.id,
            title: d.name || d.title,
            type: (d.type || 'txt') as RawDocumentType,
            content: d.content || '',
            dateAdded
          };
        });
        setDocs(list);
      })
      .catch(err => console.error('Failed to load raw sources', err));
  }, [refreshTrigger]);

  useEffect(() => {
    if (!selectedDocId) {
      setLinkedPages([]);
      return;
    }

    setLoadingPages(true);
    fetch(`/api/system/raw-sources/${encodeURIComponent(selectedDocId)}/preview-delete`)
      .then(res => res.json())
      .then(data => {
        setLinkedPages(data.linked_wiki_pages || []);
        setLoadingPages(false);
      })
      .catch(err => {
        console.error('Failed to load linked pages', err);
        setLinkedPages([]);
        setLoadingPages(false);
      });
  }, [selectedDocId]);

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    
    try {
      const previewRes = await fetch(`/api/system/raw-sources/${encodeURIComponent(id)}/preview-delete`);
      if (!previewRes.ok) throw new Error('Preview failed');
      const previewData = await previewRes.json();
      
      let confirmMsg = `Delete "${id}"?`;
      if (previewData.linked_count > 0) {
        const pageList = previewData.linked_wiki_pages.map((p: any) => p.title).join(', ');
        confirmMsg = `Delete "${id}"?\n\n⚠️ 关联的 Wiki 页面 (${previewData.linked_count}个): ${pageList}\n\n这些页面将被标记为孤立页面。`;
      }
      
      if (!confirm(confirmMsg)) return;
      
      const res = await fetch(`/api/system/raw-sources/${encodeURIComponent(id)}`, { method: 'DELETE' });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        alert(`Delete failed: ${err.detail || res.status}`);
        return;
      }
      setDocs(prev => prev.filter(d => d.id !== id));
      if (selectedDocId === id) setSelectedDocId(null);
    } catch (err) { console.error('Delete failed', err); alert('Delete failed: network error'); }
  };

  const selectedDoc = docs.find(d => d.id === selectedDocId);

  const getIcon = (type: string) => {
    switch (type) {
      case 'pdf': return <File className="w-4 h-4 text-theme-dim" />;
      case 'web': return <Globe className="w-4 h-4 text-theme-dim" />;
      case 'meeting': return <Users className="w-4 h-4 text-theme-dim" />;
      default: return <FileText className="w-4 h-4 text-theme-dim" />;
    }
  };

  const handleNavigateWiki = (pageId: string) => {
    if (onNavigateWiki) {
      const normalizedPath = pageId.replace(/\//g, '-');
      onNavigateWiki(normalizedPath);
    }
  };

  return (
    <div className="flex h-full bg-theme-bg">
      <div className="w-[240px] border-r border-theme-border overflow-y-auto bg-theme-sidebar p-3 flex flex-col gap-5 shrink-0">
        <div>
          <div className="text-[11px] font-bold uppercase text-theme-dim tracking-[0.5px] mb-2 px-2">
            2.1 原始资料层
          </div>
          <FileUploader onUploadSuccess={onUploadSuccess} />
          <ul className="flex flex-col gap-1">
            {docs.map(doc => (
              <li key={doc.id}>
                <button
                  onClick={() => setSelectedDocId(doc.id)}
                  className={cn(
                    "w-full text-left px-2 py-1.5 rounded-[4px] transition-colors flex items-center gap-2 text-[13px]",
                    selectedDocId === doc.id 
                      ? "bg-theme-accent-soft text-theme-accent font-semibold" 
                      : "text-theme-text hover:bg-theme-tag"
                  )}
                >
                  <div className="shrink-0">{getIcon(doc.type)}</div>
                  <span className="truncate flex-1">{doc.title}</span>
                  <span
                    onClick={(e) => handleDelete(e, doc.id)}
                    className="p-1 text-theme-dim hover:text-red-500 cursor-pointer"
                  >
                    <Trash2 className="w-3 h-3" />
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto bg-white flex flex-col">
        {selectedDoc ? (
          <>
            <div className="px-[32px] pt-[24px] pb-[12px] border-b border-theme-border shrink-0">
              <div className="text-[12px] text-theme-dim mb-2">
                原始资料层 / {selectedDoc.type} / {selectedDoc.title}
              </div>
              <h1 className="text-[28px] font-bold text-theme-text mb-4">{selectedDoc.title}</h1>
              <div className="text-[10px] bg-[#fffbdd] border border-[#d4a017] text-[#735c0f] px-1.5 py-0.5 rounded-[4px] inline-block mb-4">
                锁定状态：不可变源
              </div>
            </div>
            <div className="p-[32px] overflow-y-auto">
              <div className="p-4 bg-theme-bg border-radius-[8px] text-[13px] mb-6 rounded-lg">
                <div className="font-bold mb-1">溯源信息 (Immutable Source)</div>
                <code className="font-mono text-theme-dim">
                  source_id: {selectedDoc.id}<br/>
                  timestamp: {new Date(selectedDoc.dateAdded).toLocaleString()}
                </code>
              </div>
              
              {loadingPages ? (
                <div className="p-4 bg-theme-bg rounded-lg mb-6">
                  <div className="flex items-center gap-2 text-theme-dim">
                    <div className="animate-spin w-4 h-4 border-2 border-theme-accent border-t-transparent rounded-full"></div>
                    <span>加载关联Wiki页面...</span>
                  </div>
                </div>
              ) : linkedPages.length > 0 ? (
                <div className="p-4 bg-theme-bg rounded-lg mb-6">
                  <div className="flex items-center gap-2 mb-3">
                    <Link2 className="w-4 h-4 text-theme-accent" />
                    <span className="font-bold text-[13px]">关联的 Wiki 页面 ({linkedPages.length}个)</span>
                  </div>
                  <div className="flex flex-col gap-2">
                    {linkedPages.map(page => (
                      <button
                        key={page.id}
                        onClick={() => handleNavigateWiki(page.id)}
                        className="flex items-center gap-2 px-3 py-2 bg-white rounded border border-theme-border hover:border-theme-accent hover:bg-theme-accent-soft transition-colors text-left"
                      >
                        <span className="text-[13px] text-theme-text">{page.title}</span>
                        <span className="text-[10px] text-theme-dim ml-auto">点击查看</span>
                      </button>
                    ))}
                  </div>
                  <div className="mt-3 pt-3 border-t border-theme-border">
                    <p className="text-[11px] text-theme-dim">
                      删除源文件后，这些Wiki页面将被标记为孤立页面，知识内容仍可保留。
                    </p>
                  </div>
                </div>
              ) : (
                <div className="p-4 bg-theme-bg rounded-lg mb-6">
                  <div className="flex items-center gap-2 text-theme-dim">
                    <Link2 className="w-4 h-4" />
                    <span className="text-[13px]">暂无关联的Wiki页面</span>
                  </div>
                </div>
              )}
              
              <pre className="whitespace-pre-wrap font-mono text-[13px] text-theme-text leading-[1.6]">
                {selectedDoc.content}
              </pre>
            </div>
          </>
        ) : (
          <div className="h-full flex items-center justify-center text-theme-dim flex-col gap-3">
            <FileText className="w-8 h-8 opacity-50" />
            <p className="text-[13px]">选择一个文档查看其原始内容</p>
          </div>
        )}
      </div>
    </div>
  );
}