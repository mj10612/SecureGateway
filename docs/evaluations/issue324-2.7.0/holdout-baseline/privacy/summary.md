# privacy evaluation

Status: completed

The two quality axes are independent. Missing measurements are not successes.

```json
{
  "privacy": {
    "total_sensitive": 747,
    "measured_sensitive": 747,
    "unmeasured_sensitive": 0,
    "fully_protected": 719,
    "full_exposures": 28,
    "partial_exposures": 0,
    "ambiguous_possible_exposures": 0,
    "accuracy": 0.9625167336010709,
    "observed_accuracy": 0.9625167336010709,
    "requests_with_leak": 17,
    "measured_requests": 102,
    "total_requests": 102
  },
  "overmasking": {
    "measured_public": 282,
    "overmasked": 177,
    "rate": 0.6276595744680851
  },
  "integrity": {
    "roundtrip_passed": 85,
    "semantic_roundtrip_passed": 85,
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
