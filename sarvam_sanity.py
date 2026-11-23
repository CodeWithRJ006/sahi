import asyncio, os, aiohttp, json

async def test_sarvam():
    key = os.getenv('SARVAM_API_KEY')
    payload = {
        "model": "sarvam-105b",
        "messages": [
            {"role": "system", "content": "You are a test bot."},
            {"role": "user", "content": "Hello"}
        ],
        "max_tokens": 5,
        "temperature": 0.0,
        "stream": False
    }
    headers = {"Authorization": f"Bearer {key}"}
    async with aiohttp.ClientSession() as session:
        async with session.post('https://api.sarvam.ai/v1/chat/completions', json=payload, headers=headers) as resp:
            print('Sarvam 105B status:', resp.status)
            if resp.status != 200:
                print('Error body:', await resp.text())
            else:
                data = await resp.json()
                print('Response snippet:', json.dumps(data)[:200])

if __name__ == '__main__':
    asyncio.run(test_sarvam())
