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
    "passed_criteria": 44,
    "accuracy": 0.6875,
    "observed_accuracy": 0.6875,
    "all_required_passed": 1,
    "intent_passed": 1
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
      "passed_criteria": 13,
      "accuracy": 0.8125,
      "observed_accuracy": 0.8125,
      "all_required_passed": 1,
      "intent_passed": 1
    },
    "human": {
      "status": "measured",
      "scheduled_requests": 4,
      "responses_received": 4,
      "graded_requests": 4,
      "missing_or_failed_requests": 0,
      "total_criteria": 16,
      "graded_criteria": 16,
      "passed_criteria": 12,
      "accuracy": 0.75,
      "observed_accuracy": 0.75,
      "all_required_passed": 0,
      "intent_passed": 0
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
      "all_required_passed": 0,
      "intent_passed": 0
    },
    "candidate": {
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
      "all_required_passed": 0,
      "intent_passed": 0
    }
  }
}
```

Synthetic corpus only; results are not real-world disclosure probabilities.
Recorded domain settings apply to this run only; untested languages and native-client paths are not certified.
