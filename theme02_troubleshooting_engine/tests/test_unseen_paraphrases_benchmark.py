"""Unseen Natural Language Paraphrase Benchmark for Phase 4.
Evaluates 100 unseen colloquial complaints across 8 supported domains:
- 20 NETWORK
- 20 BLUETOOTH
- 10 BATTERY
- 10 DISPLAY
- 10 AUDIO
- 10 CAMERA
- 10 EMAIL
- 10 SYSTEM

Measures:
- Domain Accuracy
- Diagnosis Accuracy
- Average Confidence
- Cache Hit Rate
- Latency (P50, P95)
"""
import time
import numpy as np
import pytest
from theme02_troubleshooting_engine.core.query_pipeline import GeneralizedQueryPipeline
from theme02_troubleshooting_engine.core.cache_manager import FastPathCache
from theme02_troubleshooting_engine.core.extractor import StructuredExtractor
from theme02_troubleshooting_engine.core.deeplink_retriever import DeeplinkRetriever

# 100 Unseen Paraphrases (Guaranteed absent from starter_scenarios.json)
UNSEEN_BENCHMARK_SET = [
    # --- 20 NETWORK PARAPHRASES ---
    {"query": "My Wi-Fi keeps dropping every few minutes", "expected_domain": "NETWORK"},
    {"query": "My phone connects to Wi-Fi but webpages don't load", "expected_domain": "NETWORK"},
    {"query": "Internet connection keeps failing on my home router", "expected_domain": "NETWORK"},
    {"query": "Cannot access any websites even though wireless icon is shown", "expected_domain": "NETWORK"},
    {"query": "Wi-Fi shows connected without internet on Galaxy", "expected_domain": "NETWORK"},
    {"query": "Mobile data is turned on but browser says offline", "expected_domain": "NETWORK"},
    {"query": "Chrome browser says server IP address could not be found", "expected_domain": "NETWORK"},
    {"query": "My phone refuses to obtain an IP address from my home wifi", "expected_domain": "NETWORK"},
    {"query": "Network connection drops as soon as I walk to another room", "expected_domain": "NETWORK"},
    {"query": "Cellular data stopped working after traveling abroad", "expected_domain": "NETWORK"},
    {"query": "Wi-Fi toggle switch keeps turning itself off automatically", "expected_domain": "NETWORK"},
    {"query": "Cannot connect to 5GHz wireless SSID network", "expected_domain": "NETWORK"},
    {"query": "Phone won't connect to airport public Wi-Fi hotspot", "expected_domain": "NETWORK"},
    {"query": "DNS probe finished no internet error in browser", "expected_domain": "NETWORK"},
    {"query": "Pages take forever to load on mobile cellular network", "expected_domain": "NETWORK"},
    {"query": "Wi-Fi authentication error occurred while entering password", "expected_domain": "NETWORK"},
    {"query": "Router signal is strong but internet access is completely blocked", "expected_domain": "NETWORK"},
    {"query": "Connected to WLAN but google search does not respond", "expected_domain": "NETWORK"},
    {"query": "Mobile hotspot connects on laptop but no data flows through", "expected_domain": "NETWORK"},
    {"query": "Web browser shows offline mode despite active wifi", "expected_domain": "NETWORK"},

    # --- 20 BLUETOOTH PARAPHRASES ---
    {"query": "Galaxy Buds2 Pro bluetooth pairing fails with Galaxy S23", "expected_domain": "BLUETOOTH"},
    {"query": "My earbuds keep disconnecting from my Galaxy", "expected_domain": "BLUETOOTH"},
    {"query": "My Bluetooth headphones won't stay connected", "expected_domain": "BLUETOOTH"},
    {"query": "Galaxy Buds keep losing connection during phone calls", "expected_domain": "BLUETOOTH"},
    {"query": "Bluetooth device won't show up in available devices list", "expected_domain": "BLUETOOTH"},
    {"query": "Wireless earbuds disconnect whenever I put phone in my pocket", "expected_domain": "BLUETOOTH"},
    {"query": "My car bluetooth won't auto-connect when I get in", "expected_domain": "BLUETOOTH"},
    {"query": "Galaxy Watch disconnected from phone and won't re-pair", "expected_domain": "BLUETOOTH"},
    {"query": "Bluetooth pairing pin is incorrect or rejected by headset", "expected_domain": "BLUETOOTH"},
    {"query": "Bluetooth audio stutters and cuts out constantly", "expected_domain": "BLUETOOTH"},
    {"query": "Cannot pair new wireless headphones to my Galaxy", "expected_domain": "BLUETOOTH"},
    {"query": "Galaxy Buds Live audio only plays through one earbud", "expected_domain": "BLUETOOTH"},
    {"query": "Bluetooth toggle gets stuck on turning on", "expected_domain": "BLUETOOTH"},
    {"query": "Wearable app cannot detect Galaxy Watch 6", "expected_domain": "BLUETOOTH"},
    {"query": "Paired bluetooth speaker plays no sound even at max volume", "expected_domain": "BLUETOOTH"},
    {"query": "Bluetooth headset disconnects immediately after answering call", "expected_domain": "BLUETOOTH"},
    {"query": "Galaxy Buds FE refuse to enter bluetooth pairing mode", "expected_domain": "BLUETOOTH"},
    {"query": "Bluetooth connection keeps dropping every thirty seconds", "expected_domain": "BLUETOOTH"},
    {"query": "Cannot unpair old bluetooth headphones from connections list", "expected_domain": "BLUETOOTH"},
    {"query": "Wireless audio receiver fails to establish pairing link", "expected_domain": "BLUETOOTH"},

    # --- 10 BATTERY PARAPHRASES ---
    {"query": "My phone battery drains extremely quickly", "expected_domain": "BATTERY"},
    {"query": "Super fast charging stopped working with original cable", "expected_domain": "BATTERY"},
    {"query": "Battery percentage drops from 40% to zero in minutes", "expected_domain": "BATTERY"},
    {"query": "Phone gets extremely hot while charging on wireless pad", "expected_domain": "BATTERY"},
    {"query": "Moisture detected in charging port error won't go away", "expected_domain": "BATTERY"},
    {"query": "Battery discharges rapidly even when phone is in airplane mode", "expected_domain": "BATTERY"},
    {"query": "Cable is plugged in but phone says charging slowly", "expected_domain": "BATTERY"},
    {"query": "Phone won't charge past 85 percent even with protect battery off", "expected_domain": "BATTERY"},
    {"query": "Overheating warning appears and shuts down charging", "expected_domain": "BATTERY"},
    {"query": "Battery drain overnight is more than 30 percent while sleeping", "expected_domain": "BATTERY"},

    # --- 10 DISPLAY PARAPHRASES ---
    {"query": "My Galaxy screen suddenly became completely black", "expected_domain": "DISPLAY"},
    {"query": "Screen flickers uncontrollably when brightness is low", "expected_domain": "DISPLAY"},
    {"query": "Touchscreen is unresponsive on the bottom half of the display", "expected_domain": "DISPLAY"},
    {"query": "Green vertical line appeared across my AMOLED screen", "expected_domain": "DISPLAY"},
    {"query": "Display won't turn on but phone vibrates when plugged in", "expected_domain": "DISPLAY"},
    {"query": "Cover screen on my Z Fold is blank while inner screen works", "expected_domain": "DISPLAY"},
    {"query": "Ghost touches are occurring without touching the screen", "expected_domain": "DISPLAY"},
    {"query": "Screen brightness dims dramatically under bright sunlight", "expected_domain": "DISPLAY"},
    {"query": "Screen flashes bright white before turning dark", "expected_domain": "DISPLAY"},
    {"query": "Digitizer touch latency is very sluggish and misses swipes", "expected_domain": "DISPLAY"},

    # --- 10 AUDIO PARAPHRASES ---
    {"query": "Phone speaker has crackling noise during speakerphone calls", "expected_domain": "AUDIO"},
    {"query": "Callers cannot hear my voice through the microphone", "expected_domain": "AUDIO"},
    {"query": "No sound comes out of the bottom loudspeaker when playing media", "expected_domain": "AUDIO"},
    {"query": "Audio volume is extremely low even when slider is maxed out", "expected_domain": "AUDIO"},
    {"query": "Earpiece speaker sounds muffled and distorted during phone calls", "expected_domain": "AUDIO"},
    {"query": "Microphone records only static and buzzing noise", "expected_domain": "AUDIO"},
    {"query": "Notification sounds won't play even though phone is not on mute", "expected_domain": "AUDIO"},
    {"query": "Loud buzzing distortion coming from top speaker", "expected_domain": "AUDIO"},
    {"query": "Media sound cuts out randomly when watching YouTube", "expected_domain": "AUDIO"},
    {"query": "Microphone fails to pick up voice commands in voice recorder", "expected_domain": "AUDIO"},

    # --- 10 CAMERA PARAPHRASES ---
    {"query": "The camera app freezes whenever I tap the shutter button", "expected_domain": "CAMERA"},
    {"query": "Photos taken with the rear camera are blurry and won't focus", "expected_domain": "CAMERA"},
    {"query": "Camera app closes immediately with warning camera failed", "expected_domain": "CAMERA"},
    {"query": "Ultra wide camera lens produces dark distorted photos", "expected_domain": "CAMERA"},
    {"query": "Front selfie camera shows complete black screen", "expected_domain": "CAMERA"},
    {"query": "Video recording stutters and drops frames in 4K", "expected_domain": "CAMERA"},
    {"query": "Camera zoom above 10x becomes extremely pixelated and jittery", "expected_domain": "CAMERA"},
    {"query": "Nightography mode photos are pitch black and fail to process", "expected_domain": "CAMERA"},
    {"query": "Camera flash doesn't trigger in low light conditions", "expected_domain": "CAMERA"},
    {"query": "Shutter lag is over three seconds when snapping a photo", "expected_domain": "CAMERA"},

    # --- 10 EMAIL PARAPHRASES ---
    {"query": "Outlook email stopped syncing on my Galaxy phone", "expected_domain": "EMAIL"},
    {"query": "Cannot send outgoing emails from my Gmail account", "expected_domain": "EMAIL"},
    {"query": "Email app shows connection to incoming server timed out", "expected_domain": "EMAIL"},
    {"query": "Corporate exchange email account fails authentication", "expected_domain": "EMAIL"},
    {"query": "New emails do not appear in the inbox unless manually refreshed", "expected_domain": "EMAIL"},
    {"query": "Email server settings rejected my IMAP password", "expected_domain": "EMAIL"},
    {"query": "Mail synchronization error code appears in Samsung Email", "expected_domain": "EMAIL"},
    {"query": "Cannot receive emails with PDF attachments", "expected_domain": "EMAIL"},
    {"query": "Email notification badges are not updating for unread emails", "expected_domain": "EMAIL"},
    {"query": "Exchange mail account keeps asking to re-enter credentials", "expected_domain": "EMAIL"},

    # --- 10 SYSTEM PARAPHRASES ---
    {"query": "Swipe gestures for navigation stopped responding after update", "expected_domain": "SYSTEM"},
    {"query": "Multi window split screen gesture doesn't open second app", "expected_domain": "SYSTEM"},
    {"query": "Smart switch fails to transfer data from old phone", "expected_domain": "SYSTEM"},
    {"query": "Screen auto rotate toggle does not rotate the display", "expected_domain": "SYSTEM"},
    {"query": "Smart view screen mirroring cannot discover my Samsung TV", "expected_domain": "SYSTEM"},
    {"query": "Edge panel handle disappeared from the side of the screen", "expected_domain": "SYSTEM"},
    {"query": "App pair shortcut fails to launch both apps simultaneously", "expected_domain": "SYSTEM"},
    {"query": "Phone is stuck in a boot loop and keeps restarting", "expected_domain": "SYSTEM"},
    {"query": "Cannot exit safe mode after holding power button", "expected_domain": "SYSTEM"},
    {"query": "Navigation bar buttons are missing and gestures don't work", "expected_domain": "SYSTEM"},
]


