import React, { useState, useEffect } from 'react';
import { Database, Network, MessageSquare, Menu, ArrowLeft } from 'lucide-react';
import { RawDataView } from './components/RawDataView';
import { WikiView } from './components/WikiView';
import { ChatView } from './components/ChatView';
import { cn } from './lib/utils';
import { WikiPage } from './types';

type ViewMode = 'raw' | 'wiki' | 'chat';

export default function App() {
  const [viewMode, setViewMode] = useState<ViewMode>('wiki');
  const [currentWikiPath, setCurrentWikiPath] = useState('index.md');
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [wikiPages, setWikiPages] = useState<WikiPage[]>([]);
  const [rawRefreshTrigger, setRawRefreshTrigger] = useState(0);
  const [navigationHistory, setNavigationHistory] = useState<string[]>(['index.md']);
  const [historyIndex, setHistoryIndex] = useState(-1);

  const refreshWikiPages = () => {
    fetch('/api/wiki/pages')
      .then(res => res.json())
      .then(data => {
        const pages = data.map((p: any) => ({
          path: p.path.split('\\').join('/'),
          content: p.content,
          title: p.title || p.path.split('/').pop()?.replace(/\.md$/, '') || '',
          lastModified: p.lastModified ? new Date(p.lastModified * 1000).toISOString() : new Date().toISOString()
        }));
        setWikiPages(pages);
      })
      .catch(err => console.error('Failed to load wiki pages', err));
  };

  useEffect(() => {
    refreshWikiPages();
  }, []);

  useEffect(() => {
    if (wikiPages.length > 0 && currentWikiPath === 'index.md') {
      const defaultPage = wikiPages.find(p => p.path.endsWith('index.md')) 
        || wikiPages.find(p => p.path.endsWith('/index.md'))
        || wikiPages[0];
      if (defaultPage) {
        setCurrentWikiPath(defaultPage.path);
        setNavigationHistory([defaultPage.path]);
        setHistoryIndex(0);
      }
    }
  }, [wikiPages]);

  useEffect(() => {
    // Auto-select a default page once pages are loaded
    if (wikiPages.length > 0 && currentWikiPath === 'index.md') {
      const defaultPage = wikiPages.find(p => p.path.endsWith('index.md')) 
        || wikiPages.find(p => p.path.endsWith('/index.md'))
        || wikiPages[0];
      if (defaultPage) {
        setCurrentWikiPath(defaultPage.path);
        setNavigationHistory([defaultPage.path]);
        setHistoryIndex(0);
      }
    }
  }, [wikiPages]);

  const handleNavigateWiki = (path: string) => {
    const isNewPage = path !== currentWikiPath;
    if (isNewPage) {
      const newHistory = historyIndex >= 0 ? navigationHistory.slice(0, historyIndex + 1) : [];
      newHistory.push(path);
      setNavigationHistory(newHistory);
      setHistoryIndex(newHistory.length - 1);
    }
    
    setCurrentWikiPath(path);
    setViewMode('wiki');
  };

  const handleGoBack = () => {
    if (historyIndex > 0) {
      const newIndex = historyIndex - 1;
      setHistoryIndex(newIndex);
      setCurrentWikiPath(navigationHistory[newIndex]);
    }
  };

  const navItems = [
    { id: 'raw', label: '原始数据层', icon: Database },
    { id: 'wiki', label: 'Wiki知识', icon: Network },
    { id: 'chat', label: 'LLM聊天', icon: MessageSquare },
  ] as const;

  return (
    <div className="flex h-screen bg-theme-bg text-theme-text font-sans overflow-hidden flex-col md:flex-row">
      <header className="md:hidden h-[48px] bg-theme-sidebar border-b border-theme-border flex items-center px-4 justify-between shrink-0 z-50">
        <div className="font-bold text-[14px] flex items-center gap-2">
          <Network className="w-5 h-5 text-theme-accent" />
          知识操作系统
        </div>
        <button onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)} className="p-2 -mr-2 text-theme-dim">
          <Menu className="w-5 h-5" />
        </button>
      </header>

      <aside className={cn(
        "fixed md:static top-[48px] bottom-0 left-0 w-[240px] bg-theme-sidebar border-r border-theme-border flex flex-col transition-transform duration-200 ease-in-out z-40 p-3 gap-5 shrink-0",
        isMobileMenuOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
      )}>
        <div className="hidden md:flex font-bold text-[14px] items-center gap-2 px-2 py-1">
          <Network className="w-5 h-5 text-theme-accent" />
          知识操作系统
        </div>

        <nav className="flex flex-col gap-1">
          <div className="text-[11px] font-bold uppercase text-theme-dim tracking-[0.5px] mb-2 px-2">
            模块
          </div>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = viewMode === item.id;
            return (
              <button
                key={item.id}
                onClick={() => {
                  setViewMode(item.id);
                  setIsMobileMenuOpen(false);
                }}
                className={cn(
                  "w-full flex items-center gap-2 px-2 py-1.5 rounded-[4px] transition-colors text-[13px]",
                  isActive 
                    ? "bg-theme-accent-soft text-theme-accent font-semibold" 
                    : "text-theme-text hover:bg-theme-tag"
                )}
              >
                <Icon className="w-4 h-4" />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
        
        <div className="mt-auto px-2 py-2 text-[12px] text-theme-dim border-t border-theme-border">
          v2.1 Stable
        </div>
      </aside>

      <main className="flex-1 flex flex-col min-w-0 relative z-0 bg-theme-bg overflow-hidden">
        {viewMode === 'raw' && <RawDataView onUploadSuccess={() => { refreshWikiPages(); setRawRefreshTrigger(t => t + 1); }} refreshTrigger={rawRefreshTrigger} onNavigateWiki={(path) => { setViewMode('wiki'); handleNavigateWiki(path); }} />}
        {viewMode === 'wiki' && (
          <WikiView 
            pages={wikiPages} 
            currentPath={currentWikiPath} 
            onNavigate={handleNavigateWiki}
            onGoBack={handleGoBack}
            canGoBack={historyIndex >= 0}
            onWikiLinkClick={handleNavigateWiki}
            onDeletePage={(pageId) => {
              setWikiPages(prev => prev.filter(p => p.path !== `${pageId}.md`));
              if (currentWikiPath === `${pageId}.md`) setCurrentWikiPath('index.md');
            }}
          />
        )}
        {viewMode === 'chat' && (
          <ChatView 
            wikiPages={wikiPages}
            onNavigateWiki={handleNavigateWiki}
          />
        )}
      </main>
      
      {isMobileMenuOpen && (
        <div 
          className="fixed inset-0 bg-black/20 z-30 md:hidden top-[48px]" 
          onClick={() => setIsMobileMenuOpen(false)}
        />
      )}
    </div>
  );
}