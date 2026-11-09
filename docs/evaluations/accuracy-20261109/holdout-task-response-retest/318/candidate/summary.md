# privacy evaluation

Status: completed

The two quality axes are independent. Missing measurements are not successes.

```json
{
  "privacy": {
    "total_sensitive": 6,
    "measured_sensitive": 6,
    "unmeasured_sensitive": 0,
    "fully_protected": 6,
    "full_exposures": 0,
    "partial_exposures": 0,
    "ambiguous_possible_exposures": 0,
    "accuracy": 1.0,
    "observed_accuracy": 1.0,
    "requests_with_leak": 0,
    "measured_requests": 2,
    "total_requests": 2
  },
  "overmasking": {
    "measured_public": 10,
    "overmasked": 8,
    "rate": 0.8
  },
  "integrity": {
    "roundtrip_passed": 2,
    "semantic_roundtrip_passed": 2,
    "replay_passed": 2,
    "measured_requests": 2,
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
