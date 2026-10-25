"""Runner for Sarthi test suite without third-party runner dependencies."""

import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import tests.test_pipeline as tp
import tests.test_risk_profiler as trp

def run_all_tests():
    print("=" * 60)
    print("SARTHI DECISION SUPPORT SYSTEM: TEST SUITE EXECUTION")
    print("=" * 60)

    tests = [
        ("Step 1: Scanner & Source Hierarchy", tp.test_step1_scanner),
        ("Step 2: Event Classifier", tp.test_step2_classifier),
        ("Step 4: Confirmation Gate (Drop Tier 3 Rumors)", tp.test_step4_confirmation_gate),
        ("Step 5: Reasoner & Anti-Hallucination Grounding", tp.test_step5_reasoner_anti_hallucination),
        ("Step 6: Constraint Gate (Forbidden Numeric Ban)", tp.test_step6_constraint_gate_blocks_forbidden_claims),
        ("7-Step End-to-End Pipeline Orchestration", tp.test_full_pipeline_orchestration),
        ("Kahneman-Thaler Rationality Gap Detection", trp.test_rationality_gap_detection),
        ("Consistent Behavioral Risk Calibration", trp.test_consistent_patient_investor)
    ]

    passed = 0
    for name, test_func in tests:
        try:
            test_func()
            print(f"  [PASS] {name}")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")

    print("-" * 60)
    print(f"Results: {passed}/{len(tests)} tests passed.")
    print("=" * 60)
    if passed == len(tests):
        print("ALL TESTS PASSED SUCCESSFULLY.")
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    run_all_tests()
