import React, { useState, useEffect, useRef } from 'react';
import { WikiPage } from '../types';
import { MessageSquare, Send, Bot, User, Loader2, Trash2 } from 'lucide-react';
import { cn } from '../lib/utils';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ChatMessage, getMessages, addMessage, clearMessages, initDefaultMessage } from '../lib/chatDb';

interface ChatViewProps {
  wikiPages: WikiPage[];
  onNavigateWiki: (path: string) => void;
}

export function ChatView({ wikiPages, onNavigateWiki }: ChatViewProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isInitialized, setIsInitialized] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Load messages from IndexedDB on mount
  useEffect(() => {
    const loadMessages = async () => {
      await initDefaultMessage();
      const saved = await getMessages();
      setMessages(saved);
      setIsInitialized(true);
    };
    loadMessages();
  }, []);

  // Auto-scroll to bottom when messages change or initialized
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isInitialized]);

  const handleClearHistory = async () => {
    if (window.confirm('确定要清除聊天历史吗？')) {
      await clearMessages();
      await initDefaultMessage();
      const saved = await getMessages();
      setMessages(saved);
    }
  };

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isLoading) return;

    const newUserMessage: ChatMessage = {
      role: 'user',
      content: inputValue,
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, newUserMessage]);
    setInputValue('');
    setIsLoading(true);
    setError(null);

    try {
      await addMessage(newUserMessage);

      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: inputValue }),
      });

      if (!response.ok) {
        throw new Error('API request failed');
      }

      const data = await response.json();

      const assistantResponse: ChatMessage = {
        role: 'assistant',
        content: data.response,
        timestamp: new Date().toISOString(),
      };

      await addMessage(assistantResponse);
      setMessages(prev => [...prev, assistantResponse]);
    } catch (err) {
      setError('Failed to get response from LLM. Please try again.');

      const errorMessage: ChatMessage = {
        role: 'assistant',
        content: 'I\'m sorry, I couldn\'t process your request. Please try again later.',
        timestamp: new Date().toISOString(),
      };

      await addMessage(errorMessage);
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  if (!isInitialized) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-8 h-8 animate-spin text-theme-accent" />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-theme-bg">
      {/* Header */}
      <div className="px-[32px] py-[16px] border-b border-theme-border shrink-0 bg-theme-sidebar">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <MessageSquare className="w-5 h-5 text-theme-accent" />
            <h1 className="text-[18px] font-semibold text-theme-text">LLM聊天</h1>
          </div>
          <button
            onClick={handleClearHistory}
            className="flex items-center gap-1 px-2 py-1 text-sm text-theme-dim hover:text-theme-text transition-colors"
            title="清除聊天历史"
          >
            <Trash2 className="w-4 h-4" />
            <span>清除历史</span>
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-[32px] space-y-4">
        {messages.map((message, index) => (
          <div
            key={index}
            className={cn(
              "flex gap-3 max-w-3xl",
              message.role === 'user' ? "ml-auto flex-row-reverse" : "mr-auto"
            )}
          >
            <div
              className={cn(
                "w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0",
                message.role === 'user' ? "bg-theme-accent text-white" : "bg-theme-tag text-theme-dim"
              )}
            >
              {message.role === 'user' ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
            </div>
            <div
              className={cn(
                "p-3 rounded-lg max-w-[80%]",
                message.role === 'user'
                  ? "bg-theme-accent-soft text-theme-text rounded-tl-none"
                  : "bg-white text-theme-text border border-theme-border rounded-tr-none"
              )}
            >
              <div className="text-[14px] leading-relaxed prose prose-sm max-w-none">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {message.content}
                </ReactMarkdown>
              </div>
              <div className="mt-1 text-[10px] text-theme-dim">
                {new Date(message.timestamp).toLocaleTimeString()}
              </div>
            </div>
          </div>
        ))}

        {/* Loading indicator */}
        {isLoading && (
          <div className="flex gap-3 max-w-3xl mr-auto">
            <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 bg-theme-tag text-theme-dim">
              <Bot className="w-4 h-4" />
            </div>
            <div className="p-3 rounded-lg max-w-[80%] bg-white text-theme-text border border-theme-border rounded-tr-none">
              <div className="flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin text-theme-accent" />
                <span className="text-[14px] text-theme-dim">思考中...</span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Error message */}
      {error && (
        <div className="px-[32px] py-2 bg-red-100 text-red-700 border-b border-red-200">
          {error}
        </div>
      )}

      {/* Input */}
      <div className="p-[32px] border-t border-theme-border shrink-0 bg-theme-sidebar">
        <div className="flex gap-2">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="输入您的消息..."
            disabled={isLoading}
            className="flex-1 px-4 py-2 border border-theme-border rounded-lg focus:outline-none focus:ring-2 focus:ring-theme-accent focus:border-transparent"
          />
          <button
            onClick={handleSendMessage}
            disabled={isLoading}
            className="px-4 py-2 bg-theme-accent text-white rounded-lg hover:bg-opacity-90 transition-colors flex items-center gap-1 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <>
                <Send className="w-4 h-4" />
                <span>发送</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}