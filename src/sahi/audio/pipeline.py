"""Audio pipeline manager generating and degrading benchmark audio clips."""

import os
import hashlib
from typing import List, Dict, Any, Optional

from sahi.dataset.models import BaseUtterance
from sahi.dataset.pilot import PILOT_DATASET
from sahi.audio.models import (
    AudioCondition, TTSRequest, DegradationConfig, AudioClipRecord
)
from sahi.audio.providers.base import BaseTTSProvider
from sahi.audio.providers.sarvam_bulbul import SarvamBulbulProvider
from sahi.audio.providers.indic_parler import IndicParlerTTSStub
from sahi.audio.degradation import AudioDegradationEngine
from sahi.audio.wav_utils import read_wav_bytes

class AudioDatasetPipeline:
    """
    Manages generation of 3 conditions per utterance:
    1 utterance -> CLEAN + TELEPHONY + TELEPHONY_NOISE (3 evaluation clips).
    """

    def __init__(
        self,
        tts_provider: Optional[BaseTTSProvider] = None,
        degradation_engine: Optional[AudioDegradationEngine] = None,
        output_dir: str = "data/audio_clips"
    ):
        self.tts_provider = tts_provider or IndicParlerTTSStub(enable_mock_synthesis=True)
        self.degradation_engine = degradation_engine or AudioDegradationEngine()
        self.output_dir = output_dir

    def estimate_dataset_cost_inr(self, utterances: Optional[List[BaseUtterance]] = None) -> Dict[str, Any]:
        """Calculates character counts and dry-run cost estimates across utterances."""
        dataset = utterances or PILOT_DATASET
        total_chars = sum(len(u.native_text) for u in dataset)
        cost_inr = self.tts_provider.estimate_cost_inr(total_chars)

        return {
            "total_utterances": len(dataset),
            "total_characters": total_chars,
            "estimated_cost_inr": cost_inr,
            "clips_to_produce": len(dataset) * 3,
            "pricing_rate": "₹1.00 per 1,000 characters (Sarvam Bulbul v4 Flash)"
        }

    def generate_manifest(
        self,
        utterances: Optional[List[BaseUtterance]] = None,
        save_audio_files: bool = False
    ) -> List[AudioClipRecord]:
        """
        Processes utterances into clean, telephony, and noisy audio conditions.
        Returns a structured manifest list of AudioClipRecords.
        """
        dataset = utterances or PILOT_DATASET
        manifest: List[AudioClipRecord] = []

        if save_audio_files:
            os.makedirs(self.output_dir, exist_ok=True)

        for utt in dataset:
            # Map language group to valid standard TTS code
            lang_code = "en-IN"
            if utt.language_group == "HINDI":
                lang_code = "hi-IN"
            elif utt.language_group == "TELUGU":
                lang_code = "te-IN"
            elif utt.language_group == "HINGLISH":
                lang_code = "hi-IN"

            speaker = utt.speaker_metadata.get("gender", "meera")
            if speaker not in ["meera", "pavithra", "arvind", "amartya"]:
                speaker = "meera"

            tts_req = TTSRequest(
                text=utt.native_text,
                target_language_code=lang_code,
                speaker=speaker,
                provider="sarvam" if isinstance(self.tts_provider, SarvamBulbulProvider) else "mock_indic_parler"
            )

            # Synthesize or retrieve clean audio
            clean_resp = self.tts_provider.synthesize(tts_req)

            # Generate each condition
            for cond in [AudioCondition.CLEAN, AudioCondition.TELEPHONY, AudioCondition.TELEPHONY_NOISE]:
                clip_bytes, duration, snr_val = self.degradation_engine.process(
                    clean_resp.audio_bytes,
                    condition=cond
                )

                samples, sr, _ = read_wav_bytes(clip_bytes)
                clip_hash = hashlib.sha256(clip_bytes).hexdigest()
                clip_id = f"CLIP_{utt.id}_{cond.value}"
                rel_path = f"{cond.value.lower()}/{clip_id}.wav"

                if save_audio_files:
                    cond_dir = os.path.join(self.output_dir, cond.value.lower())
                    os.makedirs(cond_dir, exist_ok=True)
                    full_path = os.path.join(cond_dir, f"{clip_id}.wav")
                    with open(full_path, "wb") as f:
                        f.write(clip_bytes)

                record = AudioClipRecord(
                    clip_id=clip_id,
                    utterance_id=utt.id,
                    condition=cond,
                    sha256_hash=clip_hash,
                    sample_rate=sr,
                    duration_seconds=duration,
                    snr_db=snr_val,
                    provider=tts_req.provider,
                    model=tts_req.model,
                    relative_filepath=rel_path,
                    metadata={
                        "language_group": utt.language_group,
                        "category": utt.category.value,
                        "intended_amount_inr": utt.intended_amount_inr,
                        "native_text": utt.native_text
                    }
                )
                manifest.append(record)

        return manifest
