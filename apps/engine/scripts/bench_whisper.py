"""Mede velocidade e qualidade do faster-whisper em CPU. Uso: bench_whisper.py <wav> <modelo>"""
import sys, time
from faster_whisper import WhisperModel

wav, name = sys.argv[1], sys.argv[2]
t0 = time.time()
model = WhisperModel(name, device="cpu", compute_type="int8", cpu_threads=8)
load = time.time() - t0
t0 = time.time()
segs, info = model.transcribe(wav, language="pt", word_timestamps=True, vad_filter=True, beam_size=1)
text = []
for s in segs:
    text.append(s.text.strip())
took = time.time() - t0
print(f"modelo={name} carga={load:.0f}s transcricao={took:.0f}s audio={info.duration:.0f}s fator={info.duration/took:.2f}x")
open(f"{wav}.{name}.txt", "w", encoding="utf-8").write("\n".join(text))
