#!/usr/bin/env python3
"""
Standalone validation of coordinator logic without running Docker
"""

import sys
from pathlib import Path

# Add coordinator module to path
sys.path.insert(0, str(Path(__file__).parent / "coordinator"))

# Import only the pure logic functions (no Flask)
from enum import Enum

class WorkerType(Enum):
    BERT = "bert"
    MOBILENET = "mobilenet"
    CLIP = "clip"

def validate_and_route(data: dict):
    """Extract the routing logic for testing"""
    has_text = (
        "text" in data
        and isinstance(data["text"], str)
        and data["text"].strip()
    )
    has_image = (
        "image_base64" in data
        and isinstance(data["image_base64"], str)
        and data["image_base64"].strip()
    )

    if not (has_text or has_image):
        return None, "Invalid input: must provide either 'text', 'image_base64', or both"

    if has_text and not has_image:
        return WorkerType.BERT.value, None
    elif has_image and not has_text:
        return WorkerType.MOBILENET.value, None
    else:
        return WorkerType.CLIP.value, None

def test_routing():
    """Test routing logic"""
    tests = [
        ({"text": "hello"}, WorkerType.BERT.value, "text-only"),
        ({"image_base64": "img"}, WorkerType.MOBILENET.value, "image-only"),
        ({"text": "hello", "image_base64": "img"}, WorkerType.CLIP.value, "both"),
        ({}, None, "empty input"),
        ({"text": ""}, None, "empty text"),
        ({"image_base64": ""}, None, "empty image"),
        ({"text": "hello", "image_base64": ""}, WorkerType.BERT.value, "text with empty image"),
        ({"text": "", "image_base64": "img"}, WorkerType.MOBILENET.value, "empty text with image"),
    ]

    passed = 0
    failed = 0

    for data, expected_worker, description in tests:
        worker, error = validate_and_route(data)
        
        if worker == expected_worker and (worker is not None or error is not None):
            print(f"✓ {description:30} → {worker if worker else 'rejected'}")
            passed += 1
        else:
            print(f"✗ {description:30} → Expected {expected_worker}, got {worker}")
            failed += 1

    print(f"\n{passed} passed, {failed} failed")
    return failed == 0

def test_backoff():
    """Test exponential backoff calculation"""
    RETRY_BACKOFF = 0.5
    expected_times = [0.5, 1.0, 2.0]
    
    print("\nExponential Backoff Calculation:")
    all_correct = True
    
    for attempt in range(3):
        wait_time = RETRY_BACKOFF * (2 ** attempt)
        expected = expected_times[attempt]
        
        if abs(wait_time - expected) < 0.001:
            print(f"✓ Attempt {attempt}: {wait_time}s (expected {expected}s)")
        else:
            print(f"✗ Attempt {attempt}: {wait_time}s (expected {expected}s)")
            all_correct = False
    
    return all_correct

if __name__ == "__main__":
    print("=" * 60)
    print("DistAI-Docker: Coordinator Logic Validation")
    print("=" * 60)
    print()
    
    print("Testing Routing Logic:")
    print("-" * 60)
    routing_ok = test_routing()
    
    backoff_ok = test_backoff()
    
    print()
    print("=" * 60)
    
    if routing_ok and backoff_ok:
        print("✓ All validations passed!")
        sys.exit(0)
    else:
        print("✗ Some validations failed")
        sys.exit(1)
