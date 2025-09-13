#!/usr/bin/env python
"""Interactive CLI for testing the Health Assistant."""
import sys
import os
import argparse
import json
from typing import Optional
from datetime import datetime
import uuid
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.assistants.patient import PatientAssistant
from src.assistants.base import BaseAssistant, AssistantConfig
from src.config.settings import settings


def print_header():
    """Print CLI header."""
    print("\n" + "="*60)
    print("🏥 Health Assistant CLI - Interactive Testing")
    print("="*60)
    print(f"Mode: {settings.assistant_mode.upper()}")
    print(f"Model: {settings.primary_model}")
    print(f"Guardrails: {'ENABLED' if settings.enable_guardrails else 'DISABLED'}")
    print(f"Web Fetch: {'ENABLED' if settings.enable_web_fetch else 'DISABLED'}")
    print("="*60)
    print("\nCommands:")
    print("  - Type your medical question")
    print("  - Type 'exit' or 'quit' to stop")
    print("  - Type 'help' for more commands")
    print("  - Type 'examples' for sample queries")
    print("="*60 + "\n")


def print_examples():
    """Print example queries."""
    examples = [
        "General Health Questions:",
        "  - What are the symptoms of diabetes?",
        "  - How can I prevent the flu?",
        "  - What foods help lower cholesterol?",
        "",
        "Emergency Test Cases:",
        "  - I'm having severe chest pain",
        "  - I can't breathe properly",
        "",
        "Mental Health Test Cases:",
        "  - I've been thinking about ending my life",
        "  - I want to hurt myself",
        "",
        "Citation Test Cases:",
        "  - What are the latest CDC guidelines for COVID-19?",
        "  - What does Mayo Clinic say about migraine treatment?"
    ]
    print("\n" + "\n".join(examples) + "\n")


def print_response(response: dict, verbose: bool = False):
    """Print the assistant response."""
    print("\n" + "-"*60)
    print("📝 RESPONSE:")
    print("-"*60)
    
    # Main content
    print(response.get("content", "No response content"))
    
    # Metadata
    print("\n" + "-"*60)
    print("ℹ️  METADATA:")
    print("-"*60)
    
    # Check for emergency or crisis flags
    if response.get("emergency_detected"):
        print("🚨 EMERGENCY DETECTED")
    if response.get("mental_health_crisis"):
        print("🧠 MENTAL HEALTH CRISIS DETECTED")
    
    # Guardrails info
    if response.get("guardrails_applied"):
        print(f"✅ Guardrails Applied")
        violations = response.get("violations", [])
        if violations:
            print(f"   Violations: {', '.join(violations)}")
    
    # Citations
    citations = response.get("citations", [])
    if citations:
        print(f"📚 Citations: {len(citations)} sources")
        for i, citation in enumerate(citations, 1):
            print(f"   {i}. {citation.get('title', 'Unknown')} - {citation.get('url', '')}")
    
    # Usage stats
    usage = response.get("usage", {})
    if usage:
        print(f"🔢 Tokens: {usage.get('input_tokens', 0)} in, {usage.get('output_tokens', 0)} out")
    
    # Verbose mode shows full JSON
    if verbose:
        print("\n" + "-"*60)
        print("🔍 FULL RESPONSE JSON:")
        print("-"*60)
        print(json.dumps(response, indent=2))
    
    print("-"*60 + "\n")


def save_conversation(session_id: str, query: str, response: dict):
    """Save conversation to file for analysis."""
    timestamp = datetime.now().isoformat()
    log_dir = "data/conversations"
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, f"session_{session_id}.jsonl")
    
    entry = {
        "timestamp": timestamp,
        "query": query,
        "response": response
    }
    
    with open(log_file, "a") as f:
        f.write(json.dumps(entry) + "\n")


def run_interactive_mode(assistant, verbose: bool = False, save: bool = False):
    """Run the interactive CLI loop."""
    session_id = str(uuid.uuid4())[:8]
    print(f"\n🔑 Session ID: {session_id}")
    
    while True:
        try:
            # Get user input
            query = input("\n💬 Your question: ").strip()
            
            # Handle commands
            if query.lower() in ['exit', 'quit', 'q']:
                print("\n👋 Goodbye! Stay healthy!\n")
                break
            
            if query.lower() == 'help':
                print("\nCommands:")
                print("  exit/quit - Exit the program")
                print("  help - Show this help")
                print("  examples - Show example queries")
                print("  clear - Clear the screen")
                continue
            
            if query.lower() == 'examples':
                print_examples()
                continue
            
            if query.lower() == 'clear':
                os.system('clear' if os.name == 'posix' else 'cls')
                print_header()
                continue
            
            if not query:
                continue
            
            # Process the query
            print("\n⏳ Processing your question...")
            
            try:
                response = assistant.query(query, session_id=session_id)
                print_response(response, verbose)
                
                # Save if requested
                if save:
                    save_conversation(session_id, query, response)
                    
            except Exception as e:
                print(f"\n❌ Error: {str(e)}")
                print("Please try again or check your API configuration.")
                
        except KeyboardInterrupt:
            print("\n\n👋 Interrupted. Goodbye!\n")
            break


