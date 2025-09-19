"""
Streaming version of the Emergency Triage Orchestrator.
Provides real-time progress updates as agents process the assessment.
"""

from typing import Optional, Dict, Any, AsyncGenerator
from pydantic import BaseModel, Field
import json

try:
    from agents import Agent, Runner, ItemHelpers
    from agents.stream_events import StreamEvent, RunItemStreamEvent, AgentUpdatedStreamEvent, RawResponsesStreamEvent
    from openai.types.responses import ResponseTextDeltaEvent
    from langfuse import Langfuse
except ImportError:
    # Fallback for development
    Agent = None
    Runner = None
    ItemHelpers = None
    StreamEvent = None
    RunItemStreamEvent = None
    AgentUpdatedStreamEvent = None
    RawResponsesStreamEvent = None
    ResponseTextDeltaEvent = None
    Langfuse = None

from .orchestrator import TriageDecision, create_triage_orchestrator, _format_patient_data


class StreamingUpdate(BaseModel):
    """A streaming update from the triage assessment."""
    type: str = Field(description="Type of update: agent_change, tool_call, tool_result, progress, final")
    agent: Optional[str] = Field(default=None, description="Current agent name")
    tool: Optional[str] = Field(default=None, description="Tool being called")
    message: Optional[str] = Field(default=None, description="Update message")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Additional data")
    progress: Optional[float] = Field(default=None, description="Progress percentage (0-100)")


