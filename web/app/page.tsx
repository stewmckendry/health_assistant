'use client';

import { useState } from 'react';
import { ChatInterface } from '@/components/chat/ChatInterface';
import { useSession } from '@/hooks/useSession';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { ThemeToggle } from '@/components/theme-toggle';
import { ModeToggle, AssistantMode } from '@/components/ModeToggle';
import { SettingsPanel } from '@/components/settings/SettingsPanel';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Loader2, RefreshCw, Settings, Activity } from 'lucide-react';
import Link from 'next/link';

export default function Home() {
  const { sessionId, userId, isLoading, createNewSession } = useSession();
  const [mode, setMode] = useState<AssistantMode>('patient');
  const [settingsOpen, setSettingsOpen] = useState(false);

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
      <header className="sticky top-0 z-50 bg-background border-b flex-shrink-0">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold">Health Assistant</h1>
              <p className="text-sm text-muted-foreground">
                {mode === 'patient' 
                  ? 'AI-powered medical education platform'
                  : 'Clinical decision support for healthcare providers'
                }
              </p>
            </div>
            <div className="flex items-center gap-2">
              <ModeToggle onModeChange={setMode} defaultMode={mode} />
              <Button
                variant="outline"
                size="sm"
                onClick={() => setSettingsOpen(true)}
                className="gap-2"
              >
                <Settings className="h-4 w-4" />
                Settings
              </Button>
              <ThemeToggle />
              <Link href="/triage">
                <Button
                  variant="outline"
                  size="sm"
                  className="gap-2"
                >
                  <Activity className="h-4 w-4" />
                  ED Triage
                </Button>
              </Link>
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
        <ChatInterface sessionId={sessionId} userId={userId} mode={mode} />
      </main>

      {/* Settings Dialog */}
      <Dialog open={settingsOpen} onOpenChange={setSettingsOpen}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Settings</DialogTitle>
          </DialogHeader>
          <SettingsPanel sessionId={sessionId} />
        </DialogContent>
      </Dialog>
    </div>
  );
}
