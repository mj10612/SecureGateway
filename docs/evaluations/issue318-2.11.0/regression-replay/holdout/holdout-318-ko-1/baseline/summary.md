# privacy evaluation

Status: completed

The two quality axes are independent. Missing measurements are not successes.

```json
{
  "privacy": {
    "total_sensitive": 3,
    "measured_sensitive": 3,
    "unmeasured_sensitive": 0,
    "fully_protected": 1,
    "full_exposures": 2,
    "partial_exposures": 0,
    "ambiguous_possible_exposures": 0,
    "accuracy": 0.3333333333333333,
    "observed_accuracy": 0.3333333333333333,
    "requests_with_leak": 1,
    "measured_requests": 1,
    "total_requests": 1
  },
  "overmasking": {
    "measured_public": 5,
    "overmasked": 0,
    "rate": 0.0
  },
  "integrity": {
    "roundtrip_passed": 1,
    "semantic_roundtrip_passed": 1,
    "replay_passed": 1,
    "measured_requests": 1,
    "response_failures": 0,
    "payload_replay_passed": 1,
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
