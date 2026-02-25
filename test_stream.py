import httpx
import json
import asyncio

async def test_stream():
    url = "http://localhost:2024/v1/threads/test-thread-123/runs/stream"
    payload = {
        "input": {
            "support_type": "service",
            "auth_verified": True,
            "auth_step": "verified",
            "auth_identifier_type": "email",
            "auth_identifier_value": "nobody@google.com",
            "in_db": False,
            "lookup_retries": 1,
            "messages": [
                {"type": "human", "content": "Service Support"},
                {"type": "human", "content": "nobody@google.com"},
                {"type": "human", "content": "123456"},
                {"type": "human", "content": "No, continue anyway"}
            ]
        }
    }
    
    try:
        async with httpx.AsyncClient() as client:
            async with client.stream("POST", url, json=payload, timeout=10.0) as response:
                print(f"Status Code: {response.status_code}")
                async for line in response.aiter_lines():
                    print(line)
    except Exception as e:
        print(f"Error during request: {e}")

if __name__ == "__main__":
    asyncio.run(test_stream())
