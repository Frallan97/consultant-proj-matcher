import { Card, CardContent } from "@/components/ui/card";
import ReactMarkdown from "react-markdown";

interface MessageBubbleProps {
  role: "user" | "assistant";
  content: string;
}

export function MessageBubble({ role, content }: MessageBubbleProps) {
  const isUser = role === "user";
  
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-3 sm:mb-4 animate-in fade-in slide-in-from-bottom-2 duration-300`}>
      <Card 
        className={`max-w-[85%] sm:max-w-[80%] hover:shadow-md transition-shadow ${
          isUser 
            ? "bg-primary text-primary-foreground border-primary/20" 
            : "bg-muted/50 border-border/50"
        }`}
      >
        <CardContent className="p-2 sm:p-4">
          <div className={`text-xs sm:text-sm ${isUser ? "text-primary-foreground" : ""}`}>
            <ReactMarkdown
              components={{
                // Style markdown elements
                p: ({ children }) => (
                  <p className={`mb-2 last:mb-0 ${isUser ? "text-primary-foreground" : ""}`}>
                    {children}
                  </p>
                ),
                strong: ({ children }) => (
                  <strong className={`font-semibold ${isUser ? "text-primary-foreground" : ""}`}>
                    {children}
                  </strong>
                ),
                em: ({ children }) => (
                  <em className={`italic ${isUser ? "text-primary-foreground" : ""}`}>
                    {children}
                  </em>
                ),
                ul: ({ children }) => (
                  <ul className={`list-disc list-inside mb-2 space-y-1 ${isUser ? "text-primary-foreground" : ""}`}>
                    {children}
                  </ul>
                ),
                ol: ({ children }) => (
                  <ol className={`list-decimal list-inside mb-2 space-y-1 ${isUser ? "text-primary-foreground" : ""}`}>
                    {children}
                  </ol>
                ),
                li: ({ children }) => (
                  <li className={`ml-2 ${isUser ? "text-primary-foreground" : ""}`}>
                    {children}
                  </li>
                ),
                h1: ({ children }) => (
                  <h1 className={`text-lg font-bold mb-2 ${isUser ? "text-primary-foreground" : ""}`}>
                    {children}
                  </h1>
                ),
                h2: ({ children }) => (
                  <h2 className={`text-base font-bold mb-2 ${isUser ? "text-primary-foreground" : ""}`}>
                    {children}
                  </h2>
                ),
                h3: ({ children }) => (
                  <h3 className={`text-sm font-semibold mb-1 ${isUser ? "text-primary-foreground" : ""}`}>
                    {children}
                  </h3>
                ),
                code: ({ children }) => (
                  <code className={`${isUser ? "bg-primary/20 text-primary-foreground" : "bg-muted/50"} px-1 py-0.5 rounded text-xs font-mono`}>
                    {children}
                  </code>
                ),
                pre: ({ children }) => (
                  <pre className={`${isUser ? "bg-primary/20 text-primary-foreground" : "bg-muted/50"} p-2 rounded overflow-x-auto mb-2`}>
                    {children}
                  </pre>
                ),
              }}
            >
              {content}
            </ReactMarkdown>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

