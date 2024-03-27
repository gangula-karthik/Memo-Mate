import time
import torch
from transformers import pipeline
from transformers.utils import is_flash_attn_2_available

def transcribe_audio(audio_file_path, model="openai/whisper-large-v3", device="cpu"):
    """
    Transcribe audio using insanely fast whisper model.
    """
    start = time.time()

    pipe = pipeline(
        "automatic-speech-recognition",
        model=model,
        torch_dtype=torch.float32 if device == "cpu" else torch.float16,
        device=device,
        model_kwargs={"use_flash_attention_2": is_flash_attn_2_available()},
    )

    outputs = pipe(
        audio_file_path,
        chunk_length_s=30,
        batch_size=24,
        return_timestamps=True,
    )

    end = time.time()

    execution_time = end - start
    return outputs, execution_time

audio_file_path = "path/to/your/audio/file.wav"
transcription, exec_time = transcribe_audio(audio_file_path, device="cpu")
print(transcription)
print(f"EXECUTION TIME: {exec_time} seconds")
