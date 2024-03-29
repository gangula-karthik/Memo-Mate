import time
import torch
from transformers import pipeline, AutoModelForSpeechSeq2Seq
from transformers.utils import is_flash_attn_2_available

transcription_pipeline = None
model_id = "distil-whisper/distil-small.en"
torch_dtype = torch.float32

model = AutoModelForSpeechSeq2Seq.from_pretrained(
    model_id, torch_dtype=torch_dtype, low_cpu_mem_usage=True, use_safetensors=True
)

def initialize_transcription_pipeline(model=model_id, device="cpu"):
    """
    Initializes the transcription pipeline and stores it in a global variable.
    """
    global transcription_pipeline
    if transcription_pipeline is None:
        transcription_pipeline = pipeline(
            "automatic-speech-recognition",
            model=model,
            torch_dtype=torch_dtype,
            device=device,
            model_kwargs={"use_flash_attention_2": is_flash_attn_2_available()},
        )

def transcribe_audio(audio_file_path, model=model_id, device="cpu"):
    """
    Transcribe audio using the insanely fast Whisper model.
    """
    global transcription_pipeline
    if transcription_pipeline is None:
        initialize_transcription_pipeline(model, device)
    
    start = time.time()

    outputs = transcription_pipeline(
        audio_file_path,
        chunk_length_s=30,
        batch_size=24,
        return_timestamps=True,
    )

    end = time.time()

    execution_time = end - start
    return {"outputs": outputs, "execution_time": execution_time}


# testing the transcribe_audio function
if __name__ == "__main__":
    audio_file_path = "./617688378842021924.wav"
    res = transcribe_audio(audio_file_path)
    print()
    print(res)