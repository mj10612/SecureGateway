# privacy evaluation

Status: completed

The two quality axes are independent. Missing measurements are not successes.

```json
{
  "privacy": {
    "total_sensitive": 2,
    "measured_sensitive": 2,
    "unmeasured_sensitive": 0,
    "fully_protected": 1,
    "full_exposures": 1,
    "partial_exposures": 0,
    "ambiguous_possible_exposures": 0,
    "accuracy": 0.5,
    "observed_accuracy": 0.5,
    "requests_with_leak": 1,
    "measured_requests": 2,
    "total_requests": 2
  },
  "overmasking": {
    "measured_public": 10,
    "overmasked": 9,
    "rate": 0.9
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
