/**
 * Trusted Domains Configuration
 * Loads the comprehensive list of 97 trusted medical domains from domains.yaml
 */

import { readFileSync } from 'fs';
import { join } from 'path';
import yaml from 'js-yaml';

interface DomainsConfig {
  trusted_domains: string[];
  categories?: {
    [category: string]: string[];
  };
}

export class TrustedDomains {
  private static instance: TrustedDomains;
  private domains: string[] = [];
  private categories: { [category: string]: string[] } = {};

  private constructor() {
    this.loadDomains();
  }

  static getInstance(): TrustedDomains {
    if (!TrustedDomains.instance) {
      TrustedDomains.instance = new TrustedDomains();
    }
    return TrustedDomains.instance;
  }

  private loadDomains(): void {
    try {
      const domainsPath = join(process.cwd(), '..', 'src', 'config', 'domains.yaml');
      const yamlContent = readFileSync(domainsPath, 'utf8');
      const config = yaml.load(yamlContent) as DomainsConfig;
      
      this.domains = config.trusted_domains || [];
      this.categories = config.categories || {};
      
      console.log(`Loaded ${this.domains.length} trusted medical domains`);
    } catch (error) {
      console.warn('Failed to load domains.yaml, using fallback list:', error);
      this.loadFallbackDomains();
    }
  }

  private loadFallbackDomains(): void {
    // Fallback list in case YAML loading fails
    this.domains = [
      // Canadian Authorities
      'ontario.ca', 'publichealthontario.ca', 'ontariohealth.ca', 'cpso.on.ca',
      'canada.ca', 'phac-aspc.gc.ca', 'cma.ca', 'cmaj.ca',
      
      // Major US Medical Centers
      'mayoclinic.org', 'clevelandclinic.org', 'hopkinsmedicine.org',
      'massgeneral.org', 'stanfordhealthcare.org', 'ucsfhealth.org',
      
      // Medical Journals
      'nejm.org', 'thelancet.com', 'jamanetwork.com', 'bmj.com',
      'nature.com', 'pubmed.ncbi.nlm.nih.gov',
      
      // Global Health Organizations
      'who.int', 'cdc.gov', 'nih.gov', 'nhs.uk', 'fda.gov',
      
      // Evidence-Based Resources
      'uptodate.com', 'cochranelibrary.com', 'clinicaltrials.gov',
      
      // Canadian Disease Organizations
      'diabetes.ca', 'heartandstroke.ca', 'cancer.ca'
    ];
  }

  /**
   * Check if a domain is trusted
   */
  isTrusted(domain: string): boolean {
    if (!domain) return false;
    
    const normalizedDomain = domain.toLowerCase().replace('www.', '');
    
    return this.domains.some(trustedDomain => 
      normalizedDomain === trustedDomain.toLowerCase() ||
      normalizedDomain.endsWith('.' + trustedDomain.toLowerCase()) ||
      trustedDomain.toLowerCase().includes(normalizedDomain)
    );
  }

  /**
   * Get all trusted domains
   */
  getAllDomains(): string[] {
    return [...this.domains];
  }

  /**
   * Get domains by category
   */
  getDomainsByCategory(category: string): string[] {
    return this.categories[category] || [];
  }

  /**
   * Get all categories
   */
  getCategories(): string[] {
    return Object.keys(this.categories);
  }

  /**
   * Get trust level for a domain
   */
  getTrustLevel(domain: string): 'trusted' | 'unknown' {
    return this.isTrusted(domain) ? 'trusted' : 'unknown';
  }

  /**
   * Get category for a domain
   */
  getDomainCategory(domain: string): string | null {
    const normalizedDomain = domain.toLowerCase().replace('www.', '');
    
    for (const [category, domains] of Object.entries(this.categories)) {
      if (domains.some(trustedDomain => 
        normalizedDomain === trustedDomain.toLowerCase() ||
        normalizedDomain.endsWith('.' + trustedDomain.toLowerCase())
      )) {
        return category;
      }
    }
    
    return null;
  }

  /**
   * Find potential matches for a domain
   */
  findSimilarDomains(domain: string, threshold = 0.7): string[] {
    const normalizedDomain = domain.toLowerCase().replace('www.', '');
    const matches: string[] = [];
    
    for (const trustedDomain of this.domains) {
      const similarity = this.calculateSimilarity(normalizedDomain, trustedDomain.toLowerCase());
      if (similarity >= threshold) {
        matches.push(trustedDomain);
      }
    }
    
    return matches.sort((a, b) => {
      const simA = this.calculateSimilarity(normalizedDomain, a.toLowerCase());
      const simB = this.calculateSimilarity(normalizedDomain, b.toLowerCase());
      return simB - simA;
    });
  }

  /**
   * Simple string similarity calculation
   */
  private calculateSimilarity(str1: string, str2: string): number {
    const longer = str1.length > str2.length ? str1 : str2;
    const shorter = str1.length > str2.length ? str2 : str1;
    
    if (longer.length === 0) return 1.0;
    
    const editDistance = this.calculateEditDistance(longer, shorter);
    return (longer.length - editDistance) / longer.length;
  }

  /**
   * Calculate Levenshtein distance
   */
  private calculateEditDistance(str1: string, str2: string): number {
    const matrix = Array(str2.length + 1).fill(null).map(() => 
      Array(str1.length + 1).fill(null)
    );
    
    for (let i = 0; i <= str1.length; i++) matrix[0][i] = i;
    for (let j = 0; j <= str2.length; j++) matrix[j][0] = j;
    
    for (let j = 1; j <= str2.length; j++) {
      for (let i = 1; i <= str1.length; i++) {
        const indicator = str1[i - 1] === str2[j - 1] ? 0 : 1;
        matrix[j][i] = Math.min(
          matrix[j][i - 1] + 1,
          matrix[j - 1][i] + 1,
          matrix[j - 1][i - 1] + indicator
        );
      }
    }
    
    return matrix[str2.length][str1.length];
  }

  /**
   * Validate domain format
   */
  isValidDomainFormat(domain: string): boolean {
    const domainPattern = /^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$/;
    return domainPattern.test(domain);
  }

  /**
   * Extract domain from URL
   */
  extractDomain(url: string): string {
    try {
      return new URL(url).hostname.replace('www.', '');
    } catch {
      // Try to extract domain from non-URL strings
      const domainMatch = url.match(/(?:https?:\/\/)?(?:www\.)?([^\/\s]+)/);
      return domainMatch ? domainMatch[1] : url;
    }
  }
}