#!/usr/bin/env python3
"""
Utility script to view and inspect session logs.

Usage:
    python scripts/view_session_log.py <session_id>
    python scripts/view_session_log.py --list
    python scripts/view_session_log.py --latest
"""
import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.session_logging import read_session_log, format_session_log


def list_sessions(log_dir: str = "logs/sessions") -> None:
    """List all available session logs."""
    log_path = Path(log_dir)
    
    if not log_path.exists():
        print(f"Log directory {log_dir} does not exist")
        return
    
    session_files = list(log_path.glob("session_*.jsonl"))
    
    if not session_files:
        print("No session logs found")
        return
    
    # Group by session ID
    sessions = {}
    for file in session_files:
        # Extract session ID from filename
        parts = file.stem.split("_")
        if len(parts) >= 2:
            session_id = parts[1]
            if session_id not in sessions:
                sessions[session_id] = []
            sessions[session_id].append(file)
    
    print(f"\nFound {len(sessions)} sessions:\n")
    print(f"{'Session ID':<20} {'Files':<5} {'Latest File':<50}")
    print("-" * 75)
    
    for session_id, files in sorted(sessions.items()):
        latest_file = sorted(files)[-1]
        print(f"{session_id:<20} {len(files):<5} {latest_file.name:<50}")


def get_latest_session(log_dir: str = "logs/sessions") -> str:
    """Get the most recent session ID."""
    log_path = Path(log_dir)
    
    if not log_path.exists():
        raise FileNotFoundError(f"Log directory {log_dir} does not exist")
    
    session_files = list(log_path.glob("session_*.jsonl"))
    
    if not session_files:
        raise FileNotFoundError("No session logs found")
    
    # Sort by modification time
    latest_file = max(session_files, key=lambda f: f.stat().st_mtime)
    
    # Extract session ID
    parts = latest_file.stem.split("_")
    if len(parts) >= 2:
        return parts[1]
    
    raise ValueError(f"Could not extract session ID from {latest_file.name}")


def view_session(session_id: str, format: str = "formatted", stage: str = None) -> None:
    """
    View a specific session log.
    
    Args:
        session_id: Session ID to view
        format: Output format (formatted, json, raw)
        stage: Optional stage to filter by
    """
    try:
        if format == "formatted":
            print(format_session_log(session_id))
        else:
            entries = read_session_log(session_id)
            
            # Filter by stage if specified
            if stage:
                entries = [e for e in entries if e.get("stage") == stage.upper()]
            
            if format == "json":
                for entry in entries:
                    print(json.dumps(entry, indent=2))
                    print("-" * 40)
            else:  # raw
                for entry in entries:
                    print(json.dumps(entry))
                    
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)


def extract_stage_data(session_id: str, stage: str) -> None:
    """Extract specific stage data from a session."""
    try:
        entries = read_session_log(session_id)
        stage_entries = [e for e in entries if e.get("stage") == stage.upper()]
        
        if not stage_entries:
            print(f"No entries found for stage: {stage}")
            return
        
        print(f"\n{stage.upper()} Stage Data ({len(stage_entries)} entries):")
        print("=" * 60)
        
        for entry in stage_entries:
            sequence = entry.get("sequence", 0)
            timestamp = entry.get("timestamp", "")
            
            print(f"\n[{sequence:03d}] {timestamp}")
            print("-" * 40)
            
            # Show stage-specific data
            if stage.upper() == "API_CALL":
                if "api_request" in entry:
                    print("Messages:")
                    for msg in entry["api_request"].get("messages", []):
                        print(f"  {msg.get('role', 'unknown')}: {msg.get('content', '')[:100]}...")
                    if entry["api_request"].get("tools"):
                        print(f"Tools: {entry.get('tools_configured', [])}")
                        
            elif stage.upper() == "TOOL_CALL":
                print(f"Tool: {entry.get('tool_name', 'N/A')}")
                print(f"Type: {entry.get('tool_type', 'N/A')}")
                if entry.get("tool_input"):
                    print(f"Input: {json.dumps(entry['tool_input'], indent=2)}")
                    
            elif stage.upper() == "CITATIONS":
                for citation in entry.get("citations", []):
                    print(f"  - {citation.get('title', 'N/A')}")
                    print(f"    {citation.get('url', 'N/A')}")
                    
            elif stage.upper() == "OUTPUT_GUARDRAIL":
                print(f"Passes: {entry.get('passes_guardrails', True)}")
                if entry.get("violations"):
                    print(f"Violations: {', '.join(entry['violations'])}")
                if entry.get("modifications"):
                    print("Response was modified:")
                    print(f"  Original: {entry['modifications']['original_preview']}")
                    print(f"  Modified: {entry['modifications']['modified_preview']}")
                    
            else:
                # Show all non-metadata fields
                for key, value in entry.items():
                    if key not in ["stage", "sequence", "session_id", "timestamp"]:
                        if isinstance(value, (dict, list)):
                            print(f"{key}: {json.dumps(value, indent=2)}")
                        else:
                            print(f"{key}: {value}")
                            
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="View and inspect session logs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all sessions
  python scripts/view_session_log.py --list
  
  # View latest session
  python scripts/view_session_log.py --latest
  
  # View specific session (formatted)
  python scripts/view_session_log.py abc123
  
  # View session as JSON
  python scripts/view_session_log.py abc123 --format json
  
  # View only specific stage
  python scripts/view_session_log.py abc123 --stage api_call
  
  # Extract citations from session
  python scripts/view_session_log.py abc123 --extract citations
"""
    )
    
    parser.add_argument(
        "session_id",
        nargs="?",
        help="Session ID to view"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available sessions"
    )
    parser.add_argument(
        "--latest",
        action="store_true",
        help="View the most recent session"
    )
    parser.add_argument(
        "--format",
        choices=["formatted", "json", "raw"],
        default="formatted",
        help="Output format (default: formatted)"
    )
    parser.add_argument(
        "--stage",
        help="Filter by specific stage (e.g., API_CALL, CITATIONS)"
    )
    parser.add_argument(
        "--extract",
        help="Extract specific stage data (e.g., citations, tool_call)"
    )
    
    args = parser.parse_args()
    
    if args.list:
        list_sessions()
    elif args.latest:
        try:
            session_id = get_latest_session()
            print(f"Latest session: {session_id}")
            if args.extract:
                extract_stage_data(session_id, args.extract)
            else:
                view_session(session_id, args.format, args.stage)
        except (FileNotFoundError, ValueError) as e:
            print(f"Error: {e}")
            sys.exit(1)
    elif args.session_id:
        if args.extract:
            extract_stage_data(args.session_id, args.extract)
        else:
            view_session(args.session_id, args.format, args.stage)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()