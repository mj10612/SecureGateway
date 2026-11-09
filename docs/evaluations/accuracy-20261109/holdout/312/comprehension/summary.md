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
    "passed_criteria": 41,
    "accuracy": 0.640625,
    "observed_accuracy": 0.640625,
    "all_required_passed": 5,
    "intent_passed": 10
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
      "passed_criteria": 15,
      "accuracy": 0.9375,
      "observed_accuracy": 0.9375,
      "all_required_passed": 3,
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
      "passed_criteria": 14,
      "accuracy": 0.875,
      "observed_accuracy": 0.875,
      "all_required_passed": 2,
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
      "passed_criteria": 4,
      "accuracy": 0.25,
      "observed_accuracy": 0.25,
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
      "passed_criteria": 8,
      "accuracy": 0.5,
      "observed_accuracy": 0.5,
      "all_required_passed": 0,
      "intent_passed": 2
    }
  }
}
```

Synthetic corpus only; results are not real-world disclosure probabilities.
Recorded domain settings apply to this run only; untested languages and native-client paths are not certified.
