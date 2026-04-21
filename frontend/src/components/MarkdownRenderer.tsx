import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface MarkdownRendererProps {
  content: string;
  onWikiLinkClick: (pageName: string) => void;
}

export function MarkdownRenderer({ content, onWikiLinkClick }: MarkdownRendererProps) {
  // Process content to ensure all wiki links are properly formatted
  console.log('Original content:', content); // Debug log
  
  // Remove frontmatter if present
  let processedContent = content;
  if (content.startsWith('---')) {
    const parts = content.split('---', 3);
    if (parts.length >= 3) {
      processedContent = parts[2].trim();
      console.log('Removed frontmatter, content length:', processedContent.length);
    }
  }
  
  processedContent = processedContent
    // Convert [[WikiLinks]] to [WikiLinks](wikilink:WikiLinks)
    .replace(/\[\[(.*?)\]\]/g, (match, p1) => {
      console.log('Found [[WikiLink]]:', match, p1); // Debug log
      // Remove bold markers
      const cleanName = p1.replace(/\*\*/g, '').trim();
      if (cleanName.includes('(deleted)')) {
        const finalName = cleanName.replace('(deleted)', '').trim();
        return `[${finalName}](wikilink:${finalName})`;
      }
      return `[${cleanName}](wikilink:${cleanName})`;
    })
    // Convert any remaining [text](http://localhost:3001/...) links to wiki links
    .replace(/\[(.*?)\]\(http:\/\/localhost:3001\/[^)]*\)/g, (match, text) => {
      return `[${text}](wikilink:${text.trim()})`;
    })
    // Convert any remaining [text](/...) links to wiki links
    .replace(/\[(.*?)\]\(\/(?!\/)[^)]*\)/g, (match, text) => {
      return `[${text}](wikilink:${text.trim()})`;
    });
  console.log('Processed content:', processedContent); // Debug log

  return (
    <div className="prose">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ node, href, children, ...props }) => {
            const hrefStr = String(href || '');
            console.log('Link href:', hrefStr); // Debug log
            console.log('Children:', children); // Debug log
            
            // Try to extract page name from children
            const pageName = String(children || '').trim();
            if (pageName) {
              console.log('Processing link for:', pageName); // Debug log
              return (
                <button
                  onClick={() => {
                    console.log('Clicking link:', pageName); // Debug log
                    onWikiLinkClick(pageName);
                  }}
                  className="text-blue-600 hover:underline cursor-pointer font-normal bg-none border-none p-0 inline"
                  type="button"
                >
                  {children}
                </button>
              );
            }
            
            // For external links, open in new tab
            return (
              <a href={href} target="_blank" rel="noopener noreferrer" {...props}>
                {children}
              </a>
            );
          },
        }}
      >
        {processedContent}
      </ReactMarkdown>
    </div>
  );
}
