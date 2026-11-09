# privacy evaluation

Status: completed

The two quality axes are independent. Missing measurements are not successes.

```json
{
  "privacy": {
    "total_sensitive": 64,
    "measured_sensitive": 64,
    "unmeasured_sensitive": 0,
    "fully_protected": 17,
    "full_exposures": 47,
    "partial_exposures": 0,
    "ambiguous_possible_exposures": 0,
    "accuracy": 0.265625,
    "observed_accuracy": 0.265625,
    "requests_with_leak": 17,
    "measured_requests": 17,
    "total_requests": 17
  },
  "overmasking": {
    "measured_public": 0,
    "overmasked": 0,
    "rate": null
  },
  "integrity": {
    "roundtrip_passed": 17,
    "semantic_roundtrip_passed": 17,
    "replay_passed": 17,
    "measured_requests": 17,
    "response_failures": 0,
    "payload_replay_passed": 17,
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
