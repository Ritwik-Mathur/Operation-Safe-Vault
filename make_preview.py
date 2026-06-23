"""
make_preview.py  — generates spectrogram_preview.html from temp.wav
Run: python make_preview.py
Open the generated HTML file in any browser.
"""
import sys, os
sys.path.insert(0, 'backend')
from core.spectrogram_generator import generate_spectrogram_image

WAV = os.path.join("Fraud_Detection_shield", "temp.wav")
with open(WAV, 'rb') as f:
    audio = f.read()

result = generate_spectrogram_image(audio, 'temp.wav')

html = (
    "<!DOCTYPE html>\n"
    "<html>\n"
    "<head><title>Spectrogram Preview</title>\n"
    "<style>\n"
    "body{background:#131313;display:flex;flex-direction:column;"
    "align-items:center;justify-content:center;min-height:100vh;"
    "margin:0;font-family:sans-serif;padding:32px;}\n"
    "h2{color:#31e368;font-size:11px;letter-spacing:.3em;text-transform:uppercase;margin-bottom:16px;}\n"
    "img{border-radius:12px;max-width:900px;width:100%;"
    "border:1px solid rgba(67,72,68,.3);}\n"
    "p{color:#666;font-size:11px;margin-top:12px;}\n"
    "</style></head>\n"
    "<body>\n"
    "<h2>Audio Spectrogram Analysis &mdash; temp.wav</h2>\n"
    '<img src="' + result + '" alt="mel-spectrogram" />\n'
    "<p>Mel-spectrogram &bull; magma colormap &bull; 64 mel bands &bull; 16 kHz &bull; "
    + str(len(result)) + " char data URI</p>\n"
    "</body></html>\n"
)

out = "spectrogram_preview.html"
with open(out, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"[DONE] Saved {out}  ({len(result):,} char data URI inside)")
print(f"       Open in browser: file://{os.path.abspath(out)}")
