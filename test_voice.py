import requests
import sys

API = "http://localhost:8000"

# ── Test Voice ───────────────────────────────────────────────────
def test_voice(file_path):
    print(f"\n[VOICE] Testing: {file_path}")
    with open(file_path, "rb") as f:
        r = requests.post(f"{API}/analyze/voice",
                          files={"audio": ("recording.wav", f, "audio/wav")})
    import json
    print(json.dumps(r.json(), indent=2))

# ── Test Video ───────────────────────────────────────────────────
def test_video(file_path):
    print(f"\n[VIDEO] Testing: {file_path}")
    with open(file_path, "rb") as f:
        r = requests.post(f"{API}/analyze/video",
                          files={"video": (file_path.split("\\")[-1], f, "video/mp4")})
    import json
    print(json.dumps(r.json(), indent=2))

# ── Run ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Default voice test
    voice_file = r"C:\Users\kanis\OneDrive\Desktop\recordings\WhatsApp Audio 2026-04-02 at 00.56.22.wav"
    test_voice(voice_file)

    # Uncomment and set path to test video:
    # test_video(r"C:\path\to\your\video.mp4")
