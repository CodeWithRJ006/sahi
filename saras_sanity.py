import asyncio, os, aiohttp, wave, io

async def test_saras_transcribe():
    key = os.getenv('SARAS_API_KEY')
    # create 0.1 sec silence wav in memory
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b'\x00\x00' * 1600)  # 0.1 sec
    buf.seek(0)
    data = {'audio_file': buf, 'mode': 'transcribe', 'model': 'saaras:v4'}
    headers = {"Authorization": f"Bearer {key}"}
    async with aiohttp.ClientSession() as session:
        async with session.post('https://api.sarvam.ai/speech-to-text', data=data, headers=headers) as resp:
            print('Saaras transcribe status:', resp.status)
            if resp.status != 200:
                print('Error body:', await resp.text())

async def test_saras_codemix():
    key = os.getenv('SARAS_API_KEY')
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b'\x00\x00' * 1600)
    buf.seek(0)
    data = {'audio_file': buf, 'mode': 'transcribe', 'model': 'saaras:v4'}
    headers = {"Authorization": f"Bearer {key}"}
    async with aiohttp.ClientSession() as session:
        async with session.post('https://api.sarvam.ai/v1/codemix', data=data, headers=headers) as resp:
            print('Saaras codemix status:', resp.status)
            if resp.status != 200:
                print('Error body:', await resp.text())

if __name__ == '__main__':
    asyncio.run(test_saras_transcribe())
    asyncio.run(test_saras_codemix())
