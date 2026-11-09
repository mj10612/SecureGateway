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
    "scheduled_requests": 204,
    "responses_received": 204,
    "graded_requests": 204,
    "missing_or_failed_requests": 0,
    "total_criteria": 816,
    "graded_criteria": 816,
    "passed_criteria": 716,
    "accuracy": 0.8774509803921569,
    "observed_accuracy": 0.8774509803921569,
    "all_required_passed": 149,
    "intent_passed": 187
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
      "passed_criteria": 195,
      "accuracy": 0.9558823529411765,
      "observed_accuracy": 0.9558823529411765,
      "all_required_passed": 45,
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
      "passed_criteria": 194,
      "accuracy": 0.9509803921568627,
      "observed_accuracy": 0.9509803921568627,
      "all_required_passed": 43,
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
      "passed_criteria": 144,
      "accuracy": 0.7058823529411765,
      "observed_accuracy": 0.7058823529411765,
      "all_required_passed": 23,
      "intent_passed": 37
    },
    "candidate": {
      "status": "measured",
      "scheduled_requests": 51,
      "responses_received": 51,
      "graded_requests": 51,
      "missing_or_failed_requests": 0,
      "total_criteria": 204,
      "graded_criteria": 204,
      "passed_criteria": 183,
      "accuracy": 0.8970588235294118,
      "observed_accuracy": 0.8970588235294118,
      "all_required_passed": 38,
      "intent_passed": 48
    }
  }
}
```

Synthetic corpus only; results are not real-world disclosure probabilities.
Recorded domain settings apply to this run only; untested languages and native-client paths are not certified.
