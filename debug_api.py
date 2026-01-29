import httpx
import time
import asyncio

async def test_connection():
    print("Testing API Connection...")
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Test Health
        try:
            print(f"GET http://localhost:8000/agent/health")
            resp = await client.get("http://localhost:8000/agent/health")
            print(f"Status: {resp.status_code}")
            print(f"Response: {resp.text}")
        except Exception as e:
            print(f"Health Check Failed: {e}")
            return

        # 2. Test Query (Simple)
        try:
            payload = {
                "query": "Hello, are you there?",
                "session_id": "test-debug-1",
                "patient_id": "179713d4-6c3d-4397-81f4-687dc9d7e609"
            }
            print(f"\nPOST http://localhost:8000/agent/query")
            print(f"Payload: {payload}")
            resp = await client.post("http://localhost:8000/agent/query", json=payload)
            print(f"Status: {resp.status_code}")
            print(f"Response: {resp.text[:500]}...") # Print first 500 chars
        except Exception as e:
            print(f"Query Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())
