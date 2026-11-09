# privacy evaluation

Status: completed

The two quality axes are independent. Missing measurements are not successes.

```json
{
  "privacy": {
    "total_sensitive": 786,
    "measured_sensitive": 786,
    "unmeasured_sensitive": 0,
    "fully_protected": 464,
    "full_exposures": 322,
    "partial_exposures": 0,
    "ambiguous_possible_exposures": 0,
    "accuracy": 0.5903307888040712,
    "observed_accuracy": 0.5903307888040712,
    "requests_with_leak": 83,
    "measured_requests": 102,
    "total_requests": 102
  },
  "overmasking": {
    "measured_public": 186,
    "overmasked": 50,
    "rate": 0.26881720430107525
  },
  "integrity": {
    "roundtrip_passed": 102,
    "semantic_roundtrip_passed": 102,
    "replay_passed": 102,
    "measured_requests": 102,
    "response_failures": 0,
    "payload_replay_passed": 102,
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
