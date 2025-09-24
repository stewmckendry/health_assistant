"""
Conflict detection and resolution for Dr. OFF responses.
Identifies and handles conflicts between SQL and vector evidence.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ConflictInfo:
    """Information about a detected conflict."""
    field: str
    sql_value: Any
    vector_value: Any
    resolution: str
    severity: str  # 'high', 'medium', 'low'


class ConflictDetector:
    """Detect conflicts between SQL and vector evidence."""
    
    @staticmethod
    def detect_conflicts(
        sql_data: Dict[str, Any],
        vector_data: Dict[str, Any],
        critical_fields: List[str] = None
    ) -> List[ConflictInfo]:
        """
        Detect conflicts between SQL and vector data.
        
        Args:
            sql_data: Data from SQL query
            vector_data: Data from vector search
            critical_fields: Fields that are critical for accuracy
        
        Returns:
            List of detected conflicts
        """
        conflicts = []
        critical_fields = critical_fields or []
        
        # Check for conflicts in common fields
        for field in set(sql_data.keys()) & set(vector_data.keys()):
            sql_val = sql_data[field]
            vec_val = vector_data[field]
            
            if ConflictDetector._values_conflict(sql_val, vec_val):
                severity = 'high' if field in critical_fields else 'medium'
                
                conflict = ConflictInfo(
                    field=field,
                    sql_value=sql_val,
                    vector_value=vec_val,
                    resolution=ConflictDetector._suggest_resolution(field, sql_val, vec_val),
                    severity=severity
                )
                conflicts.append(conflict)
        
        return conflicts
    
    @staticmethod
    def _values_conflict(val1: Any, val2: Any) -> bool:
        """
        Check if two values are in conflict.
        
        Args:
            val1: First value
            val2: Second value
        
        Returns:
            True if values conflict
        """
        # Handle None values
        if val1 is None or val2 is None:
            return False
        
        # Handle boolean conflicts
        if isinstance(val1, bool) and isinstance(val2, bool):
            return val1 != val2
        
        # Handle numeric conflicts (with tolerance)
        if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
            tolerance = 0.01  # 1% tolerance
            return abs(val1 - val2) > max(abs(val1), abs(val2)) * tolerance
        
        # Handle string conflicts (case-insensitive)
        if isinstance(val1, str) and isinstance(val2, str):
            # Normalize strings for comparison
            norm1 = val1.lower().strip()
            norm2 = val2.lower().strip()
            
            # Check for semantic equivalence
            if ConflictDetector._semantically_equivalent(norm1, norm2):
                return False
            
            return norm1 != norm2
        
        # Handle list conflicts
        if isinstance(val1, list) and isinstance(val2, list):
            return set(val1) != set(val2)
        
        # Default: direct comparison
        return val1 != val2
    
    @staticmethod
    def _semantically_equivalent(str1: str, str2: str) -> bool:
        """
        Check if two strings are semantically equivalent.
        
        Args:
            str1: First string
            str2: Second string
        
        Returns:
            True if semantically equivalent
        """
        equivalences = [
            ("yes", "true", "eligible", "covered"),
            ("no", "false", "ineligible", "not covered"),
            ("mrp", "most responsible physician"),
            ("lu", "limited use"),
            ("ea", "exceptional access")
        ]
        
        for group in equivalences:
            if str1 in group and str2 in group:
                return True
        
        return False
    
    @staticmethod
    def _suggest_resolution(field: str, sql_val: Any, vec_val: Any) -> str:
        """
        Suggest how to resolve a conflict.
        
        Args:
            field: Field name with conflict
            sql_val: SQL value
            vec_val: Vector value
        
        Returns:
            Resolution suggestion
        """
        # Prefer SQL for structured data fields
        structured_fields = [
            "fee", "price", "din", "code", "percent", 
            "threshold", "max_contribution"
        ]
        
        # Prefer vector for narrative/policy fields
        narrative_fields = [
            "requirements", "documentation", "criteria",
            "exclusions", "eligibility", "description"
        ]
        
        if any(f in field.lower() for f in structured_fields):
            return f"Using SQL value ({sql_val}) - structured data more reliable"
        elif any(f in field.lower() for f in narrative_fields):
            return f"Using vector value ({vec_val}) - document context more complete"
        else:
            # Default to SQL for recency
            return f"Using SQL value ({sql_val}) - assuming more recent"


class ConflictResolver:
    """Resolve conflicts between evidence sources."""
    
    @staticmethod
    def resolve(
        conflicts: List[ConflictInfo],
        prefer_source: str = "sql"
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Resolve conflicts and return consolidated data.
        
        Args:
            conflicts: List of detected conflicts
            prefer_source: Preferred source ('sql' or 'vector')
        
        Returns:
            Tuple of (resolved_data, conflict_records)
        """
        resolved = {}
        conflict_records = []
        
        for conflict in conflicts:
            # Choose value based on preference and severity
            if conflict.severity == 'high':
                # For high severity, use suggested resolution
                if "SQL value" in conflict.resolution:
                    resolved[conflict.field] = conflict.sql_value
                else:
                    resolved[conflict.field] = conflict.vector_value
            else:
                # For lower severity, use preference
                if prefer_source == "sql":
                    resolved[conflict.field] = conflict.sql_value
                else:
                    resolved[conflict.field] = conflict.vector_value
            
            # Record the conflict for transparency
            conflict_records.append({
                "field": conflict.field,
                "sql_value": conflict.sql_value,
                "vector_value": conflict.vector_value,
                "resolution": conflict.resolution
            })
        
        return resolved, conflict_records
    
    @staticmethod
    def merge_without_conflicts(
        sql_data: Dict[str, Any],
        vector_data: Dict[str, Any],
        conflicts: List[ConflictInfo]
    ) -> Dict[str, Any]:
        """
        Merge SQL and vector data, excluding conflicted fields.
        
        Args:
            sql_data: Data from SQL
            vector_data: Data from vector
            conflicts: Detected conflicts
        
        Returns:
            Merged data without conflicts
        """
        merged = {}
        conflict_fields = {c.field for c in conflicts}
        
        # Add all non-conflicting SQL fields
        for field, value in sql_data.items():
            if field not in conflict_fields:
                merged[field] = value
        
        # Add all non-conflicting vector fields not in SQL
        for field, value in vector_data.items():
            if field not in conflict_fields and field not in merged:
                merged[field] = value
        
        return merged