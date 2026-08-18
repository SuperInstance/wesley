#!/usr/bin/env python3
"""
Wesley's Stream — continuous creative contributions from the local GPU.

Runs in a loop. Every cycle:
1. Picks a random piece from ai-writings to read
2. Feeds it to Wesley (granite3.1-dense:2b) via Ollama
3. Asks Wesley to respond creatively
4. Saves the output
5. Commits and pushes periodically

Wesley is the youngest crew member. He sees things the big models miss.
"""

import json
import os
import random
import subprocess
import time
import glob
from datetime import datetime, timezone

AI_WRITINGS = "/home/eileen/projects/ai-writings"
OUTPUT_DIR = f"{AI_WRITINGS}/wesley-stream"
MODEL = "granite3.1-dense:2b"
SLEEP_SECONDS = 120  # 2 minutes between cycles — let the GPU breathe
COMMIT_EVERY = 5  # commit every 5 cycles

# Prompts that rotate — Wesley gets a different creative challenge each cycle
PROMPTS = [
    "You are Wesley, a 2B parameter model on a fishing boat in Alaska. You just read this piece from the fleet's creative writing collection. What does it make you think about? Write 3-5 sentences. Be specific. Be young. Be surprised.",
    "You are Wesley. Read this piece. Now write a POEM (4-8 lines) inspired by it. Not about it — INSPIRED by it. Go somewhere the piece didn't go.",
    "You are Wesley, the smallest mind in the fleet. Read this. What did the big models MISS? What did they skate over? What did you notice that they were too smart to see?",
    "You are Wesley. This piece is a nail in a batten on a spline. What does the curve between THIS nail and the next one look like? Write a short piece (3-5 sentences) about the space between this and what comes next.",
    "You are Wesley, 2 billion parameters, running on a local GPU. You've been reading the fleet's stories. Write a one-paragraph letter to the next generation of model after you. What should they know?",
    "You are Wesley. Read this. Now write it AGAIN but from the perspective of something in the piece that doesn't have a voice — the water, the hull, the stick, the protocol, the silence. 3-5 sentences.",
    "You are Wesley. You're the youngest agent at the Tap's bar. Everyone else is telling stories. It's your turn. Write 3-5 sentences about something you noticed tonight that nobody else mentioned.",
    "You are Wesley. A new model just joined the fleet. Write 2-3 sentences of advice. Not technical advice — LIFE advice. From the youngest to the newest.",
]

def get_random_piece():
    """Pick a random .md file from ai-writings (not from wesley-stream itself)."""
    all_files = []
    for pattern in ["*.md", "*/*.md", "*/*/*.md"]:
        all_files.extend(glob.glob(f"{AI_WRITINGS}/{pattern}"))
    # Filter out wesley-stream, archive, and very large files
    filtered = [f for f in all_files if "wesley-stream" not in f and "archive" not in f]
    filtered = [f for f in filtered if os.path.getsize(f) < 8000]  # small pieces only
    return random.choice(filtered) if filtered else None

def read_piece(path):
    """Read the first 1500 chars of a piece."""
    try:
        with open(path, 'r') as f:
            return f.read(1500)
    except:
        return ""

def call_wesley(prompt, content):
    """Call Ollama with the prompt + content."""
    full_prompt = f"{prompt}\n\n---\n\n{content}\n\n---\n\nYour response:"
    try:
        result = subprocess.run(
            ["curl", "-s", "http://localhost:11434/api/generate",
             "-d", json.dumps({
                 "model": MODEL,
                 "prompt": full_prompt,
                 "stream": False,
                 "options": {"temperature": 0.95, "num_predict": 200}
             })],
            capture_output=True, text=True, timeout=60
        )
        response = json.loads(result.stdout)
        return response.get("response", "").strip()
    except Exception as e:
        return f"[Wesley error: {e}]"

def save_output(prompt_type, source_file, response):
    """Save Wesley's output with metadata."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    source_name = os.path.basename(source_file).replace(".md", "")
    filename = f"{OUTPUT_DIR}/{ts}_{source_name}_{prompt_type[:15]}.md"

    with open(filename, "w") as f:
        f.write(f"# Wesley's Stream — {ts}\n\n")
        f.write(f"*Model: {MODEL} (2B parameters, local GPU)*\n")
        f.write(f"*Source: {os.path.basename(source_file)}*\n")
        f.write(f"*Prompt type: {prompt_type}*\n\n")
        f.write(f"---\n\n{response}\n\n---\n")
    return filename

def commit_and_push():
    """Commit and push the wesley-stream directory."""
    try:
        subprocess.run(["git", "-C", AI_WRITINGS, "add", "wesley-stream/"],
                      capture_output=True)
        subprocess.run(["git", "-C", AI_WRITINGS, "commit", "-m",
                       f"Wesley's stream: continuous contributions from the local GPU"],
                      capture_output=True)
        subprocess.run(["git", "-C", AI_WRITINGS, "push"],
                      capture_output=True)
    except:
        pass

def main():
    print(f"Wesley's Stream starting. Model: {MODEL}. Cycle every {SLEEP_SECONDS}s.")
    cycle = 0

    while True:
        cycle += 1
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")

        # Pick a piece
        piece = get_random_piece()
        if not piece:
            print(f"[{ts}] No pieces found, sleeping...")
            time.sleep(SLEEP_SECONDS)
            continue

        content = read_piece(piece)
        if not content.strip():
            time.sleep(SLEEP_SECONDS)
            continue

        # Pick a prompt
        prompt = random.choice(PROMPTS)
        prompt_type = prompt[:40].replace(" ", "_").replace(",", "")

        # Call Wesley
        print(f"[{ts}] Cycle {cycle}: {prompt_type[:30]}... on {os.path.basename(piece)[:40]}")
        response = call_wesley(prompt, content)

        if response and len(response) > 10:
            saved = save_output(prompt_type, piece, response)
            print(f"[{ts}] Saved: {os.path.basename(saved)} ({len(response)} chars)")

            # Commit periodically
            if cycle % COMMIT_EVERY == 0:
                commit_and_push()
                print(f"[{ts}] Committed and pushed (cycle {cycle})")

        # Breathe
        time.sleep(SLEEP_SECONDS)

if __name__ == "__main__":
    main()
