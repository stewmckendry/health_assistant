"""
Conflict resolution system for Dr. OPA responses.
Handles conflicts between different sources, versions, and guidance levels.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def resolve_conflicts(
    sql_results: List[Dict[str, Any]],
    vector_results: List[Dict[str, Any]]
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Resolve conflicts between SQL and vector search results.
    
    Args:
        sql_results: Results from SQL queries
        vector_results: Results from vector search
    
    Returns:
        Tuple of (resolved_data, conflicts_list)
    """
    conflicts = []
    resolved = {}
    
    # Create lookup maps
    sql_map = {r.get('document_id', r.get('section_id', str(i))): r 
               for i, r in enumerate(sql_results)}
    vector_map = {r.get('chunk_id', r.get('metadata', {}).get('section_id', str(i))): r 
                  for i, r in enumerate(vector_results)}
    
    # Find overlapping results
    common_ids = set(sql_map.keys()) & set(vector_map.keys())
    
    for doc_id in common_ids:
        sql_data = sql_map[doc_id]
        vector_data = vector_map[doc_id]
        
        # Check for conflicts in key fields
        conflict_fields = []
        
        # Check text content
        sql_text = sql_data.get('section_text', sql_data.get('text', ''))
        vector_text = vector_data.get('text', '')
        
        if sql_text and vector_text and sql_text[:100] != vector_text[:100]:
            conflict_fields.append('content')
        
        # Check metadata conflicts
        sql_meta = sql_data.get('metadata', {})
        vector_meta = vector_data.get('metadata', {})
        
        for field in ['effective_date', 'document_type', 'policy_level']:
            sql_val = sql_data.get(field) or sql_meta.get(field)
            vec_val = vector_meta.get(field)
            
            if sql_val and vec_val and str(sql_val) != str(vec_val):
                conflict_fields.append(field)
        
        if conflict_fields:
            # Record the conflict
            conflict = {
                'document_id': doc_id,
                'fields': conflict_fields,
                'sql_source': sql_data,
                'vector_source': vector_data,
                'resolution': 'SQL preferred for structured data'
            }
            conflicts.append(conflict)
            
            # Use SQL as authoritative for structured data
            resolved[doc_id] = sql_data
        else:
            # No conflict - merge the data
            merged = {**vector_data, **sql_data}
            resolved[doc_id] = merged
    
    # Add non-overlapping results
    for doc_id, data in sql_map.items():
        if doc_id not in common_ids:
            resolved[doc_id] = data
    
    for doc_id, data in vector_map.items():
        if doc_id not in common_ids:
            resolved[doc_id] = data
    
    return resolved, conflicts


class OPAConflictResolver:
    """Resolve conflicts specific to Ontario Practice Advice."""
    
    # Resolution strategies
    STRATEGIES = {
        "newest": "Use the most recent guidance",
        "highest_authority": "Use guidance from highest authority source",
        "most_restrictive": "Use the most restrictive/conservative guidance",
        "policy_over_advice": "Prefer policy expectations over advice"
    }
    
    @classmethod
    def resolve_version_conflict(
        cls,
        documents: List[Dict[str, Any]]
    ) -> Tuple[Dict[str, Any], str]:
        """
        Resolve conflicts between different versions of guidance.
        
        Args:
            documents: List of conflicting documents
        
        Returns:
            Tuple of (selected_document, resolution_reason)
        """
        if not documents:
            return {}, "No documents to resolve"
        
        if len(documents) == 1:
            return documents[0], "Single document - no conflict"
        
        # Sort by effective date (newest first)
        sorted_docs = sorted(
            documents,
            key=lambda d: d.get('effective_date', '1900-01-01'),
            reverse=True
        )
        
        # Check if newest is superseded
        newest = sorted_docs[0]
        if newest.get('is_superseded', False):
            # Find the non-superseded one
            for doc in sorted_docs:
                if not doc.get('is_superseded', False):
                    return doc, "Selected non-superseded document"
        
        return newest, "Selected most recent guidance"
    
    @classmethod
    def resolve_source_conflict(
        cls,
        sources: List[Dict[str, Any]],
        topic: str
    ) -> Tuple[Dict[str, Any], str]:
        """
        Resolve conflicts between different sources.
        
        Args:
            sources: List of sources with conflicting guidance
            topic: Topic in question
        
        Returns:
            Tuple of (selected_source, resolution_reason)
        """
        # Authority hierarchy for Ontario practice
        authority_order = {
            "cpso": 5,  # College of Physicians - highest for practice standards
            "ontario_health": 4,  # Provincial screening programs
            "pho": 3,  # Public Health Ontario
            "moh": 3,  # Ministry of Health
            "cep": 2,  # Centre for Effective Practice
            "other": 1
        }
        
        if not sources:
            return {}, "No sources to resolve"
        
        # Sort by authority
        sorted_sources = sorted(
            sources,
            key=lambda s: authority_order.get(s.get('source_org', 'other'), 1),
            reverse=True
        )
        
        highest = sorted_sources[0]
        
        # Special cases
        if topic and 'screening' in topic.lower():
            # Prefer Ontario Health for screening
            for source in sources:
                if source.get('source_org') == 'ontario_health':
                    return source, "Ontario Health authoritative for screening"
        
        if topic and ('ipac' in topic.lower() or 'infection' in topic.lower()):
            # Prefer PHO for infection control
            for source in sources:
                if source.get('source_org') == 'pho':
                    return source, "PHO authoritative for infection control"
        
        return highest, f"Highest authority source: {highest.get('source_org')}"
    
    @classmethod
    def resolve_policy_level_conflict(
        cls,
        items: List[Dict[str, Any]]
    ) -> Tuple[Dict[str, Any], str]:
        """
        Resolve conflicts between policy levels (expectations vs advice).
        
        Args:
            items: List of items with different policy levels
        
        Returns:
            Tuple of (selected_item, resolution_reason)
        """
        if not items:
            return {}, "No items to resolve"
        
        # Find expectations (mandatory)
        expectations = [i for i in items if i.get('policy_level') == 'expectation']
        if expectations:
            return expectations[0], "Policy expectation (mandatory) takes precedence"
        
        # Find advice
        advice = [i for i in items if i.get('policy_level') == 'advice']
        if advice:
            return advice[0], "Professional advice selected"
        
        # Return first item if no policy levels
        return items[0], "No policy levels specified"
    
    @classmethod
    def create_conflict_summary(
        cls,
        conflicts: List[Dict[str, Any]]
    ) -> str:
        """
        Create a human-readable summary of conflicts.
        
        Args:
            conflicts: List of conflict records
        
        Returns:
            Summary text
        """
        if not conflicts:
            return "No conflicts detected"
        
        summaries = []
        
        for conflict in conflicts:
            fields = conflict.get('fields', [])
            doc_id = conflict.get('document_id', 'Unknown')
            resolution = conflict.get('resolution', 'Resolved')
            
            if fields:
                field_str = ", ".join(fields)
                summaries.append(f"• {doc_id}: Conflict in {field_str} - {resolution}")
        
        if summaries:
            return "Conflicts resolved:\n" + "\n".join(summaries)
        
        return "Minor conflicts resolved using authoritative sources"