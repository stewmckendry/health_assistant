'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { Stethoscope, Users, ChevronDown } from 'lucide-react';

export type AssistantMode = 'patient' | 'provider';

interface ModeToggleProps {
  onModeChange?: (mode: AssistantMode) => void;
  defaultMode?: AssistantMode;
}

export function ModeToggle({ onModeChange, defaultMode = 'patient' }: ModeToggleProps) {
  const [mode, setMode] = useState<AssistantMode>(defaultMode);
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    // Load mode from localStorage on mount
    const savedMode = localStorage.getItem('assistantMode') as AssistantMode;
    if (savedMode && ['patient', 'provider'].includes(savedMode)) {
      setMode(savedMode);
      onModeChange?.(savedMode);
    }
  }, []);

  const handleModeChange = (newMode: AssistantMode) => {
    setMode(newMode);
    localStorage.setItem('assistantMode', newMode);
    onModeChange?.(newMode);
    setIsOpen(false);
  };

  const modeConfig = {
    patient: {
      label: 'Patient',
      icon: Users,
      description: 'Educational health information for patients',
      color: 'bg-blue-500',
    },
    provider: {
      label: 'Provider',
      icon: Stethoscope,
      description: 'Clinical information for healthcare professionals',
      color: 'bg-purple-500',
    },
  };

  const currentConfig = modeConfig[mode];
  const Icon = currentConfig.icon;

  return (
    <Popover open={isOpen} onOpenChange={setIsOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          className="gap-2 min-w-[120px] justify-between"
        >
          <div className="flex items-center gap-2">
            <Icon className="h-4 w-4" />
            <span>{currentConfig.label}</span>
          </div>
          <ChevronDown className="h-3 w-3 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-80" align="end">
        <div className="space-y-3">
          <div className="font-semibold text-sm">Select Assistant Mode</div>
          {Object.entries(modeConfig).map(([modeKey, config]) => {
            const ModeIcon = config.icon;
            const isSelected = mode === modeKey;
            return (
              <div
                key={modeKey}
                onClick={() => handleModeChange(modeKey as AssistantMode)}
                className={`
                  cursor-pointer rounded-lg border p-3 transition-all
                  ${isSelected 
                    ? 'border-primary bg-primary/5' 
                    : 'border-border hover:border-primary/50'
                  }
                `}
              >
                <div className="flex items-start gap-3">
                  <div className={`p-2 rounded-md ${config.color} text-white`}>
                    <ModeIcon className="h-4 w-4" />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{config.label} Mode</span>
                      {isSelected && (
                        <Badge variant="secondary" className="text-xs">
                          Active
                        </Badge>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      {config.description}
                    </p>
                  </div>
                </div>
              </div>
            );
          })}
          <div className="pt-2 border-t">
            <p className="text-xs text-muted-foreground">
              {mode === 'patient' 
                ? '⚠️ Patient mode provides educational information only. Not for diagnosis.'
                : '🔬 Provider mode includes technical medical information for professionals.'
              }
            </p>
          </div>
        </div>
      </PopoverContent>
    </Popover>
  );
}