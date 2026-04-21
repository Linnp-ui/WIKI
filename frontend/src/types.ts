export type RawDocumentType = 'pdf' | 'web' | 'meeting' | 'txt';

export interface RawDocument {
  id: string;
  title: string;
  type: RawDocumentType;
  content: string;
  dateAdded: string;
}

export interface WikiPage {
  id: string;
  title: string;
  path: string;
  content: string;
  lastModified: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}
