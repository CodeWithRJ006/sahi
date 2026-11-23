import yaml, pathlib, sys
from collections import Counter

path = pathlib.Path(__file__).resolve().parent / "data" / "live_pilot_8.yaml"
records = yaml.safe_load(path.read_text(encoding='utf-8'))

print('YAML parsed, count:', len(records))

ids = [r.get('id') for r in records]
print('Unique IDs:', len(set(ids)) == len(ids))

print('INR values:', [r.get('intended_inr') for r in records])

langs = Counter(r.get('language_code') for r in records)
print('Language distribution:', dict(langs))

allow = {'simran_en_customer','ritu_hi_customer','simran_enhi_customer','kavitha_te_conversation'}
invalid = [r['proposed_speaker'] for r in records if r['proposed_speaker'] not in allow]
print('Invalid speakers:', invalid)

print('Verification statuses:', [r.get('verification_status') for r in records])
