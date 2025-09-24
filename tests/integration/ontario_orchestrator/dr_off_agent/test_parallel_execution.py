"""
Test to verify that SQL and vector queries run in parallel using asyncio.gather().
This test demonstrates that dual-path retrieval meets performance requirements.
"""
import asyncio
import time
from unittest.mock import AsyncMock, patch
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agents.ontario_orchestrator.mcp.tools.schedule import ScheduleTool
from src.agents.ontario_orchestrator.mcp.tools.adp import ADPTool
from src.agents.ontario_orchestrator.mcp.models.request import ScheduleGetRequest, ADPGetRequest, DeviceSpec


async def test_schedule_parallel_execution():
    """Test that schedule.get runs SQL and vector queries in parallel."""
    
    print("\n=== Testing Schedule Tool Parallel Execution ===")
    
    # Create mock clients with delays
    mock_sql_client = AsyncMock()
    mock_vector_client = AsyncMock()
    
    # SQL takes 300ms
    async def slow_sql_query(*args, **kwargs):
        print(f"  SQL query started at {time.time():.3f}")
        await asyncio.sleep(0.3)
        print(f"  SQL query finished at {time.time():.3f}")
        return [
            {
                "code": "C124",
                "description": "Day of discharge",
                "amount": 31.00,
                "requirements": "Discharge summary required"
            }
        ]
    
    # Vector takes 500ms
    async def slow_vector_search(*args, **kwargs):
        print(f"  Vector search started at {time.time():.3f}")
        await asyncio.sleep(0.5)
        print(f"  Vector search finished at {time.time():.3f}")
        return [
            {
                "text": "C124 requires 72 hour admission minimum",
                "metadata": {"source": "schedule.pdf", "page": 45}
            }
        ]
    
    mock_sql_client.query_schedule_fees = slow_sql_query
    mock_vector_client.search_schedule = slow_vector_search
    
    # Create tool and request
    tool = ScheduleTool(sql_client=mock_sql_client, vector_client=mock_vector_client)
    request = ScheduleGetRequest(
        q="MRP discharge billing",
        codes=["C124"],
        include=["codes", "fee", "limits"]
    )
    
    # Execute and measure time
    start_time = time.time()
    print(f"Starting dual-path query at {start_time:.3f}")
    
    response = await tool.execute(request)
    
    elapsed = time.time() - start_time
    print(f"Completed in {elapsed:.3f} seconds")
    
    # Verify parallel execution
    assert elapsed < 0.6, f"Should complete in ~0.5s (parallel), but took {elapsed:.3f}s"
    assert elapsed > 0.4, f"Should take at least 0.5s (vector time), but only took {elapsed:.3f}s"
    
    # Verify both paths executed
    assert "sql" in response.provenance
    assert "vector" in response.provenance
    
    print(f"✓ Schedule tool runs in parallel: {elapsed:.3f}s (expected ~0.5s)")
    return elapsed


