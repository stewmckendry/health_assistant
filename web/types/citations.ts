/**
 * Standardized Citation System Types
 * Used by all agents for consistent citation handling
 */

export type SourceType = 'policy' | 'guideline' | 'journal' | 'website' | 'database';
export type TrustLevel = 'trusted' | 'unverified';

/**
 * Standard Citation Model
 * Used across all agents for consistent citation structure
 */
export interface Citation {
  /** Unique identifier for this citation */
  id: string;
  
  /** Human-readable title of the source */
  title: string;
  
  /** Organization or publication name */
  source: string;
  
  /** Type of source document */
  source_type: SourceType;
  
  /** Direct URL to the source */
  url: string;
  
  /** Domain name (normalized, without www.) */
  domain: string;
  
  /** Whether this domain is in the 97 trusted sources */
  is_trusted: boolean;
  
  /** When this citation was retrieved (ISO timestamp) */
  access_date: string;
  
  /** Relevant excerpt from the source (optional) */
  snippet?: string;
  
  /** Relevance score to the original query (0.0-1.0) */
  relevance_score: number;
  
  /** Additional metadata for specific source types */
  metadata?: CitationMetadata;
}

/**
 * Optional metadata for citations
 */
export interface CitationMetadata {
  /** Section reference for policy documents */
  section?: string;
  
  /** Page number if available */
  page?: number;
  
  /** Effective date for policies/guidelines */
  effective_date?: string;
  
  /** Publication date for journals */
  published_date?: string;
  
  /** Authors for academic sources */
  authors?: string[];
  
  /** DOI for academic papers */
  doi?: string;
  
  /** Whether this document supersedes others */
  is_superseded?: boolean;
}

/**
 * Highlighted key point with supporting citations
 */
export interface Highlight {
  /** The key information point */
  point: string;
  
  /** Citations that support this point */
  citations: string[]; // Citation IDs
  
  /** Confidence level in this information (0.0-1.0) */
  confidence: number;
  
  /** Policy level for regulatory content */
  policy_level?: 'expectation' | 'advice' | 'guideline';
}

/**
 * Enhanced agent response with structured citations
 */
export interface AgentResponseWithCitations {
  /** Main text response */
  response: string;
  
  /** MCP tools that were executed */
  tool_calls: Array<{
    name: string;
    arguments: Record<string, any>;
    result?: any;
  }>;
  
  /** List of tool names used */
  tools_used: string[];
  
  /** Structured citations from all sources */
  citations: Citation[];
  
  /** Key points with their supporting citations */
  highlights: Highlight[];
  
  /** Overall confidence in the response (0.0-1.0) */
  confidence: number;
  
  /** Any errors encountered */
  error?: string;
}

/**
 * Citation group for UI display
 */
export interface CitationGroup {
  /** Domain name */
  domain: string;
  
  /** All citations from this domain */
  citations: Citation[];
  
  /** Whether any citation from this domain is trusted */
  is_trusted: boolean;
  
  /** Source type category */
  category: string;
}

/**
 * Citation validation result
 */
export interface CitationValidation {
  /** Whether the citation is valid */
  is_valid: boolean;
  
  /** Whether the URL is accessible */
  url_accessible: boolean;
  
  /** Trust level of the domain */
  trust_level: TrustLevel;
  
  /** Any validation warnings */
  warnings: string[];
  
  /** Suggested corrections if invalid */
  suggestions?: Partial<Citation>;
}

/**
 * Citation extraction result from text
 */
export interface CitationExtractionResult {
  /** Extracted citations */
  citations: Citation[];
  
  /** Original text with citation markers removed */
  cleaned_text: string;
  
  /** Extraction method used */
  extraction_method: 'structured' | 'markdown' | 'url' | 'reference';
}

/**
 * Citation deduplication strategies
 */
export type DeduplicationStrategy = 'url' | 'title_domain' | 'fuzzy_match';

/**
 * Citation sorting options
 */
export interface CitationSortOptions {
  /** Primary sort field */
  sort_by: 'relevance' | 'trust' | 'date' | 'source';
  
  /** Sort order */
  order: 'asc' | 'desc';
  
  /** Whether to prioritize trusted sources */
  prioritize_trusted: boolean;
}

/**
 * Citation filter options
 */
export interface CitationFilter {
  /** Filter by trust level */
  trust_level?: TrustLevel;
  
  /** Filter by source type */
  source_types?: SourceType[];
  
  /** Filter by minimum relevance score */
  min_relevance?: number;
  
  /** Filter by specific domains */
  domains?: string[];
  
  /** Filter by date range */
  date_range?: {
    start: string;
    end: string;
  };
}

/**
 * Citation display preferences
 */
export interface CitationDisplayOptions {
  /** Whether to show snippets */
  show_snippets: boolean;
  
  /** Whether to group by domain */
  group_by_domain: boolean;
  
  /** Maximum number of citations to show initially */
  initial_limit: number;
  
  /** Whether to auto-expand trusted sources */
  auto_expand_trusted: boolean;
  
  /** Whether to show relevance scores */
  show_relevance_scores: boolean;
}

/**
 * Citation analytics/metrics
 */
export interface CitationMetrics {
  /** Total number of citations */
  total_citations: number;
  
  /** Number of trusted citations */
  trusted_citations: number;
  
  /** Trust ratio (trusted/total) */
  trust_ratio: number;
  
  /** Average relevance score */
  avg_relevance: number;
  
  /** Number of unique domains */
  unique_domains: number;
  
  /** Most cited domains */
  top_domains: Array<{
    domain: string;
    count: number;
  }>;
}

/**
 * Citation event for streaming updates
 */
export interface CitationStreamEvent {
  /** Event type */
  type: 'citation_added' | 'citation_updated' | 'citation_removed';
  
  /** Citation data */
  citation: Citation;
  
  /** Timestamp of the event */
  timestamp: string;
  
  /** Source of the citation (which tool/agent) */
  source: string;
}