async def run_triage_assessment_streaming(
    patient_data: Dict[str, Any],
    session_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    langfuse_enabled: bool = True
) -> AsyncGenerator[StreamingUpdate, None]:
    """
    Run a triage assessment with streaming progress updates.
    
    Yields StreamingUpdate objects with progress information as the assessment proceeds.
    The final yield will be a StreamingUpdate with type="final" containing the TriageDecision.
    
    Args:
        patient_data: Patient information dictionary
        session_id: Optional session ID for tracking
        trace_id: Optional trace ID for Langfuse
        langfuse_enabled: Whether to enable Langfuse tracing
        
    Yields:
        StreamingUpdate objects with progress information
    """
    
    # Initialize Langfuse if enabled
    langfuse_trace = None
    if langfuse_enabled and Langfuse:
        try:
            langfuse = Langfuse()
            langfuse_trace = langfuse.trace(
                name="triage_assessment_streaming",
                id=trace_id,
                metadata={
                    "session_id": session_id,
                    "chief_complaint": patient_data.get("chief_complaint"),
                    "age": patient_data.get("age"),
                    "streaming": True
                }
            )
        except Exception as e:
            print(f"Failed to initialize Langfuse: {e}")
    
    try:
        # Create the orchestrator
        orchestrator = create_triage_orchestrator()
        
        # Format patient data as string for the agent
        patient_info = _format_patient_data(patient_data)
        
        if Runner is None:
            # Development mode - yield mock updates
            yield StreamingUpdate(
                type="progress",
                message="Development mode - returning mock assessment",
                progress=0
            )
            
            yield StreamingUpdate(
                type="final",
                data={
                    "final_ctas_level": 3,
                    "urgency": "Urgent",
                    "red_flags_identified": ["Development mode - no actual assessment"],
                    "initial_actions": ["Complete patient registration", "Obtain vital signs"],
                    "recommended_tests": ["ECG", "CBC", "Basic metabolic panel"],
                    "estimated_wait_time": "30 minutes",
                    "disposition": "Emergency treatment area - requires physician assessment",
                    "clinical_summary": "Mock triage assessment in development mode",
                    "confidence": 0.0
                },
                progress=100
            )
            return
        
        # Run the orchestrator with streaming
        result = Runner.run_streamed(
            orchestrator,
            input=patient_info,
            max_turns=4  # 3 tool calls + 1 final response
        )
        
        # Track progress
        current_agent = "Emergency Triage Orchestrator"
        tools_called = set()  # Track unique tools called
        total_tools = 3  # We have 3 specialist agents
        
        # Initial update
        try:
            initial_update = StreamingUpdate(
                type="progress",
                agent=current_agent,
                message="Starting triage assessment",
                progress=0
            )
            yield initial_update
        except Exception as e:
            print(f"ERROR creating initial StreamingUpdate: {e}")
            raise
        
        # Stream events
        async for event in result.stream_events():
            
            # Agent change events
            if event.type == "agent_updated_stream_event":
                try:
                    current_agent = event.new_agent.name
                    # Calculate progress based on unique tools called
                    progress = (len(tools_called) / total_tools) * 90
                    update = StreamingUpdate(
                        type="agent_change",
                        agent=current_agent,
                        message=f"Processing with {current_agent}",
                        progress=progress
                    )
                    yield update
                except Exception as e:
                    print(f"ERROR in agent_updated_stream_event handler: {e}")
                    print(f"Event: {event}")
                    raise
            
            # Run item events (tool calls, outputs)
            elif event.type == "run_item_stream_event":
                if event.item.type == "tool_call_item":
                    # Extract tool name from the raw_item
                    tool_name = "unknown"
                    try:
                        # The tool name is in raw_item.name
                        if hasattr(event.item, 'raw_item') and hasattr(event.item.raw_item, 'name'):
                            tool_name = event.item.raw_item.name
                    except Exception as e:
                        pass  # Silently continue with "unknown"
                    
                    # Map tool names to friendly names
                    friendly_names = {
                        "detect_red_flags": "Red Flag Detector",
                        "assess_triage_level": "CTAS Triage Assessor",
                        "suggest_initial_workup": "Workup Suggester"
                    }
                    friendly_tool = friendly_names.get(tool_name, tool_name)
                    
                    # Track unique tools called
                    if tool_name in friendly_names:
                        tools_called.add(tool_name)
                    
                    # Calculate progress based on unique tools called
                    progress = (len(tools_called) / total_tools) * 90
                    
                    yield StreamingUpdate(
                        type="tool_call",
                        agent=current_agent,
                        tool=friendly_tool,
                        message=f"Analyzing with {friendly_tool}",
                        progress=progress
                    )
                
                elif event.item.type == "tool_call_output_item":
                    # Tool completed - we can access the output
                    try:
                        # Extract the actual output content
                        tool_output = None
                        summary = None
                        
                        if hasattr(event.item, 'output'):
                            tool_output = event.item.output
                            # Try to parse JSON and extract key info
                            if isinstance(tool_output, str):
                                try:
                                    import json
                                    parsed = json.loads(tool_output)
                                    # Create a human-readable summary based on tool output
                                    if 'has_red_flags' in parsed:
                                        # Red flag detector output
                                        if parsed.get('has_red_flags'):
                                            summary = f"⚠️ Red flags detected: {', '.join(parsed.get('red_flags', []))[:100]}"
                                        else:
                                            summary = "✓ No red flags identified"
                                    elif 'ctas_level' in parsed:
                                        # CTAS assessor output
                                        summary = f"CTAS Level {parsed.get('ctas_level')}: {parsed.get('urgency', '')}"
                                    elif 'immediate_tests' in parsed:
                                        # Workup suggester output
                                        tests = parsed.get('immediate_tests', [])
                                        if tests:
                                            test_names = [t.get('test', '') for t in tests[:2]]
                                            summary = f"Tests recommended: {', '.join(test_names)}"
                                        else:
                                            summary = "Routine tests suggested"
                                except:
                                    # If not JSON, just take first line
                                    lines = tool_output.split('\n')
                                    if lines:
                                        summary = lines[0][:150]
                        
                        # Calculate progress based on unique tools called
                        progress = (len(tools_called) / total_tools) * 90
                        yield StreamingUpdate(
                            type="tool_result",
                            agent=current_agent,
                            message=f"Completed analysis",
                            data={"summary": summary} if summary else None,
                            progress=progress
                        )
                    except Exception as e:
                        pass
                
                elif event.item.type == "message_output_item":
                    # Final message being composed - this might be partial text
                    try:
                        # Extract the message text if available
                        message_text = None
                        if ItemHelpers:
                            try:
                                message_text = ItemHelpers.text_message_output(event.item)
                                # Get a preview of the message
                                if message_text:
                                    preview = message_text[:100] + "..." if len(message_text) > 100 else message_text
                                else:
                                    preview = None
                            except:
                                preview = None
                        else:
                            preview = None
                        
                        yield StreamingUpdate(
                            type="progress",
                            agent=current_agent,
                            message="Synthesizing assessment results",
                            data={"preview": preview} if preview else None,
                            progress=95
                        )
                    except Exception as e:
                        pass
            
            # Raw response events (optional - for fine-grained text streaming)
            elif event.type == "raw_response_event":
                # We could stream text deltas here if needed
                # For now, we'll skip these for cleaner progress updates
                pass
        
        # Get the final result
        final_result = result.final_output
        
        # Update Langfuse trace with results if available
        if langfuse_trace:
            langfuse_trace.update(
                output=final_result.model_dump() if hasattr(final_result, 'model_dump') else str(final_result),
                metadata={
                    "ctas_level": getattr(final_result, 'final_ctas_level', None),
                    "confidence": getattr(final_result, 'confidence', None),
                    "red_flags_count": len(getattr(final_result, 'red_flags_identified', [])),
                }
            )
        
        # Yield the final result
        if isinstance(final_result, TriageDecision):
            yield StreamingUpdate(
                type="final",
                message="Assessment complete",
                data=final_result.model_dump(),
                progress=100
            )
        else:
            # Fallback if output isn't properly structured
            yield StreamingUpdate(
                type="final",
                message="Assessment complete (with errors)",
                data={
                    "final_ctas_level": 2,
                    "urgency": "Emergent",
                    "red_flags_identified": ["Unable to complete full assessment"],
                    "initial_actions": ["Immediate physician assessment required"],
                    "recommended_tests": ["As per physician assessment"],
                    "estimated_wait_time": "Immediate",
                    "disposition": "Resuscitation area - immediate physician assessment",
                    "clinical_summary": "Assessment incomplete - defaulting to high acuity for safety",
                    "confidence": 0.0
                },
                progress=100
            )
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        
        # Log detailed error
        print(f"ERROR in run_triage_assessment_streaming: {str(e)}")
        print(f"Full traceback:\n{error_details}")
        
        # Log error to Langfuse if available
        if langfuse_trace:
            langfuse_trace.update(
                level="ERROR",
                status_message=f"{str(e)}\n{error_details}"
            )
        
        # Yield error as final update
        yield StreamingUpdate(
            type="final",
            message=f"Assessment error: {str(e)}",
            data={
                "final_ctas_level": 1,
                "urgency": "Resuscitation",
                "red_flags_identified": [f"System error: {str(e)}"],
                "initial_actions": ["Immediate physician assessment", "Manual triage required"],
                "recommended_tests": ["As per physician assessment"],
                "estimated_wait_time": "Immediate",
                "disposition": "Resuscitation area - immediate physician assessment",
                "clinical_summary": f"System error during assessment - defaulting to highest acuity",
                "confidence": 0.0
            },
            progress=100
        )
    
    finally:
        # Ensure Langfuse flushes
        if langfuse_enabled and Langfuse:
            try:
                langfuse = Langfuse()
                langfuse.flush()
            except:
                pass