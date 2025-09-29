'use client';

import { Citation } from '@/types/agents';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { 
  ExternalLink, 
  BookOpen, 
  Shield, 
  Calendar,
  Link as LinkIcon,
  Globe,
  Copy,
  Check
} from 'lucide-react';
import { useState } from 'react';

interface CitationListProps {
  citations: Citation[];
  compact?: boolean;
}

export function CitationList({ citations, compact = false }: CitationListProps) {
  const [copiedUrl, setCopiedUrl] = useState<string | null>(null);

  const copyToClipboard = async (url: string) => {
    try {
      await navigator.clipboard.writeText(url);
      setCopiedUrl(url);
      setTimeout(() => setCopiedUrl(null), 2000);
    } catch (error) {
      console.error('Failed to copy to clipboard:', error);
    }
  };

  const getSourceTypeColor = (domain: string, isTrusted: boolean) => {
    if (!isTrusted) return 'gray';
    
    // Canadian sources
    if (domain.includes('ontario.ca') || domain.includes('cpso.on.ca') || domain.includes('publichealthontario.ca')) {
      return 'blue';
    }
    // Medical journals
    if (domain.includes('nejm.org') || domain.includes('thelancet.com') || domain.includes('jamanetwork.com')) {
      return 'purple';
    }
    // Health organizations
    if (domain.includes('who.int') || domain.includes('cdc.gov') || domain.includes('mayoclinic.org')) {
      return 'green';
    }
    return 'gray';
  };

  const formatDomain = (url: string) => {
    try {
      return new URL(url).hostname.replace('www.', '');
    } catch {
      return url;
    }
  };

  const groupCitationsByDomain = (citations: Citation[]) => {
    const grouped = citations.reduce((acc, citation) => {
      const domain = formatDomain(citation.url);
      if (!acc[domain]) {
        acc[domain] = [];
      }
      acc[domain].push(citation);
      return acc;
    }, {} as Record<string, Citation[]>);

    // Sort domains by trust level and citation count
    const sortedDomains = Object.keys(grouped).sort((a, b) => {
      const aIsTrusted = grouped[a].some(c => c.isTrusted);
      const bIsTrusted = grouped[b].some(c => c.isTrusted);
      
      if (aIsTrusted && !bIsTrusted) return -1;
      if (!aIsTrusted && bIsTrusted) return 1;
      
      return grouped[b].length - grouped[a].length;
    });

    return sortedDomains.map(domain => ({
      domain,
      citations: grouped[domain]
    }));
  };

  if (citations.length === 0) {
    return (
      <Card className="h-full">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-sm">
            <BookOpen className="h-4 w-4" />
            Citations
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center text-muted-foreground text-sm py-8">
            <BookOpen className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p>Citations will appear here as the agent responds</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const groupedCitations = groupCitationsByDomain(citations);
  const trustedCount = citations.filter(c => c.isTrusted).length;

  if (compact) {
    return (
      <div className="space-y-2">
        <div className="flex items-center gap-2 text-sm font-medium">
          <BookOpen className="h-4 w-4" />
          <span>Sources ({citations.length})</span>
          {trustedCount > 0 && (
            <Badge className="bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400 text-xs">
              <Shield className="h-3 w-3 mr-1" />
              {trustedCount} trusted
            </Badge>
          )}
        </div>
        <div className="space-y-1">
          {citations.slice(0, 5).map((citation, index) => (
            <div key={`compact-${index}-${citation.url}`} className="flex items-center gap-2 text-sm">
              <span className="text-muted-foreground">{index + 1}.</span>
              <a 
                href={citation.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary hover:underline truncate flex-1"
              >
                {citation.title || citation.source}
              </a>
              {citation.isTrusted && (
                <Shield className="h-3 w-3 text-green-500" />
              )}
            </div>
          ))}
          {citations.length > 5 && (
            <p className="text-xs text-muted-foreground">
              +{citations.length - 5} more sources
            </p>
          )}
        </div>
      </div>
    );
  }

  return (
    <Card className="h-full">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-2">
            <BookOpen className="h-4 w-4" />
            Citations ({citations.length})
          </div>
          {trustedCount > 0 && (
            <Badge className="bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400 text-xs">
              <Shield className="h-3 w-3 mr-1" />
              {trustedCount} trusted
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[calc(100%-4rem)]">
          <div className="space-y-4">
            {groupedCitations.map(({ domain, citations: domainCitations }, index) => (
              <div key={domain} className="space-y-2">
                {/* Domain Header */}
                <div className="flex items-center gap-2 pb-2 border-b border-border/50">
                  <Globe className="h-3 w-3 text-muted-foreground" />
                  <span className="text-xs font-medium text-muted-foreground">{domain}</span>
                  <Badge 
                    variant="outline" 
                    className={`text-xs text-${getSourceTypeColor(domain, domainCitations.some(c => c.isTrusted))}-600`}
                  >
                    {domainCitations.length}
                  </Badge>
                  {domainCitations.some(c => c.isTrusted) && (
                    <Shield className="h-3 w-3 text-green-500" />
                  )}
                </div>

                {/* Citations for this domain */}
                <div className="space-y-2">
                  {domainCitations.map((citation, citationIndex) => (
                    <div key={`${domain}-${citationIndex}-${citation.url}`} className="border rounded-lg p-3 space-y-2">
                      {/* Title and Link */}
                      <div className="flex items-start gap-2">
                        <span className="text-xs text-muted-foreground font-mono min-w-[1.5rem]">
                          {index + 1}.{citationIndex + 1}
                        </span>
                        <div className="flex-1 min-w-0">
                          <h4 className="text-sm font-medium line-clamp-2">
                            {citation.title || citation.source}
                          </h4>
                          <div className="flex items-center gap-2 mt-1">
                            <a 
                              href={citation.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-xs text-primary hover:underline flex items-center gap-1"
                            >
                              <ExternalLink className="h-3 w-3" />
                              Open source
                            </a>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-auto p-0 text-xs text-muted-foreground hover:text-foreground"
                              onClick={() => copyToClipboard(citation.url)}
                            >
                              {copiedUrl === citation.url ? (
                                <Check className="h-3 w-3" />
                              ) : (
                                <Copy className="h-3 w-3" />
                              )}
                            </Button>
                          </div>
                        </div>
                        {citation.isTrusted && (
                          <Badge className="bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400 text-xs">
                            Trusted
                          </Badge>
                        )}
                      </div>

                      {/* Snippet */}
                      {citation.snippet && (
                        <div className="text-xs text-muted-foreground bg-muted/50 rounded p-2">
                          &quot;{citation.snippet}&quot;
                        </div>
                      )}

                      {/* Metadata */}
                      <div className="flex items-center gap-3 text-xs text-muted-foreground">
                        {citation.publishedDate && (
                          <span className="flex items-center gap-1">
                            <Calendar className="h-3 w-3" />
                            {citation.publishedDate}
                          </span>
                        )}
                        <span className="flex items-center gap-1">
                          <LinkIcon className="h-3 w-3" />
                          Accessed: {new Date(citation.accessDate).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}