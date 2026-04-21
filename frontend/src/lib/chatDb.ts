import Dexie, { Table } from 'dexie';

/**
 * 聊天消息类型定义
 */
export interface ChatMessage {
  id?: number;           // 消息ID（自增）
  role: 'user' | 'assistant';  // 消息角色：用户或AI助手
  content: string;       // 消息内容
  timestamp: string;     // 时间戳
}

/**
 * 聊天数据库类（基于Dexie.js）
 * 使用IndexedDB存储聊天记录
 */
class ChatDatabase extends Dexie {
  messages!: Table<ChatMessage>;

  constructor() {
    super('LLMChatDB');
    this.version(1).stores({
      messages: '++id, role, timestamp'
    });
  }
}

// 导出数据库实例
export const chatDB = new ChatDatabase();

/**
 * 获取所有聊天消息
 * 按时间戳排序返回
 */
export async function getMessages(): Promise<ChatMessage[]> {
  return await chatDB.messages.orderBy('timestamp').toArray();
}

/**
 * 添加单条聊天消息
 * @param message - 消息对象（不含id，由数据库自动生成）
 * @returns 新消息的ID
 */
export async function addMessage(message: Omit<ChatMessage, 'id'>): Promise<number> {
  return await chatDB.messages.add(message);
}

/**
 * 清空所有聊天消息
 */
export async function clearMessages(): Promise<void> {
  await chatDB.messages.clear();
}

/**
 * 初始化默认欢迎消息
 * 当数据库为空时添加初始消息
 */
export async function initDefaultMessage(): Promise<void> {
  const count = await chatDB.messages.count();
  if (count === 0) {
    await chatDB.messages.add({
      role: 'assistant',
      content: 'Hello! I\'m your LLM assistant. How can I help you today?',
      timestamp: new Date().toISOString(),
    });
  }
}