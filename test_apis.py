"""Quick test script to verify API connections."""

import sys

print("Testing API connections...", flush=True)

# Test 1: Import test
print("\n[TEST 1] Testing imports...", flush=True)
try:
    from src.services import TavilyService, DeepSeekService
    print("✅ Imports successful", flush=True)
except Exception as e:
    print(f"❌ Import failed: {e}", flush=True)
    sys.exit(1)

# Test 2: Get API keys
print("\n[TEST 2] Enter API keys", flush=True)
deepseek_key = input("DeepSeek API Key: ").strip()
tavily_key = input("Tavily API Key: ").strip()

if not deepseek_key or not tavily_key:
    print("❌ API keys required", flush=True)
    sys.exit(1)

print("✅ API keys provided", flush=True)

# Test 3: Initialize services
print("\n[TEST 3] Initializing services...", flush=True)
try:
    tavily = TavilyService(tavily_key)
    deepseek = DeepSeekService(deepseek_key)
    print("✅ Services initialized", flush=True)
except Exception as e:
    print(f"❌ Initialization failed: {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Test Tavily search
print("\n[TEST 4] Testing Tavily search...", flush=True)
try:
    results = tavily.search("biopharma oncology clinical trial", max_results=3)
    print(f"✅ Tavily search returned {len(results)} results", flush=True)
    if results:
        print(f"   First result: {results[0].get('title', 'No title')}", flush=True)
except Exception as e:
    print(f"❌ Tavily search failed: {e}", flush=True)
    import traceback
    traceback.print_exc()

# Test 5: Test DeepSeek V3
print("\n[TEST 5] Testing DeepSeek V3...", flush=True)
try:
    response = deepseek.call_v3(
        system_prompt="You are a helpful assistant. Respond with JSON only.",
        user_prompt='Return this JSON: {"status": "working", "test": true}'
    )
    print(f"✅ DeepSeek V3 returned {len(response)} chars", flush=True)
    print(f"   Response preview: {response[:100]}...", flush=True)
except Exception as e:
    print(f"❌ DeepSeek V3 failed: {e}", flush=True)
    import traceback
    traceback.print_exc()

# Test 6: Test DeepSeek R1
print("\n[TEST 6] Testing DeepSeek R1...", flush=True)
try:
    response = deepseek.call_r1(
        system_prompt="You are a helpful assistant. Respond with JSON only.",
        user_prompt='Return this JSON: {"status": "working", "test": true}'
    )
    print(f"✅ DeepSeek R1 returned {len(response)} chars", flush=True)
    print(f"   Response preview: {response[:100]}...", flush=True)
except Exception as e:
    print(f"❌ DeepSeek R1 failed: {e}", flush=True)
    import traceback
    traceback.print_exc()

print("\n" + "="*60, flush=True)
print("API CONNECTION TEST COMPLETE", flush=True)
print("="*60, flush=True)
