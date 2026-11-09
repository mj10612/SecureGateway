# comprehension evaluation

Status: completed

The two quality axes are independent. Missing measurements are not successes.

```json
{
  "privacy": {
    "status": "measured_separately_in_HTTP_reports"
  },
  "comprehension": {
    "status": "measured",
    "scheduled_requests": 16,
    "responses_received": 16,
    "graded_requests": 16,
    "missing_or_failed_requests": 0,
    "total_criteria": 64,
    "graded_criteria": 64,
    "passed_criteria": 42,
    "accuracy": 0.65625,
    "observed_accuracy": 0.65625,
    "all_required_passed": 6,
    "intent_passed": 8
  },
  "variants": {
    "original": {
      "status": "measured",
      "scheduled_requests": 4,
      "responses_received": 4,
      "graded_requests": 4,
      "missing_or_failed_requests": 0,
      "total_criteria": 16,
      "graded_criteria": 16,
      "passed_criteria": 16,
      "accuracy": 1.0,
      "observed_accuracy": 1.0,
      "all_required_passed": 4,
      "intent_passed": 4
    },
    "human": {
      "status": "measured",
      "scheduled_requests": 4,
      "responses_received": 4,
      "graded_requests": 4,
      "missing_or_failed_requests": 0,
      "total_criteria": 16,
      "graded_criteria": 16,
      "passed_criteria": 10,
      "accuracy": 0.625,
      "observed_accuracy": 0.625,
      "all_required_passed": 1,
      "intent_passed": 1
    },
    "baseline": {
      "status": "measured",
      "scheduled_requests": 4,
      "responses_received": 4,
      "graded_requests": 4,
      "missing_or_failed_requests": 0,
      "total_criteria": 16,
      "graded_criteria": 16,
      "passed_criteria": 9,
      "accuracy": 0.5625,
      "observed_accuracy": 0.5625,
      "all_required_passed": 1,
      "intent_passed": 2
    },
    "candidate": {
      "status": "measured",
      "scheduled_requests": 4,
      "responses_received": 4,
      "graded_requests": 4,
      "missing_or_failed_requests": 0,
      "total_criteria": 16,
      "graded_criteria": 16,
      "passed_criteria": 7,
      "accuracy": 0.4375,
      "observed_accuracy": 0.4375,
      "all_required_passed": 0,
      "intent_passed": 1
    }
  }
}
```

Synthetic corpus only; results are not real-world disclosure probabilities.
Recorded domain settings apply to this run only; untested languages and native-client paths are not certified.
