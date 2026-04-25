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
        return `[${finalName}](wikilink:${encodeURIComponent(finalName)})`;
      }
      return `[${cleanName}](wikilink:${encodeURIComponent(cleanName)})`;
    })
    // Convert any remaining [text](url) links
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, (match, text, url) => {
      // If it's already a wikilink, make sure it's encoded
      if (url.startsWith('wikilink:')) {
        const target = url.slice(9);
        const decodedTarget = decodeURIComponent(target);
        return `[${text}](wikilink:${encodeURIComponent(decodedTarget)})`;
      }
      // If it's a localhost link
      if (url.startsWith('http://localhost:3001/')) {
        return `[${text}](wikilink:${encodeURIComponent(text.trim())})`;
      }
      // If it starts with /
      if (url.startsWith('/') && !url.startsWith('//')) {
        return `[${text}](wikilink:${encodeURIComponent(text.trim())})`;
      }
      // If the url is identical to the text (e.g. [Hugging Face](Hugging Face))
      if (url.trim() === text.trim()) {
        return `[${text}](wikilink:${encodeURIComponent(text.trim())})`;
      }
      // Encode any other URLs with spaces so they parse correctly
      if (url.includes(' ')) {
        return `[${text}](${encodeURI(url)})`;
      }
      return match;
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
