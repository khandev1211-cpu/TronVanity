"""
End-to-End Real-Life Test Script for TRON GPU Mining System.
Pushes a vanity pattern request to VPS Redis 'gpu_queue' at 167.172.140.20:6379,
and listens for real-time status and generated result from the Vast.ai GPU Worker Node.
"""

import time
import json
import redis

REDIS_HOST = "167.172.140.20"
REDIS_PORT = 6379

def run_end_to_end_test(pattern: str = "TX...99"):
    print("==================================================")
    print("🧪 TRON GPU Mining End-to-End Real-Life Test")
    print("==================================================")
    print(f"[*] Connecting to VPS Redis ({REDIS_HOST}:{REDIS_PORT})...")

    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, protocol=2, decode_responses=True)
        if not r.ping():
            print("❌ [ERROR] Could not connect to VPS Redis!")
            return
    except Exception as e:
        print(f"❌ [ERROR] Redis Connection Error: {e}")
        return

    print("✅ [OK] Connected to VPS Redis!")

    # Clean previous status/result for this pattern
    r.delete(f"mine_status:{pattern}")
    r.delete(f"mine_result:{pattern}")

    # Push task to gpu_queue
    task_payload = json.dumps({"pattern": pattern})
    r.lpush("gpu_queue", task_payload)
    print(f"🚀 [TASK PUSHED] Pushed pattern '{pattern}' to 'gpu_queue' on VPS Redis!")
    print("[*] Waiting for Vast.ai GPU Node worker to pick up and process task...\n")

    start_time = time.time()
    last_status = None

    while time.time() - start_time < 300: # Wait up to 5 minutes
        status = r.get(f"mine_status:{pattern}")
        mode = r.get(f"mine_mode:{pattern}")

        if status and status != last_status:
            print(f"⏱️ [{int(time.time() - start_time)}s] Status: {status.upper()} | Miner: {mode or 'GPU Node'}")
            last_status = status

        result_raw = r.get(f"mine_result:{pattern}")
        if result_raw:
            print("\n==================================================")
            print("🎉 [SUCCESS] REAL-TIME RESULT RECEIVED FROM GPU NODE!")
            print("==================================================")
            try:
                res = json.loads(result_raw)
                print(f"📍 Address:     {res.get('address')}")
                print(f"🔑 Private Key: {res.get('private_key')}")
                print(f"⏱️ Time Taken:  {int(time.time() - start_time)} seconds")
            except Exception as e:
                print(f"Raw Result: {result_raw}")
            print("==================================================")
            return

        time.sleep(1)

    print("⚠️ [TIMEOUT] No result received within 5 minutes. Check if GPU worker is running on Vast.ai.")

if __name__ == "__main__":
    import sys
    test_pattern = sys.argv[1] if len(sys.argv) > 1 else "TX...99"
    run_end_to_end_test(test_pattern)
