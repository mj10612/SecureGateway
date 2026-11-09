# privacy evaluation

Status: completed

The two quality axes are independent. Missing measurements are not successes.

```json
{
  "privacy": {
    "total_sensitive": 786,
    "measured_sensitive": 786,
    "unmeasured_sensitive": 0,
    "fully_protected": 703,
    "full_exposures": 83,
    "partial_exposures": 0,
    "ambiguous_possible_exposures": 2,
    "accuracy": 0.8944020356234097,
    "observed_accuracy": 0.8944020356234097,
    "requests_with_leak": 37,
    "measured_requests": 102,
    "total_requests": 102
  },
  "overmasking": {
    "measured_public": 186,
    "overmasked": 95,
    "rate": 0.510752688172043
  },
  "integrity": {
    "roundtrip_passed": 101,
    "semantic_roundtrip_passed": 101,
    "replay_passed": 101,
    "measured_requests": 102,
    "response_failures": 1,
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
