# privacy evaluation

Status: completed

The two quality axes are independent. Missing measurements are not successes.

```json
{
  "privacy": {
    "total_sensitive": 2,
    "measured_sensitive": 2,
    "unmeasured_sensitive": 0,
    "fully_protected": 2,
    "full_exposures": 0,
    "partial_exposures": 0,
    "ambiguous_possible_exposures": 0,
    "accuracy": 1.0,
    "observed_accuracy": 1.0,
    "requests_with_leak": 0,
    "measured_requests": 1,
    "total_requests": 1
  },
  "overmasking": {
    "measured_public": 0,
    "overmasked": 0,
    "rate": null
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
