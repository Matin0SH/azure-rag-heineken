"""
Test the improved JSON cleaning function using JSONDecoder
"""
import json

def clean_llm_json_output(raw_text: str) -> str:
    """Clean and extract JSON array from LLM output using JSONDecoder."""
    if not raw_text or not raw_text.strip():
        raise ValueError("Empty input")

    # Remove common LLM tokens
    text = raw_text.strip()
    for token in ["<|python_start|>", "<|python_end|>", "<|im_start|>",
                  "<|im_end|>", "```json", "```", "```python"]:
        text = text.replace(token, "")

    text = text.strip()

    # Find first [ bracket
    start_pos = text.find('[')
    if start_pos == -1:
        raise ValueError("No JSON array found (missing '[')")

    # Use JSONDecoder to parse from that position
    decoder = json.JSONDecoder()

    try:
        parsed_data, end_pos = decoder.raw_decode(text, start_pos)

        # Validate it's a non-empty list
        if not isinstance(parsed_data, list):
            raise ValueError(f"Expected array, got {type(parsed_data).__name__}")

        if len(parsed_data) == 0:
            raise ValueError("JSON array is empty")

        # Re-serialize for consistency
        return json.dumps(parsed_data, ensure_ascii=False)

    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON at position {e.pos}: {e.msg}")


# Test cases
test_cases = [
    # Test 1: Clean JSON (should work)
    {
        "name": "Clean JSON array",
        "input": '[{"q": "What is?", "a": "B"}]',
        "should_pass": True
    },

    # Test 2: JSON with prefix token
    {
        "name": "JSON with <|python_start|> prefix",
        "input": '<|python_start|>[{"q": "What is?", "a": "B"}]',
        "should_pass": True
    },

    # Test 3: JSON with extra text after
    {
        "name": "JSON with garbage after",
        "input": '[{"q": "What is?", "a": "B"}]\nSome extra thoughts here...',
        "should_pass": True
    },

    # Test 4: Real problematic case from database
    {
        "name": "Real case with prefix and suffix",
        "input": '''<|python_start|>[
  {
    "question_text": "What should you check?",
    "options": {"A": "Option A", "B": "Option B"},
    "correct_answer": "B"
  }
]
Extra thoughts from the AI
Maybe I should explain...
''',
        "should_pass": True
    },

    # Test 5: No JSON array
    {
        "name": "No JSON array (should fail)",
        "input": "Just some text without JSON",
        "should_pass": False
    },

    # Test 6: Nested arrays (complex)
    {
        "name": "Nested arrays",
        "input": '[{"options": ["A", "B", "C"]}, {"data": [[1,2],[3,4]]}]',
        "should_pass": True
    }
]

print("=" * 80)
print("TESTING IMPROVED JSON CLEANING FUNCTION")
print("=" * 80)

passed = 0
failed = 0

for i, test in enumerate(test_cases, 1):
    print(f"\nTest {i}: {test['name']}")
    print("-" * 80)

    try:
        result = clean_llm_json_output(test['input'])
        parsed = json.loads(result)

        if test['should_pass']:
            print(f"OK: Passed (extracted {len(parsed)} items)")
            print(f"First 100 chars: {result[:100]}")
            passed += 1
        else:
            print(f"FAILED: Should have raised error but didn't")
            failed += 1

    except ValueError as e:
        if not test['should_pass']:
            print(f"OK: Correctly failed with: {str(e)[:100]}")
            passed += 1
        else:
            print(f"FAILED: {str(e)[:100]}")
            failed += 1

print("\n" + "=" * 80)
print(f"RESULTS: {passed}/{len(test_cases)} tests passed")
if failed == 0:
    print("SUCCESS: All tests passed!")
else:
    print(f"WARNING: {failed} tests failed")
print("=" * 80)
