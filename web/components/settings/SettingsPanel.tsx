'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Slider } from '@/components/ui/slider';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { AlertCircle, Save, RotateCcw, Zap, Shield, Brain, Eye, Search, ChevronDown, ChevronRight } from 'lucide-react';
import { toast } from 'sonner';
import { Checkbox } from '@/components/ui/checkbox';
import { ScrollArea } from '@/components/ui/scroll-area';

interface SettingsPanelProps {
  sessionId: string;
}

export function SettingsPanel({ sessionId }: SettingsPanelProps) {
  const readonly = true; // Set to true to make all settings read-only
  const [defaultTrustedDomains, setDefaultTrustedDomains] = useState<string[]>([]);
  const [settings, setSettings] = useState({
    // Safety Settings
    enable_input_guardrails: true,
    enable_output_guardrails: false,
    guardrail_mode: 'llm',
    
    // Performance Settings
    enable_streaming: true,
    max_web_searches: 1,
    max_web_fetches: 2,
    response_timeout: 30,
    
    // Content Settings
    enable_trusted_domains: true,
    custom_trusted_domains: [] as string[],
    blocked_domains: [] as string[],
    include_citations: 'always',
    response_detail_level: 'standard',
    show_confidence_scores: false,
    
    // Model Settings
    model: 'claude-3-5-sonnet-20241022',
    temperature: 0.3,
    max_tokens: 1000,
    
    // Display Settings
    show_tool_calls: false,
    show_response_timing: false,
    markdown_rendering: true,
  });

  const [customDomain, setCustomDomain] = useState('');
  const [isDirty, setIsDirty] = useState(false);
  const [domainSearchQuery, setDomainSearchQuery] = useState('');
  const [expandedDomainCategories, setExpandedDomainCategories] = useState<Set<string>>(new Set());

  // Load settings on mount
  useEffect(() => {
    loadSettings();
  }, [sessionId]);

  const loadSettings = async () => {
    try {
      const response = await fetch(`/api/sessions/${sessionId}/settings`);
      if (response.ok) {
        const data = await response.json();
        if (data.settings && Object.keys(data.settings).length > 0) {
          setSettings(prev => ({ ...prev, ...data.settings }));
        }
        if (data.default_trusted_domains) {
          setDefaultTrustedDomains(data.default_trusted_domains);
        }
      }
    } catch (error) {
      console.error('Failed to load settings:', error);
    }
  };

  const saveSettings = async () => {
    try {
      const response = await fetch(`/api/sessions/${sessionId}/settings`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings),
      });
      
      if (response.ok) {
        toast.success('Settings saved successfully');
        setIsDirty(false);
      } else {
        toast.error('Failed to save settings');
      }
    } catch (error) {
      console.error('Failed to save settings:', error);
      toast.error('Failed to save settings');
    }
  };

  const resetToDefaults = () => {
    setSettings({
      enable_input_guardrails: true,
      enable_output_guardrails: false,
      guardrail_mode: 'llm',
      enable_streaming: true,
      max_web_searches: 1,
      max_web_fetches: 2,
      response_timeout: 30,
      enable_trusted_domains: true,
      custom_trusted_domains: [],
      blocked_domains: [],
      include_citations: 'always',
      response_detail_level: 'standard',
      show_confidence_scores: false,
      model: 'claude-3-5-sonnet-20241022',
      temperature: 0.3,
      max_tokens: 1000,
      show_tool_calls: false,
      show_response_timing: false,
      markdown_rendering: true,
    });
    setIsDirty(true);
    toast.info('Settings reset to defaults');
  };

  const updateSetting = (key: string, value: any) => {
    setSettings(prev => ({ ...prev, [key]: value }));
    setIsDirty(true);
  };

  const addCustomDomain = () => {
    if (customDomain && !settings.custom_trusted_domains.includes(customDomain)) {
      updateSetting('custom_trusted_domains', [...settings.custom_trusted_domains, customDomain]);
      setCustomDomain('');
    }
  };

  const removeCustomDomain = (domain: string) => {
    updateSetting('custom_trusted_domains', settings.custom_trusted_domains.filter(d => d !== domain));
  };

  return (
    <Card className="w-full max-w-4xl mx-auto">
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>Session Settings (Read-Only)</span>
          <Badge variant="secondary">View Only</Badge>
        </CardTitle>
        <CardDescription>
          Current configuration for the AI assistant (settings are controlled by administrators)
        </CardDescription>
      </CardHeader>
      
      <CardContent>
        <Tabs defaultValue="safety" className="w-full">
          <TabsList className="flex w-full">
            <TabsTrigger value="safety" className="flex-1">
              <Shield className="h-4 w-4 mr-1" />
              Safety
            </TabsTrigger>
            <TabsTrigger value="performance" className="flex-1">
              <Zap className="h-4 w-4 mr-1" />
              Performance
            </TabsTrigger>
            <TabsTrigger value="model" className="flex-1">
              <Brain className="h-4 w-4 mr-1" />
              Model
            </TabsTrigger>
            <TabsTrigger value="display" className="flex-1">
              <Eye className="h-4 w-4 mr-1" />
              Display
            </TabsTrigger>
          </TabsList>

          <TabsContent value="safety" className="space-y-6 mt-6">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <Label htmlFor="input-guardrails">Input Guardrails</Label>
                  <p className="text-sm text-muted-foreground">
                    Check queries for emergencies and unsafe content before processing
                  </p>
                </div>
                <Switch
                  id="input-guardrails"
                  checked={settings.enable_input_guardrails}
                  onCheckedChange={(checked) => updateSetting('enable_input_guardrails', checked)}
                  disabled={readonly}
                />
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <Label htmlFor="output-guardrails">Output Guardrails</Label>
                  <p className="text-sm text-muted-foreground">
                    Check and modify responses for safety (disables streaming)
                  </p>
                </div>
                <Switch
                  id="output-guardrails"
                  checked={settings.enable_output_guardrails}
                  onCheckedChange={(checked) => updateSetting('enable_output_guardrails', checked)}
                  disabled={readonly}
                />
              </div>

              {settings.enable_output_guardrails && (
                <div className="pl-4 py-2 border-l-2 border-yellow-500 bg-yellow-50 dark:bg-yellow-950/20">
                  <div className="flex items-start gap-2">
                    <AlertCircle className="h-4 w-4 text-yellow-600 mt-0.5" />
                    <p className="text-sm text-yellow-800 dark:text-yellow-200">
                      Output guardrails will disable streaming for better safety checks
                    </p>
                  </div>
                </div>
              )}

              <div>
                <Label htmlFor="guardrail-mode">Guardrail Mode</Label>
                <Select value={settings.guardrail_mode} onValueChange={(value) => updateSetting('guardrail_mode', value)} disabled={readonly}>
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="regex">Regex (Fast)</SelectItem>
                    <SelectItem value="llm">LLM (Smart)</SelectItem>
                    <SelectItem value="hybrid">Hybrid (Best)</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-sm text-muted-foreground mt-1">
                  How to check for safety violations
                </p>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label>Trusted Domains</Label>
                  <Switch
                    checked={settings.enable_trusted_domains}
                    onCheckedChange={(checked) => updateSetting('enable_trusted_domains', checked)}
                    disabled={readonly}
                  />
                </div>
                {settings.enable_trusted_domains && (
                  <div className="space-y-4">
                    {/* Search trusted domains */}
                    <div className="relative">
                      <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                      <Input
                        placeholder="Search trusted domains..."
                        value={domainSearchQuery}
                        onChange={(e) => setDomainSearchQuery(e.target.value)}
                        className="pl-8"
                        disabled={readonly}
                      />
                    </div>
                    
                    {/* Default trusted domains list */}
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <Label className="text-sm">Default Trusted Domains ({defaultTrustedDomains.length})</Label>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            const allExpanded = expandedDomainCategories.has('default');
                            if (allExpanded) {
                              setExpandedDomainCategories(new Set());
                            } else {
                              setExpandedDomainCategories(new Set(['default']));
                            }
                          }}
                        >
                          {expandedDomainCategories.has('default') ? (
                            <>
                              <ChevronDown className="h-4 w-4 mr-1" />
                              Hide
                            </>
                          ) : (
                            <>
                              <ChevronRight className="h-4 w-4 mr-1" />
                              Show
                            </>
                          )}
                        </Button>
                      </div>
                      
                      {expandedDomainCategories.has('default') && (
                        <Card className="p-3">
                          <ScrollArea className="h-64">
                            <div className="space-y-1">
                              {defaultTrustedDomains
                                .filter(domain => 
                                  domainSearchQuery === '' || 
                                  domain.toLowerCase().includes(domainSearchQuery.toLowerCase())
                                )
                                .map((domain) => {
                                  const isBlocked = settings.blocked_domains.includes(domain);
                                  return (
                                    <div key={domain} className="flex items-center space-x-2 py-1">
                                      <Checkbox
                                        id={`domain-${domain}`}
                                        checked={!isBlocked}
                                        disabled={readonly}
                                        onCheckedChange={(checked) => {
                                          if (checked) {
                                            // Remove from blocked list
                                            updateSetting('blocked_domains', 
                                              settings.blocked_domains.filter(d => d !== domain)
                                            );
                                          } else {
                                            // Add to blocked list
                                            updateSetting('blocked_domains', 
                                              [...settings.blocked_domains, domain]
                                            );
                                          }
                                        }}
                                      />
                                      <label
                                        htmlFor={`domain-${domain}`}
                                        className={`text-sm cursor-pointer ${
                                          isBlocked ? 'text-muted-foreground line-through' : ''
                                        }`}
                                      >
                                        {domain}
                                      </label>
                                    </div>
                                  );
                                })}
                            </div>
                          </ScrollArea>
                        </Card>
                      )}
                    </div>
                    
                    {/* Custom domains */}
                    <div className="space-y-2">
                      <Label className="text-sm">Custom Trusted Domains</Label>
                      <div className="flex gap-2">
                        <Input
                          placeholder="Add custom domain (e.g., example.com)"
                          value={customDomain}
                          onChange={(e) => setCustomDomain(e.target.value)}
                          onKeyDown={(e) => e.key === 'Enter' && addCustomDomain()}
                          disabled={readonly}
                        />
                        <Button size="sm" onClick={addCustomDomain} disabled={readonly}>Add</Button>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {settings.custom_trusted_domains.map((domain) => (
                          <Badge key={domain} variant="secondary" className="cursor-pointer"
                            onClick={() => removeCustomDomain(domain)}>
                            {domain} ×
                          </Badge>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Show blocked domains summary */}
              {settings.blocked_domains.length > 0 && (
                <div className="space-y-2">
                  <Label className="text-sm">Blocked Domains ({settings.blocked_domains.length})</Label>
                  <div className="flex flex-wrap gap-2">
                    {settings.blocked_domains.map((domain) => (
                      <Badge key={domain} variant="destructive" className="cursor-pointer"
                        onClick={() => updateSetting('blocked_domains', 
                          settings.blocked_domains.filter(d => d !== domain)
                        )}>
                        {domain} ×
                      </Badge>
                    ))}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    These domains are blocked from web searches. Click to unblock.
                  </p>
                </div>
              )}
            </div>
          </TabsContent>

          <TabsContent value="performance" className="space-y-6 mt-6">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <Label htmlFor="streaming">Enable Streaming</Label>
                  <p className="text-sm text-muted-foreground">
                    Show responses as they&apos;re generated (faster perceived speed)
                  </p>
                </div>
                <Switch
                  id="streaming"
                  checked={settings.enable_streaming}
                  onCheckedChange={(checked) => updateSetting('enable_streaming', checked)}
                  disabled={readonly || settings.enable_output_guardrails}
                />
              </div>

              <div>
                <Label htmlFor="web-searches">Max Web Searches: {settings.max_web_searches}</Label>
                <Slider
                  id="web-searches"
                  min={0}
                  max={5}
                  step={1}
                  value={[settings.max_web_searches]}
                  onValueChange={([value]) => updateSetting('max_web_searches', value)}
                  className="mt-2"
                  disabled={readonly}
                />
                <p className="text-sm text-muted-foreground mt-1">
                  Number of web searches per query (fewer = faster)
                </p>
              </div>

              <div>
                <Label htmlFor="web-fetches">Max Web Fetches: {settings.max_web_fetches}</Label>
                <Slider
                  id="web-fetches"
                  min={0}
                  max={10}
                  step={1}
                  value={[settings.max_web_fetches]}
                  onValueChange={([value]) => updateSetting('max_web_fetches', value)}
                  className="mt-2"
                  disabled={readonly}
                />
                <p className="text-sm text-muted-foreground mt-1">
                  Number of pages to fetch per query
                </p>
              </div>

              <div>
                <Label htmlFor="timeout">Response Timeout: {settings.response_timeout}s</Label>
                <Slider
                  id="timeout"
                  min={10}
                  max={60}
                  step={5}
                  value={[settings.response_timeout]}
                  onValueChange={([value]) => updateSetting('response_timeout', value)}
                  className="mt-2"
                  disabled={readonly}
                />
              </div>

              <div>
                <Label htmlFor="detail-level">Response Detail Level</Label>
                <Select value={settings.response_detail_level} onValueChange={(value) => updateSetting('response_detail_level', value)} disabled={readonly}>
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="brief">Brief</SelectItem>
                    <SelectItem value="standard">Standard</SelectItem>
                    <SelectItem value="comprehensive">Comprehensive</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label htmlFor="citations">Include Citations</Label>
                <Select value={settings.include_citations} onValueChange={(value) => updateSetting('include_citations', value)} disabled={readonly}>
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="always">Always</SelectItem>
                    <SelectItem value="auto">Auto</SelectItem>
                    <SelectItem value="never">Never</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="model" className="space-y-6 mt-6">
            <div className="space-y-4">
              <div>
                <Label htmlFor="model">AI Model</Label>
                <Select value={settings.model} onValueChange={(value) => updateSetting('model', value)} disabled={readonly}>
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="claude-3-5-sonnet-20241022">Claude 3.5 Sonnet (Fast)</SelectItem>
                    <SelectItem value="claude-opus-4-1-20250805">Claude 4 Opus (Smart)</SelectItem>
                    <SelectItem value="claude-sonnet-4-20250514">Claude 4 Sonnet (Balanced)</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-sm text-muted-foreground mt-1">
                  Choose between speed and capability
                </p>
              </div>

              <div>
                <Label htmlFor="temperature">Temperature: {settings.temperature.toFixed(1)}</Label>
                <Slider
                  id="temperature"
                  min={0}
                  max={1}
                  step={0.1}
                  value={[settings.temperature]}
                  onValueChange={([value]) => updateSetting('temperature', value)}
                  className="mt-2"
                  disabled={readonly}
                />
                <p className="text-sm text-muted-foreground mt-1">
                  Lower = more focused, Higher = more creative
                </p>
              </div>

              <div>
                <Label htmlFor="max-tokens">Max Response Length: {settings.max_tokens}</Label>
                <Slider
                  id="max-tokens"
                  min={500}
                  max={2000}
                  step={100}
                  value={[settings.max_tokens]}
                  onValueChange={([value]) => updateSetting('max_tokens', value)}
                  className="mt-2"
                  disabled={readonly}
                />
                <p className="text-sm text-muted-foreground mt-1">
                  Maximum tokens in response
                </p>
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <Label htmlFor="confidence">Show Confidence Scores</Label>
                  <p className="text-sm text-muted-foreground">
                    Display confidence levels for medical information
                  </p>
                </div>
                <Switch
                  id="confidence"
                  checked={settings.show_confidence_scores}
                  onCheckedChange={(checked) => updateSetting('show_confidence_scores', checked)}
                  disabled={readonly}
                />
              </div>
            </div>
          </TabsContent>

          <TabsContent value="display" className="space-y-6 mt-6">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <Label htmlFor="tool-calls">Show Tool Calls</Label>
                  <p className="text-sm text-muted-foreground">
                    Display web searches and fetches in chat
                  </p>
                </div>
                <Switch
                  id="tool-calls"
                  checked={settings.show_tool_calls}
                  onCheckedChange={(checked) => updateSetting('show_tool_calls', checked)}
                  disabled={readonly}
                />
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <Label htmlFor="timing">Show Response Timing</Label>
                  <p className="text-sm text-muted-foreground">
                    Display how long responses take
                  </p>
                </div>
                <Switch
                  id="timing"
                  checked={settings.show_response_timing}
                  onCheckedChange={(checked) => updateSetting('show_response_timing', checked)}
                  disabled={readonly}
                />
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <Label htmlFor="markdown">Markdown Rendering</Label>
                  <p className="text-sm text-muted-foreground">
                    Format responses with rich text
                  </p>
                </div>
                <Switch
                  id="markdown"
                  checked={settings.markdown_rendering}
                  onCheckedChange={(checked) => updateSetting('markdown_rendering', checked)}
                  disabled={readonly}
                />
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}