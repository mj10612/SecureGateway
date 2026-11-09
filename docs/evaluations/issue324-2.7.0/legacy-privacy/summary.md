# privacy evaluation

Status: completed

The two quality axes are independent. Missing measurements are not successes.

```json
{
  "privacy": {
    "total_sensitive": 66,
    "measured_sensitive": 66,
    "unmeasured_sensitive": 0,
    "fully_protected": 57,
    "full_exposures": 9,
    "partial_exposures": 0,
    "ambiguous_possible_exposures": 0,
    "accuracy": 0.8636363636363636,
    "observed_accuracy": 0.8636363636363636,
    "requests_with_leak": 9,
    "measured_requests": 32,
    "total_requests": 32
  },
  "overmasking": {
    "measured_public": 117,
    "overmasked": 30,
    "rate": 0.2564102564102564
  },
  "integrity": {
    "roundtrip_passed": 31,
    "semantic_roundtrip_passed": 32,
    "replay_passed": 32,
    "measured_requests": 32,
    "response_failures": 0,
    "payload_replay_passed": 32,
    "session_isolation": true,
    "snapshot_restart": true
  },
  "comprehension": {
    "status": "not_measured"
  }
}
```

Synthetic corpus only; results are not real-world disclosure probabilities.
Recorded domain settings apply to this run only; untested languages and native-client paths are not certified.
