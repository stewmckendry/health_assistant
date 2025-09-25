/**
 * Citation Extraction and Deduplication
 * Extracts citations from agent responses and manages deduplicated source lists
 */

import { Citation } from '@/types/agents';
import { v4 as uuidv4 } from 'uuid';
import { TrustedDomains } from './trusted-domains';

export interface ExtractionResult {
  citations: Citation[];
  cleanedText: string;
}

export class CitationExtractor {
  private static trustedDomains = TrustedDomains.getInstance();

  /**
   * Extract citations from agent response text
   */
  static extractFromText(responseText: string): ExtractionResult {
    const citations: Citation[] = [];
    let cleanedText = responseText;

    // Extract different citation formats
    const extractors = [
      this.extractMarkdownLinks,
      this.extractPlainUrls,
      this.extractSourceReferences,
      this.extractStructuredCitations
    ];

    extractors.forEach(extractor => {
      const result = extractor(cleanedText);
      citations.push(...result.citations);
      cleanedText = result.cleanedText;
    });

    // Deduplicate citations
    const deduplicatedCitations = this.deduplicateCitations(citations);

    return {
      citations: deduplicatedCitations,
      cleanedText
    };
  }

  /**
   * Extract markdown-style links [title](url)
   */
  private static extractMarkdownLinks(text: string): ExtractionResult {
    const citations: Citation[] = [];
    const markdownLinkPattern = /\[([^\]]+)\]\(([^)]+)\)/g;
    
    const cleanedText = text.replace(markdownLinkPattern, (match, title, url) => {
      const citation = this.createCitation(title, url, url);
      if (citation) {
        citations.push(citation);
        return title; // Replace with just the title
      }
      return match;
    });

    return { citations, cleanedText };
  }

  /**
   * Extract plain URLs from text
   */
  private static extractPlainUrls(text: string): ExtractionResult {
    const citations: Citation[] = [];
    const urlPattern = /https?:\/\/[^\s<>"{}|\\^`[\]]+/g;
    
    const cleanedText = text.replace(urlPattern, (url) => {
      const citation = this.createCitation(null, url, url);
      if (citation) {
        citations.push(citation);
        return `[${this.extractDomain(url)}]`; // Replace with domain reference
      }
      return url;
    });

    return { citations, cleanedText };
  }

  /**
   * Extract source references like "According to [Source Name]" or "Source: [Name]"
   */
  private static extractSourceReferences(text: string): ExtractionResult {
    const citations: Citation[] = [];
    let cleanedText = text;

    const patterns = [
      /(?:According to|Source:|Per|Based on)\s+([^.,:;]+?)(?:\s*\([^)]*\))?[.,:;]/gi,
      /\[([^\]]+)\]/g // Bracketed source names
    ];

    patterns.forEach(pattern => {
      cleanedText = cleanedText.replace(pattern, (match, source) => {
        if (source && source.length > 3 && source.length < 100) {
          // Try to find a URL for this source
          const url = this.guessUrlFromSource(source.trim());
          const citation = this.createCitation(source.trim(), source.trim(), url);
          if (citation) {
            citations.push(citation);
          }
        }
        return match;
      });
    });

    return { citations, cleanedText };
  }

  /**
   * Extract structured citations from agent responses
   */
  private static extractStructuredCitations(text: string): ExtractionResult {
    const citations: Citation[] = [];
    let cleanedText = text;

    // Look for structured citation patterns
    const structuredPattern = /(?:Source|Citation):\s*(.+?)(?:\n|$)/gi;
    
    cleanedText = cleanedText.replace(structuredPattern, (match, citationText) => {
      // Try to parse structured citation
      const parts = citationText.split(' - ');
      if (parts.length >= 2) {
        const title = parts[0].trim();
        const source = parts[1].trim();
        const url = parts[2]?.trim() || this.guessUrlFromSource(source);
        
        const citation = this.createCitation(title, source, url);
        if (citation) {
          citations.push(citation);
        }
      }
      return ''; // Remove citation line from text
    });

    return { citations, cleanedText };
  }

  /**
   * Create a citation object from extracted information
   */
  private static createCitation(
    title: string | null, 
    source: string, 
    url: string
  ): Citation | null {
    if (!source || source.length < 3) return null;

    const domain = this.extractDomain(url);
    const isTrusted = this.isTrustedDomain(domain);

    return {
      id: `citation_${uuidv4().substring(0, 8)}`,
      title: title || this.generateTitleFromSource(source),
      source: source,
      url: url,
      domain: domain,
      isTrusted: isTrusted,
      accessDate: new Date().toISOString()
    };
  }

  /**
   * Deduplicate citations by URL and title similarity
   */
  private static deduplicateCitations(citations: Citation[]): Citation[] {
    const seen = new Set<string>();
    const deduplicated: Citation[] = [];

    for (const citation of citations) {
      // Create deduplication key
      const key = this.createDeduplicationKey(citation);
      
      if (!seen.has(key)) {
        seen.add(key);
        deduplicated.push(citation);
      }
    }

    return deduplicated;
  }

  /**
   * Create a key for deduplication
   */
  private static createDeduplicationKey(citation: Citation): string {
    // Use URL if available, otherwise use normalized title + domain
    if (citation.url && citation.url.startsWith('http')) {
      return this.normalizeUrl(citation.url);
    }
    
    return `${this.normalizeText(citation.title)}_${citation.domain}`;
  }

  /**
   * Normalize URL for deduplication
   */
  private static normalizeUrl(url: string): string {
    try {
      const parsed = new URL(url);
      // Remove query params and fragments for deduplication
      return `${parsed.hostname}${parsed.pathname}`.toLowerCase();
    } catch {
      return url.toLowerCase();
    }
  }

  /**
   * Normalize text for comparison
   */
  private static normalizeText(text: string): string {
    return text.toLowerCase()
      .replace(/[^\w\s]/g, '')
      .replace(/\s+/g, '_');
  }

  /**
   * Extract domain from URL
   */
  private static extractDomain(url: string): string {
    return this.trustedDomains.extractDomain(url);
  }

  /**
   * Check if domain is trusted
   */
  private static isTrustedDomain(domain: string): boolean {
    return this.trustedDomains.isTrusted(domain);
  }

  /**
   * Guess URL from source name
   */
  private static guessUrlFromSource(source: string): string {
    const normalized = source.toLowerCase();
    
    // Common source name to URL mappings
    const mappings: Record<string, string> = {
      'mayo clinic': 'https://www.mayoclinic.org',
      'cdc': 'https://www.cdc.gov',
      'who': 'https://www.who.int',
      'nih': 'https://www.nih.gov',
      'cpso': 'https://www.cpso.on.ca',
      'ontario health': 'https://www.ontariohealth.ca',
      'public health ontario': 'https://www.publichealthontario.ca',
      'cleveland clinic': 'https://www.clevelandclinic.org',
      'johns hopkins': 'https://www.hopkinsmedicine.org',
      'harvard': 'https://www.harvard.edu',
      'stanford': 'https://www.stanford.edu'
    };

    for (const [key, url] of Object.entries(mappings)) {
      if (normalized.includes(key)) {
        return url;
      }
    }

    return source; // Return source as-is if no mapping found
  }

  /**
   * Generate title from source name
   */
  private static generateTitleFromSource(source: string): string {
    if (source.startsWith('http')) {
      const domain = this.extractDomain(source);
      return `Source from ${domain}`;
    }
    return source.length > 50 ? source.substring(0, 50) + '...' : source;
  }

  /**
   * Group citations by domain for display
   */
  static groupByDomain(citations: Citation[]): Array<{
    domain: string;
    citations: Citation[];
    isTrusted: boolean;
  }> {
    const groups = new Map<string, Citation[]>();

    citations.forEach(citation => {
      const domain = citation.domain;
      if (!groups.has(domain)) {
        groups.set(domain, []);
      }
      groups.get(domain)!.push(citation);
    });

    return Array.from(groups.entries())
      .map(([domain, citations]) => ({
        domain,
        citations,
        isTrusted: citations.some(c => c.isTrusted)
      }))
      .sort((a, b) => {
        // Sort trusted domains first
        if (a.isTrusted && !b.isTrusted) return -1;
        if (!a.isTrusted && b.isTrusted) return 1;
        // Then by citation count
        return b.citations.length - a.citations.length;
      });
  }
}