async def test_adp_parallel_execution():
    """Test that adp.get runs SQL and vector queries in parallel."""
    
    print("\n=== Testing ADP Tool Parallel Execution ===")
    
    # Create mock clients with delays
    mock_sql_client = AsyncMock()
    mock_vector_client = AsyncMock()
    
    # SQL takes 400ms (two queries)
    async def slow_sql_funding(*args, **kwargs):
        print(f"  SQL funding query started at {time.time():.3f}")
        await asyncio.sleep(0.2)
        print(f"  SQL funding query finished at {time.time():.3f}")
        return [
            {
                "scenario": "Power wheelchair",
                "client_share_percent": 25,
                "adp_share_percent": 75
            }
        ]
    
    async def slow_sql_exclusions(*args, **kwargs):
        print(f"  SQL exclusion query started at {time.time():.3f}")
        await asyncio.sleep(0.2)
        print(f"  SQL exclusion query finished at {time.time():.3f}")
        return []
    
    # Vector takes 600ms
    async def slow_vector_search(*args, **kwargs):
        print(f"  Vector search started at {time.time():.3f}")
        await asyncio.sleep(0.6)
        print(f"  Vector search finished at {time.time():.3f}")
        return [
            {
                "text": "Power wheelchairs require assessment. ADP covers 75%.",
                "metadata": {"source": "mobility-manual", "page": 45}
            }
        ]
    
    mock_sql_client.query_adp_funding = slow_sql_funding
    mock_sql_client.query_adp_exclusions = slow_sql_exclusions
    mock_vector_client.search_adp = slow_vector_search
    
    # Create tool and request
    tool = ADPTool(sql_client=mock_sql_client, vector_client=mock_vector_client)
    request = ADPGetRequest(
        device=DeviceSpec(category="mobility", type="power_wheelchair"),
        check=["eligibility", "funding"],
        patient_income=19000
    )
    
    # Execute and measure time
    start_time = time.time()
    print(f"Starting dual-path query at {start_time:.3f}")
    
    response = await tool.execute(request)
    
    elapsed = time.time() - start_time
    print(f"Completed in {elapsed:.3f} seconds")
    
    # Verify parallel execution
    # Should take ~0.6s (max of SQL and vector), not 1.0s (sequential)
    assert elapsed < 0.7, f"Should complete in ~0.6s (parallel), but took {elapsed:.3f}s"
    assert elapsed > 0.5, f"Should take at least 0.6s (vector time), but only took {elapsed:.3f}s"
    
    # Verify both paths executed
    assert "sql" in response.provenance
    assert "vector" in response.provenance
    
    print(f"✓ ADP tool runs in parallel: {elapsed:.3f}s (expected ~0.6s)")
    return elapsed


async def test_error_handling():
    """Test that one path failing doesn't break the other."""
    
    print("\n=== Testing Error Handling in Parallel Execution ===")
    
    # Create mock clients where SQL fails
    mock_sql_client = AsyncMock()
    mock_vector_client = AsyncMock()
    
    # SQL fails after 100ms
    async def failing_sql(*args, **kwargs):
        print(f"  SQL query will fail...")
        await asyncio.sleep(0.1)
        raise Exception("SQL connection error")
    
    # Vector succeeds after 200ms
    async def working_vector(*args, **kwargs):
        print(f"  Vector search working...")
        await asyncio.sleep(0.2)
        return [
            {
                "text": "C124 billing information",
                "metadata": {"source": "schedule.pdf"}
            }
        ]
    
    mock_sql_client.query_schedule_fees = failing_sql
    mock_vector_client.search_schedule = working_vector
    
    # Create tool and request
    tool = ScheduleTool(sql_client=mock_sql_client, vector_client=mock_vector_client)
    request = ScheduleGetRequest(q="test query")
    
    # Execute
    response = await tool.execute(request)
    
    # Verify vector succeeded even though SQL failed
    assert "sql" not in response.provenance
    assert "vector" in response.provenance
    assert response.confidence < 0.9  # Lower confidence without SQL
    
    print("✓ Error handling works: Vector continues when SQL fails")


async def main():
    """Run all parallel execution tests."""
    
    print("=" * 60)
    print("DUAL-PATH PARALLEL EXECUTION VERIFICATION")
    print("=" * 60)
    
    try:
        # Test schedule tool
        schedule_time = await test_schedule_parallel_execution()
        
        # Test ADP tool
        adp_time = await test_adp_parallel_execution()
        
        # Test error handling
        await test_error_handling()
        
        print("\n" + "=" * 60)
        print("✅ ALL PARALLEL EXECUTION TESTS PASSED")
        print(f"Schedule tool: {schedule_time:.3f}s (parallel)")
        print(f"ADP tool: {adp_time:.3f}s (parallel)")
        print("Both tools correctly use asyncio.gather() for parallel execution")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())