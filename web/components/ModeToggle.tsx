'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Stethoscope, Users, ChevronDown, Lock, AlertCircle, Eye, EyeOff } from 'lucide-react';

export type AssistantMode = 'patient' | 'provider';

interface ModeToggleProps {
  onModeChange?: (mode: AssistantMode) => void;
  defaultMode?: AssistantMode;
}

export function ModeToggle({ onModeChange, defaultMode = 'patient' }: ModeToggleProps) {
  const [mode, setMode] = useState<AssistantMode>(defaultMode);
  const [isOpen, setIsOpen] = useState(false);
  const [showPasswordDialog, setShowPasswordDialog] = useState(false);
  const [password, setPassword] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [hasProviderAccess, setHasProviderAccess] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  useEffect(() => {
    // Load mode from localStorage on mount
    const savedMode = localStorage.getItem('assistantMode') as AssistantMode;
    const savedAccess = localStorage.getItem('providerAccess') === 'true';
    
    if (savedAccess) {
      setHasProviderAccess(true);
    }
    
    if (savedMode && ['patient', 'provider'].includes(savedMode)) {
      // Only set provider mode if user has access
      if (savedMode === 'provider' && !savedAccess) {
        setMode('patient');
        localStorage.setItem('assistantMode', 'patient');
        onModeChange?.('patient');
      } else {
        setMode(savedMode);
        onModeChange?.(savedMode);
      }
    }
  }, []);

  const handleModeChange = (newMode: AssistantMode) => {
    // If switching to provider mode and no access, show password dialog
    if (newMode === 'provider' && !hasProviderAccess) {
      setShowPasswordDialog(true);
      setPassword('');
      setPasswordError('');
      setShowPassword(false);
      return;
    }
    
    setMode(newMode);
    localStorage.setItem('assistantMode', newMode);
    onModeChange?.(newMode);
    setIsOpen(false);
  };

  const handlePasswordSubmit = () => {
    const correctPassword = 'iunderstandthisisaresearchproject';
    
    if (password === correctPassword) {
      // Grant access
      setHasProviderAccess(true);
      localStorage.setItem('providerAccess', 'true');
      
      // Switch to provider mode
      setMode('provider');
      localStorage.setItem('assistantMode', 'provider');
      onModeChange?.('provider');
      
      // Close dialogs
      setShowPasswordDialog(false);
      setIsOpen(false);
      setPassword('');
      setPasswordError('');
    } else {
      setPasswordError('Incorrect password. Please try again.');
    }
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
    <>
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

    {/* Password Dialog for Provider Mode */}
    <Dialog open={showPasswordDialog} onOpenChange={setShowPasswordDialog}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Lock className="h-5 w-5" />
            Provider Mode Access
          </DialogTitle>
          <DialogDescription>
            Provider mode contains clinical information intended for healthcare professionals.
            Please enter the access password to continue.
          </DialogDescription>
        </DialogHeader>
        
        <div className="grid gap-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <div className="relative">
              <Input
                id="password"
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  setPasswordError('');
                }}
                placeholder="Enter password..."
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    handlePasswordSubmit();
                  }
                }}
                className="pr-10"
              />
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                onClick={() => setShowPassword(!showPassword)}
              >
                {showPassword ? (
                  <EyeOff className="h-4 w-4 text-muted-foreground" />
                ) : (
                  <Eye className="h-4 w-4 text-muted-foreground" />
                )}
              </Button>
            </div>
            {passwordError && (
              <div className="flex items-center gap-2 text-sm text-red-600">
                <AlertCircle className="h-4 w-4" />
                {passwordError}
              </div>
            )}
          </div>
          
          <div className="bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-800 rounded-lg p-3">
            <p className="text-xs text-blue-700 dark:text-blue-300">
              <strong>Note:</strong> This is a research project. Provider mode should only be used 
              by those who understand this is experimental software not intended for real clinical use.
            </p>
          </div>
        </div>
        
        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => {
              setShowPasswordDialog(false);
              setPassword('');
              setPasswordError('');
              setShowPassword(false);
            }}
          >
            Cancel
          </Button>
          <Button
            onClick={handlePasswordSubmit}
            disabled={!password}
          >
            <Lock className="h-4 w-4 mr-2" />
            Unlock Provider Mode
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
    </>
  );
}