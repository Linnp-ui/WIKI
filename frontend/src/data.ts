import { RawDocument, WikiPage } from './types';

export const initialRawDocuments: RawDocument[] = [
  {
    id: 'raw-1',
    title: 'Attention Is All You Need.pdf',
    type: 'pdf',
    content: 'Abstract\nThe dominant sequence transduction models are based on complex recurrent or convolutional neural networks that include an encoder and a decoder. The best performing models also connect the encoder and decoder through an attention mechanism. We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely.',
    dateAdded: '2023-10-01T10:00:00Z',
  },
  {
    id: 'raw-2',
    title: 'Meeting Notes - Project X Sync.txt',
    type: 'meeting',
    content: 'Attendees: Alice, Bob, Charlie\nDate: 2023-10-05\n\nDiscussed the new architecture for the knowledge graph. Decided to use a two-layer approach: a raw data layer that is immutable, and a wiki layer maintained by the LLM. Bob will look into the Markdown rendering.',
    dateAdded: '2023-10-05T14:30:00Z',
  },
  {
    id: 'raw-3',
    title: 'Andrej Karpathy Blog - Software 2.0.web',
    type: 'web',
    content: 'Neural networks are not just another classifier, they represent the beginning of a fundamental shift in how we write software. They are Software 2.0.',
    dateAdded: '2023-10-10T09:15:00Z',
  }
];

export const initialWikiPages: WikiPage[] = [
  {
    path: 'index.md',
    content: '# Wiki Knowledge Graph\n\nWelcome to the Wiki Knowledge Graph. This system is divided into two main layers:\n\n1. **Raw Data Layer**: Immutable source of truth.\n2. **Wiki Knowledge Layer**: Structured knowledge maintained by the LLM.\n\n## Quick Links\n- [[Transformer Architecture]]\n- [[Software 2.0]]\n- [[Andrej Karpathy]]\n\nNavigate using the sidebar or click on the WikiLinks to explore.',
    lastModified: '2023-10-11T10:00:00Z',
  },
  {
    path: 'concepts/Transformer Architecture.md',
    content: '# Transformer Architecture\n\nThe Transformer is a deep learning architecture introduced in the paper "Attention Is All You Need". It relies entirely on self-attention mechanisms, dispensing with recurrences and convolutions.\n\n## Key Components\n- Self-Attention\n- Multi-Head Attention\n- Feed-Forward Networks\n\n*Source: [[Attention Is All You Need.pdf]]*',
    lastModified: '2023-10-11T10:05:00Z',
  },
  {
    path: 'concepts/Software 2.0.md',
    content: '# Software 2.0\n\nA concept popularized by [[Andrej Karpathy]], describing a shift in software development where code is written by optimization algorithms (like neural networks) rather than human programmers explicitly writing instructions.',
    lastModified: '2023-10-11T10:10:00Z',
  },
  {
    path: 'entities/Andrej Karpathy.md',
    content: '# Andrej Karpathy\n\nAndrej Karpathy is a computer scientist and former Director of AI at Tesla. He is known for his work in deep learning and computer vision, and for popularizing the term [[Software 2.0]].',
    lastModified: '2023-10-11T10:15:00Z',
  },
  {
    path: 'summaries/Attention Is All You Need.pdf.md',
    content: '# Summary: Attention Is All You Need\n\nThis paper introduces the [[Transformer Architecture]], a novel neural network architecture based solely on attention mechanisms. It achieves state-of-the-art results on translation tasks while being more parallelizable and requiring significantly less time to train than previous recurrent or convolutional models.',
    lastModified: '2023-10-11T10:20:00Z',
  }
];
