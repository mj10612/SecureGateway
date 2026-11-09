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
    "scheduled_requests": 153,
    "responses_received": 153,
    "graded_requests": 153,
    "missing_or_failed_requests": 0,
    "total_criteria": 612,
    "graded_criteria": 612,
    "passed_criteria": 540,
    "accuracy": 0.8823529411764706,
    "observed_accuracy": 0.8823529411764706,
    "all_required_passed": 116,
    "intent_passed": 139
  },
  "variants": {
    "original": {
      "status": "measured",
      "scheduled_requests": 51,
      "responses_received": 51,
      "graded_requests": 51,
      "missing_or_failed_requests": 0,
      "total_criteria": 204,
      "graded_criteria": 204,
      "passed_criteria": 191,
      "accuracy": 0.9362745098039216,
      "observed_accuracy": 0.9362745098039216,
      "all_required_passed": 42,
      "intent_passed": 51
    },
    "human": {
      "status": "measured",
      "scheduled_requests": 51,
      "responses_received": 51,
      "graded_requests": 51,
      "missing_or_failed_requests": 0,
      "total_criteria": 204,
      "graded_criteria": 204,
      "passed_criteria": 197,
      "accuracy": 0.9656862745098039,
      "observed_accuracy": 0.9656862745098039,
      "all_required_passed": 46,
      "intent_passed": 51
    },
    "baseline": {
      "status": "measured",
      "scheduled_requests": 51,
      "responses_received": 51,
      "graded_requests": 51,
      "missing_or_failed_requests": 0,
      "total_criteria": 204,
      "graded_criteria": 204,
      "passed_criteria": 152,
      "accuracy": 0.7450980392156863,
      "observed_accuracy": 0.7450980392156863,
      "all_required_passed": 28,
      "intent_passed": 37
    }
  }
}
```

Synthetic corpus only; results are not real-world disclosure probabilities.
Recorded domain settings apply to this run only; untested languages and native-client paths are not certified.
