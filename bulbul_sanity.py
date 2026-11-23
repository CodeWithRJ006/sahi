import asyncio, os, aiohttp, wave, io

async def test_bulbul():
    key = os.getenv('BULBUL_API_KEY')
    payload = {
        "text": "test",
        "language_code": "en-US",
        "voice_id": "en_us_neutral_01",
        "audio_format": "wav",
        "sample_rate_hz": 16000,
    }
    headers = {"Authorization": f"Bearer {key}"}
    async with aiohttp.ClientSession() as session:
        async with session.post('https://api.sarvam.ai/text-to-speech', json=payload, headers=headers) as resp:
            print('Bulbul status:', resp.status)
            if resp.status != 200:
                print('Error body:', await resp.text())

if __name__ == '__main__':
    asyncio.run(test_bulbul())