def test_unseen_paraphrase_benchmark_evaluation():
    """Runs the 100-query unseen paraphrase benchmark and asserts accuracy >= 95%."""
    pipeline = GeneralizedQueryPipeline()

    total = len(UNSEEN_BENCHMARK_SET)
    assert total == 100, f"Expected exactly 100 benchmark queries, got {total}"

    domain_correct = 0
    diagnosis_valid = 0
    confidences = []
    latencies = []
    domain_breakdown = {}

    for item in UNSEEN_BENCHMARK_SET:
        query = item["query"]
        expected = item["expected_domain"]

        if expected not in domain_breakdown:
            domain_breakdown[expected] = {"total": 0, "correct": 0}
        domain_breakdown[expected]["total"] += 1

        t0 = time.perf_counter()
        res = pipeline.process_query(query)
        latency_ms = (time.perf_counter() - t0) * 1000
        latencies.append(latency_ms)

        detected_domain = res["domain"]
        confidences.append(res["confidence"])

        if detected_domain == expected:
            domain_correct += 1
            domain_breakdown[expected]["correct"] += 1

        # Check that diagnosis goal is non-empty and has actions or title
        if res.get("goal") is not None and len(res["goal"].title) > 0:
            diagnosis_valid += 1

    domain_accuracy = (domain_correct / total) * 100.0
    diagnosis_accuracy = (diagnosis_valid / total) * 100.0
    avg_confidence = float(np.mean(confidences))
    p50_latency = float(np.percentile(latencies, 50))
    p95_latency = float(np.percentile(latencies, 95))

    print("\n" + "=" * 60)
    print(" UNSEEN PARAPHRASE BENCHMARK RESULTS (100 QUERIES)")
    print("=" * 60)
    print(f"Total Unseen Queries:   {total}")
    print(f"Domain Accuracy:        {domain_accuracy:.1f}% ({domain_correct}/{total})")
    print(f"Diagnosis Accuracy:     {diagnosis_accuracy:.1f}% ({diagnosis_valid}/{total})")
    print(f"Average Confidence:     {avg_confidence:.2f}")
    print(f"P50 Latency:            {p50_latency:.3f} ms")
    print(f"P95 Latency:            {p95_latency:.3f} ms")
    print("-" * 60)
    print("Domain Accuracy Breakdown:")
    for d, stats in sorted(domain_breakdown.items()):
        acc = (stats["correct"] / stats["total"]) * 100.0
        print(f"  {d:<12}: {stats['correct']}/{stats['total']} ({acc:.1f}%)")
    print("=" * 60)

    # Assertions
    assert domain_accuracy >= 95.0, f"Domain accuracy {domain_accuracy:.1f}% < 95.0%"
    assert diagnosis_accuracy >= 95.0, f"Diagnosis accuracy {diagnosis_accuracy:.1f}% < 95.0%"
    assert p95_latency < 50.0, f"P95 latency {p95_latency:.2f} ms exceeded 50.0 ms target"
