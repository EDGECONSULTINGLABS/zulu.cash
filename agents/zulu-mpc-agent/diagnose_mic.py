"""
Quick microphone diagnostic to test if audio capture is working.
"""

import sounddevice as sd
import numpy as np
import time

print("\n" + "="*60)
print("Microphone Diagnostic")
print("="*60 + "\n")

# Show available devices
print("[*] Available audio input devices:")
devices = sd.query_devices()
for i, dev in enumerate(devices):
    if dev['max_input_channels'] > 0:
        default = " (DEFAULT)" if i == sd.default.device[0] else ""
        print(f"  [{i}] {dev['name']}{default}")

print(f"\n[*] Using default input device: {sd.default.device[0]}")
print("[*] Testing microphone for 5 seconds...")
print("[*] Please speak or make noise...\n")

# Record 5 seconds
duration = 5
samplerate = 16000

try:
    recording = sd.rec(
        int(duration * samplerate),
        samplerate=samplerate,
        channels=1,
        dtype=np.int16,
    )
    
    # Show progress
    for i in range(duration):
        time.sleep(1)
        print(f"  Recording... {i+1}/{duration}s")
    
    sd.wait()
    
    # Analyze results
    print(f"\n[OK] Recording complete!")
    print(f"  - Samples captured: {len(recording)}")
    print(f"  - Duration: {len(recording) / samplerate:.1f}s")
    print(f"  - Max amplitude: {np.max(np.abs(recording))}")
    print(f"  - Mean amplitude: {np.mean(np.abs(recording)):.1f}")
    
    if np.max(np.abs(recording)) < 100:
        print("\n[!] WARNING: Very low audio levels!")
        print("    - Check if microphone is muted")
        print("    - Check microphone permissions in Windows settings")
        print("    - Try speaking louder or closer to mic")
    else:
        print("\n[OK] ✅ Microphone is working!")
        print("    Audio levels look good.")
        
except Exception as e:
    print(f"\n[X] ERROR: {e}")
    print("\n[*] Troubleshooting:")
    print("  1. Check Windows microphone permissions")
    print("  2. Make sure mic isn't muted")
    print("  3. Try selecting a different input device")
    print("  4. Test mic in Windows sound settings first")

print("\n" + "="*60 + "\n")
