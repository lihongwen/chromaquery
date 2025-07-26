import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { tomorrow } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface MarkdownRendererProps {
  content: string;
  style?: React.CSSProperties;
}

const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content, style }) => {
  return (
    <div style={style}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code({ node, inline, className, children, ...props }) {
            const match = /language-(\w+)/.exec(className || '');
            return !inline && match ? (
              <SyntaxHighlighter
                style={tomorrow}
                language={match[1]}
                PreTag="div"
                {...props}
              >
                {String(children).replace(/\n$/, '')}
              </SyntaxHighlighter>
            ) : (
              <code 
                className={className} 
                style={{
                  backgroundColor: '#f6f8fa',
                  padding: '2px 4px',
                  borderRadius: '3px',
                  fontSize: '0.9em',
                  color: '#d73a49'
                }}
                {...props}
              >
                {children}
              </code>
            );
          },
          h1: ({ children }) => (
            <h1 style={{ 
              fontSize: '1.8em', 
              fontWeight: 600, 
              marginBottom: '0.5em',
              borderBottom: '2px solid #eaecef',
              paddingBottom: '0.3em'
            }}>
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2 style={{ 
              fontSize: '1.5em', 
              fontWeight: 600, 
              marginBottom: '0.5em',
              borderBottom: '1px solid #eaecef',
              paddingBottom: '0.3em'
            }}>
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 style={{ 
              fontSize: '1.3em', 
              fontWeight: 600, 
              marginBottom: '0.5em'
            }}>
              {children}
            </h3>
          ),
          h4: ({ children }) => (
            <h4 style={{ 
              fontSize: '1.1em', 
              fontWeight: 600, 
              marginBottom: '0.5em'
            }}>
              {children}
            </h4>
          ),
          h5: ({ children }) => (
            <h5 style={{ 
              fontSize: '1em', 
              fontWeight: 600, 
              marginBottom: '0.5em'
            }}>
              {children}
            </h5>
          ),
          h6: ({ children }) => (
            <h6 style={{ 
              fontSize: '0.9em', 
              fontWeight: 600, 
              marginBottom: '0.5em',
              color: '#6a737d'
            }}>
              {children}
            </h6>
          ),
          p: ({ children }) => (
            <p style={{ 
              marginBottom: '1em', 
              lineHeight: '1.6',
              color: '#24292e'
            }}>
              {children}
            </p>
          ),
          ul: ({ children }) => (
            <ul style={{ 
              marginBottom: '1em',
              paddingLeft: '2em',
              lineHeight: '1.6'
            }}>
              {children}
            </ul>
          ),
          ol: ({ children }) => (
            <ol style={{ 
              marginBottom: '1em',
              paddingLeft: '2em',
              lineHeight: '1.6'
            }}>
              {children}
            </ol>
          ),
          li: ({ children }) => (
            <li style={{ 
              marginBottom: '0.25em',
              color: '#24292e'
            }}>
              {children}
            </li>
          ),
          strong: ({ children }) => (
            <strong style={{ 
              fontWeight: 600,
              color: '#24292e'
            }}>
              {children}
            </strong>
          ),
          em: ({ children }) => (
            <em style={{ 
              fontStyle: 'italic',
              color: '#24292e'
            }}>
              {children}
            </em>
          ),
          blockquote: ({ children }) => (
            <blockquote style={{
              borderLeft: '4px solid #dfe2e5',
              paddingLeft: '1em',
              margin: '1em 0',
              color: '#6a737d',
              fontStyle: 'italic'
            }}>
              {children}
            </blockquote>
          ),
          table: ({ children }) => (
            <div style={{ overflowX: 'auto', marginBottom: '1em' }}>
              <table style={{
                borderCollapse: 'collapse',
                width: '100%',
                border: '1px solid #d0d7de'
              }}>
                {children}
              </table>
            </div>
          ),
          th: ({ children }) => (
            <th style={{
              border: '1px solid #d0d7de',
              padding: '6px 13px',
              backgroundColor: '#f6f8fa',
              fontWeight: 600,
              textAlign: 'left'
            }}>
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td style={{
              border: '1px solid #d0d7de',
              padding: '6px 13px'
            }}>
              {children}
            </td>
          ),
          a: ({ children, href }) => (
            <a 
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                color: '#0969da',
                textDecoration: 'none'
              }}
              onMouseOver={(e) => {
                e.currentTarget.style.textDecoration = 'underline';
              }}
              onMouseOut={(e) => {
                e.currentTarget.style.textDecoration = 'none';
              }}
            >
              {children}
            </a>
          ),
          hr: () => (
            <hr style={{
              border: 'none',
              borderTop: '2px solid #eaecef',
              margin: '1.5em 0'
            }} />
          )
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
};

export default MarkdownRenderer;