'use client';

import { ChatInterface } from '@/components/chat/ChatInterface';
import { useSession } from '@/hooks/useSession';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { ThemeToggle } from '@/components/theme-toggle';
import { Loader2, RefreshCw } from 'lucide-react';

export default function Home() {
  const { sessionId, userId, isLoading, createNewSession } = useSession();

  if (isLoading || !sessionId) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Card className="p-8">
          <div className="flex flex-col items-center gap-4">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
            <p className="text-muted-foreground">Initializing session...</p>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <header className="border-b flex-shrink-0">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold">Health Assistant</h1>
              <p className="text-sm text-muted-foreground">
                AI-powered medical education platform
              </p>
            </div>
            <div className="flex items-center gap-2">
              <ThemeToggle />
              <Button
                variant="outline"
                size="sm"
                onClick={createNewSession}
                className="gap-2"
              >
                <RefreshCw className="h-4 w-4" />
                New Session
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8 flex-1 flex flex-col">
        <ChatInterface sessionId={sessionId} userId={userId} />
      </main>
    </div>
  );
}
