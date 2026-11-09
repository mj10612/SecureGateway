# privacy evaluation

Status: completed

The two quality axes are independent. Missing measurements are not successes.

```json
{
  "privacy": {
    "total_sensitive": 747,
    "measured_sensitive": 747,
    "unmeasured_sensitive": 0,
    "fully_protected": 465,
    "full_exposures": 282,
    "partial_exposures": 0,
    "ambiguous_possible_exposures": 1,
    "accuracy": 0.6224899598393574,
    "observed_accuracy": 0.6224899598393574,
    "requests_with_leak": 86,
    "measured_requests": 102,
    "total_requests": 102
  },
  "overmasking": {
    "measured_public": 282,
    "overmasked": 46,
    "rate": 0.16312056737588654
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
