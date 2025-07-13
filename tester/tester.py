import asyncio
import httpx

async def send_request(session, i):
    try:
        payload = {"input": f"Test input {i}"}
        response = await session.post("http://localhost:8000/infer", json=payload)
        # response = await session.post("http://coordinator:8000/infer", json=payload)
        print(f"Request {i}: {response.status_code}, {response.json()}")
    except Exception as e:
        print(f"Request {i} failed: {e}")

async def main():
    async with httpx.AsyncClient() as client:
        tasks = [send_request(client, i) for i in range(6)]
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
