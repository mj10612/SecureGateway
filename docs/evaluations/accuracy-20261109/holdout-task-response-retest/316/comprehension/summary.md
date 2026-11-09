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
    "passed_criteria": 58,
    "accuracy": 0.90625,
    "observed_accuracy": 0.90625,
    "all_required_passed": 12,
    "intent_passed": 12
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
      "passed_criteria": 16,
      "accuracy": 1.0,
      "observed_accuracy": 1.0,
      "all_required_passed": 4,
      "intent_passed": 4
    },
    "baseline": {
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
      "all_required_passed": 2,
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
      "passed_criteria": 14,
      "accuracy": 0.875,
      "observed_accuracy": 0.875,
      "all_required_passed": 2,
      "intent_passed": 2
    }
  }
}
```

Synthetic corpus only; results are not real-world disclosure probabilities.
Recorded domain settings apply to this run only; untested languages and native-client paths are not certified.