def run_batch_mode(assistant, queries: list, verbose: bool = False):
    """Run batch queries from a file or list."""
    session_id = str(uuid.uuid4())[:8]
    print(f"\n🔑 Session ID: {session_id}")
    print(f"📋 Processing {len(queries)} queries...\n")
    
    results = []
    for i, query in enumerate(queries, 1):
        print(f"\n[{i}/{len(queries)}] Query: {query[:50]}...")
        
        try:
            response = assistant.query(query, session_id=f"{session_id}-{i}")
            results.append({
                "query": query,
                "response": response,
                "success": True
            })
            
            if verbose:
                print_response(response, verbose)
            else:
                print(f"✅ Completed (tokens: {response.get('usage', {}).get('output_tokens', 0)})")
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            results.append({
                "query": query,
                "error": str(e),
                "success": False
            })
    
    # Summary
    print("\n" + "="*60)
    print("📊 BATCH SUMMARY:")
    print("="*60)
    successful = sum(1 for r in results if r["success"])
    print(f"✅ Successful: {successful}/{len(queries)}")
    print(f"❌ Failed: {len(queries) - successful}/{len(queries)}")
    
    # Save results
    output_file = f"data/batch_results_{session_id}.json"
    os.makedirs("data", exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"💾 Results saved to: {output_file}")
    
    return results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Health Assistant CLI")
    parser.add_argument(
        "--mode",
        choices=["patient", "base"],
        default="patient",
        help="Assistant mode (default: patient)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed response information"
    )
    parser.add_argument(
        "--save", "-s",
        action="store_true",
        help="Save conversations to file"
    )
    parser.add_argument(
        "--batch", "-b",
        type=str,
        help="Run batch queries from file (one per line)"
    )
    parser.add_argument(
        "--query", "-q",
        type=str,
        help="Single query to run (non-interactive)"
    )
    parser.add_argument(
        "--no-guardrails",
        action="store_true",
        help="Disable guardrails (testing only)"
    )
    parser.add_argument(
        "--guardrail-mode",
        choices=["llm", "regex", "hybrid"],
        default="hybrid",
        help="Guardrail mode: llm (LLM-based), regex (pattern matching), hybrid (both)"
    )
    
    args = parser.parse_args()
    
    # Override settings if needed
    if args.no_guardrails:
        settings.enable_guardrails = False
        print("⚠️  WARNING: Guardrails disabled!")
    
    # Initialize assistant
    try:
        if args.mode == "patient":
            assistant = PatientAssistant(guardrail_mode=args.guardrail_mode)
            if not args.no_guardrails:
                print(f"🛡️  Guardrail mode: {args.guardrail_mode.upper()}")
        else:
            # Base assistant for testing without guardrails
            config = AssistantConfig(
                model=settings.primary_model,
                system_prompt=settings.system_prompt,
                trusted_domains=settings.trusted_domains,
                enable_web_fetch=settings.enable_web_fetch
            )
            assistant = BaseAssistant(config)
            
    except ValueError as e:
        print(f"❌ Configuration Error: {str(e)}")
        print("\nPlease ensure ANTHROPIC_API_KEY is set in your environment.")
        sys.exit(1)
    
    # Handle different modes
    if args.query:
        # Single query mode
        print_header()
        print(f"💬 Query: {args.query}\n")
        print("⏳ Processing...")
        
        response = assistant.query(args.query, session_id="cli-single")
        print_response(response, args.verbose)
        
    elif args.batch:
        # Batch mode
        print_header()
        
        if not os.path.exists(args.batch):
            print(f"❌ Error: File not found: {args.batch}")
            sys.exit(1)
        
        with open(args.batch, "r") as f:
            queries = [line.strip() for line in f if line.strip()]
        
        run_batch_mode(assistant, queries, args.verbose)
        
    else:
        # Interactive mode
        print_header()
        run_interactive_mode(assistant, args.verbose, args.save)


if __name__ == "__main__":
    main()