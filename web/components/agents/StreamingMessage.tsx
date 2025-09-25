'use client';

import { useEffect, useState } from 'react';
import { Loader2 } from 'lucide-react';

interface StreamingMessageProps {
  content: string;
  isComplete?: boolean;
  showCursor?: boolean;
}

export function StreamingMessage({ 
  content, 
  isComplete = false, 
  showCursor = true 
}: StreamingMessageProps) {
  const [displayContent, setDisplayContent] = useState('');
  const [showBlinkingCursor, setShowBlinkingCursor] = useState(true);

  useEffect(() => {
    // Smooth animation when content updates
    if (content !== displayContent) {
      setDisplayContent(content);
    }
  }, [content, displayContent]);

  useEffect(() => {
    // Handle cursor blinking
    if (isComplete) {
      setShowBlinkingCursor(false);
      return;
    }

    const interval = setInterval(() => {
      setShowBlinkingCursor(prev => !prev);
    }, 500);

    return () => clearInterval(interval);
  }, [isComplete]);

  // Format content with basic markdown support
  const formatContent = (text: string) => {
    // Simple markdown formatting
    const formatted = text
      // Bold
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      // Italic  
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      // Code inline
      .replace(/`([^`]+)`/g, '<code class="bg-muted px-1 py-0.5 rounded text-sm font-mono">$1</code>')
      // Line breaks
      .replace(/\n/g, '<br>');

    return formatted;
  };

  return (
    <div className="prose prose-sm dark:prose-invert max-w-none">
      <div 
        dangerouslySetInnerHTML={{ 
          __html: formatContent(displayContent) 
        }} 
      />
      {!isComplete && showCursor && (
        <span className={`inline-block w-2 h-4 bg-primary ml-1 ${showBlinkingCursor ? 'opacity-100' : 'opacity-0'} transition-opacity duration-100`}>
          {/* Cursor */}
        </span>
      )}
      {!isComplete && !displayContent && (
        <div className="flex items-center gap-2 text-muted-foreground">
          <Loader2 className="h-3 w-3 animate-spin" />
          <span className="text-sm">Thinking...</span>
        </div>
      )}
    </div>
  );
}