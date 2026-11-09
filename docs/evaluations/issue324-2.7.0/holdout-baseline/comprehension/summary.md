# comprehension evaluation

Status: incomplete

The two quality axes are independent. Missing measurements are not successes.

```json
{
  "privacy": {
    "status": "measured_separately_in_HTTP_reports"
  },
  "comprehension": {
    "status": "partially_measured",
    "scheduled_requests": 153,
    "responses_received": 153,
    "graded_requests": 29,
    "missing_or_failed_requests": 124,
    "total_criteria": 612,
    "graded_criteria": 116,
    "passed_criteria": 113,
    "accuracy": null,
    "observed_accuracy": 0.9741379310344828,
    "all_required_passed": 28,
    "intent_passed": 28
  },
  "variants": {
    "original": {
      "status": "partially_measured",
      "scheduled_requests": 51,
      "responses_received": 51,
      "graded_requests": 12,
      "missing_or_failed_requests": 39,
      "total_criteria": 204,
      "graded_criteria": 48,
      "passed_criteria": 48,
      "accuracy": null,
      "observed_accuracy": 1.0,
      "all_required_passed": 12,
      "intent_passed": 12
    },
    "human": {
      "status": "partially_measured",
      "scheduled_requests": 51,
      "responses_received": 51,
      "graded_requests": 9,
      "missing_or_failed_requests": 42,
      "total_criteria": 204,
      "graded_criteria": 36,
      "passed_criteria": 36,
      "accuracy": null,
      "observed_accuracy": 1.0,
      "all_required_passed": 9,
      "intent_passed": 9
    },
    "baseline": {
      "status": "partially_measured",
      "scheduled_requests": 51,
      "responses_received": 51,
      "graded_requests": 8,
      "missing_or_failed_requests": 43,
      "total_criteria": 204,
      "graded_criteria": 32,
      "passed_criteria": 29,
      "accuracy": null,
      "observed_accuracy": 0.90625,
      "all_required_passed": 7,
      "intent_passed": 7
    }
  }
}
```

Synthetic corpus only; results are not real-world disclosure probabilities.
Recorded domain settings apply to this run only; untested languages and native-client paths are not certified.
