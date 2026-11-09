# Reliable multilingual evaluation

Status: incomplete
Split: development; repeats: 3; grading policy: 2

Privacy and task-response scores are separate. Development scores cannot authorize adoption.
Capture reports retain synthetic alias-to-original source maps for owner-side grading. They are synthetic evaluation artifacts for owner review, not production privacy data or shareable results.

```json
{
  "privacy": {
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
  },
  "repeated_statistics": {
    "schema_version": 1,
    "expected_repeats": 3,
    "minimum_repeats": 3,
    "groups": [
      {
        "split": "development",
        "variant": "baseline",
        "language": "ar",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "baseline",
        "language": "bn",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "baseline",
        "language": "de",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "baseline",
        "language": "en",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "baseline",
        "language": "es",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "baseline",
        "language": "fr",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "baseline",
        "language": "hi",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "baseline",
        "language": "id",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "baseline",
        "language": "ja",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "baseline",
        "language": "ko",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "baseline",
        "language": "mr",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "baseline",
        "language": "pt",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "baseline",
        "language": "ru",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "baseline",
        "language": "te",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "baseline",
        "language": "tr",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "baseline",
        "language": "ur",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "baseline",
        "language": "zh",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "candidate",
        "language": "ar",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "candidate",
        "language": "bn",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "candidate",
        "language": "de",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "candidate",
        "language": "en",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "candidate",
        "language": "es",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "candidate",
        "language": "fr",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "candidate",
        "language": "hi",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "candidate",
        "language": "id",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "candidate",
        "language": "ja",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "candidate",
        "language": "ko",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "candidate",
        "language": "mr",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "candidate",
        "language": "pt",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "candidate",
        "language": "ru",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "candidate",
        "language": "te",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "candidate",
        "language": "tr",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "candidate",
        "language": "ur",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "candidate",
        "language": "zh",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "human",
        "language": "ar",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "human",
        "language": "bn",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "human",
        "language": "de",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "human",
        "language": "en",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "human",
        "language": "es",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "human",
        "language": "fr",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "human",
        "language": "hi",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "human",
        "language": "id",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "human",
        "language": "ja",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "human",
        "language": "ko",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "human",
        "language": "mr",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "human",
        "language": "pt",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "human",
        "language": "ru",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "human",
        "language": "te",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "human",
        "language": "tr",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "human",
        "language": "ur",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "human",
        "language": "zh",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "original",
        "language": "ar",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "original",
        "language": "bn",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "original",
        "language": "de",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "original",
        "language": "en",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "original",
        "language": "es",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "original",
        "language": "fr",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "original",
        "language": "hi",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "original",
        "language": "id",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "original",
        "language": "ja",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "original",
        "language": "ko",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "original",
        "language": "mr",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "original",
        "language": "pt",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "original",
        "language": "ru",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "original",
        "language": "te",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "original",
        "language": "tr",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "original",
        "language": "ur",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "original",
        "language": "zh",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 0,
            "missing_tasks": 1,
            "possible_criteria": 4,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      }
    ],
    "aggregates": [
      {
        "split": "development",
        "variant": "baseline",
        "languages": [
          "ar",
          "bn",
          "de",
          "en",
          "es",
          "fr",
          "hi",
          "id",
          "ja",
          "ko",
          "mr",
          "pt",
          "ru",
          "te",
          "tr",
          "ur",
          "zh"
        ],
        "scheduled_tasks": 17,
        "possible_criteria_per_repeat": 68,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 17,
            "rows_present": 17,
            "graded_tasks": 0,
            "missing_tasks": 17,
            "possible_criteria": 68,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 17,
            "rows_present": 17,
            "graded_tasks": 0,
            "missing_tasks": 17,
            "possible_criteria": 68,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 17,
            "rows_present": 17,
            "graded_tasks": 0,
            "missing_tasks": 17,
            "possible_criteria": 68,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "candidate",
        "languages": [
          "ar",
          "bn",
          "de",
          "en",
          "es",
          "fr",
          "hi",
          "id",
          "ja",
          "ko",
          "mr",
          "pt",
          "ru",
          "te",
          "tr",
          "ur",
          "zh"
        ],
        "scheduled_tasks": 17,
        "possible_criteria_per_repeat": 68,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 17,
            "rows_present": 17,
            "graded_tasks": 0,
            "missing_tasks": 17,
            "possible_criteria": 68,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 17,
            "rows_present": 17,
            "graded_tasks": 0,
            "missing_tasks": 17,
            "possible_criteria": 68,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 17,
            "rows_present": 17,
            "graded_tasks": 0,
            "missing_tasks": 17,
            "possible_criteria": 68,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "human",
        "languages": [
          "ar",
          "bn",
          "de",
          "en",
          "es",
          "fr",
          "hi",
          "id",
          "ja",
          "ko",
          "mr",
          "pt",
          "ru",
          "te",
          "tr",
          "ur",
          "zh"
        ],
        "scheduled_tasks": 17,
        "possible_criteria_per_repeat": 68,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 17,
            "rows_present": 17,
            "graded_tasks": 0,
            "missing_tasks": 17,
            "possible_criteria": 68,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 17,
            "rows_present": 17,
            "graded_tasks": 0,
            "missing_tasks": 17,
            "possible_criteria": 68,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 17,
            "rows_present": 17,
            "graded_tasks": 0,
            "missing_tasks": 17,
            "possible_criteria": 68,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      },
      {
        "split": "development",
        "variant": "original",
        "languages": [
          "ar",
          "bn",
          "de",
          "en",
          "es",
          "fr",
          "hi",
          "id",
          "ja",
          "ko",
          "mr",
          "pt",
          "ru",
          "te",
          "tr",
          "ur",
          "zh"
        ],
        "scheduled_tasks": 17,
        "possible_criteria_per_repeat": 68,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 17,
            "rows_present": 17,
            "graded_tasks": 0,
            "missing_tasks": 17,
            "possible_criteria": 68,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 1,
            "scheduled_tasks": 17,
            "rows_present": 17,
            "graded_tasks": 0,
            "missing_tasks": 17,
            "possible_criteria": 68,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          },
          {
            "repeat": 2,
            "scheduled_tasks": 17,
            "rows_present": 17,
            "graded_tasks": 0,
            "missing_tasks": 17,
            "possible_criteria": 68,
            "graded_criteria": 0,
            "passed_criteria": 0,
            "task_success": 0,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": null
          }
        ],
        "complete_repeats": 0,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 0,
          "graded_criteria": 0,
          "passed_criteria": 0,
          "mean_observed_accuracy": null
        }
      }
    ],
    "paired": [
      {
        "split": "development",
        "language": null,
        "baseline_variant": "baseline",
        "candidate_variant": "candidate",
        "scheduled_tasks": 17,
        "possible_criteria_per_repeat": 68,
        "repeats": [
          {
            "repeat": 0,
            "complete": false,
            "passed_criteria_diff": null,
            "accuracy_diff": null,
            "task_success_diff": null
          },
          {
            "repeat": 1,
            "complete": false,
            "passed_criteria_diff": null,
            "accuracy_diff": null,
            "task_success_diff": null
          },
          {
            "repeat": 2,
            "complete": false,
            "passed_criteria_diff": null,
            "accuracy_diff": null,
            "task_success_diff": null
          }
        ],
        "eligible": false,
        "ineligible_reasons": [
          "baseline:missing_grades",
          "candidate:missing_grades"
        ],
        "statistics": null
      },
      {
        "split": "development",
        "language": "ar",
        "baseline_variant": "baseline",
        "candidate_variant": "candidate",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "complete": false,
            "passed_criteria_diff": null,
            "accuracy_diff": null,
            "task_success_diff": null
          },
          {
            "repeat": 1,
            "complete": false,
            "passed_criteria_diff": null,
            "accuracy_diff": null,
            "task_success_diff": null
          },
          {
            "repeat": 2,
            "complete": false,
            "passed_criteria_diff": null,
            "accuracy_diff": null,
            "task_success_diff": null
          }
        ],
        "eligible": false,
        "ineligible_reasons": [
          "baseline:missing_grades",
          "candidate:missing_grades"
        ],
        "statistics": null
      },
      {
        "split": "development",
        "language": "bn",
        "baseline_variant": "baseline",
        "candidate_variant": "candidate",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "complete": false,
            "passed_criteria_diff": null,
            "accuracy_diff": null,
            "task_success_diff": null
          },
          {
            "repeat": 1,
            "complete": false,
            "passed_criteria_diff": null,
            "accuracy_diff": null,
            "task_success_diff": null
          },
          {
            "repeat": 2,
            "complete": false,
            "passed_criteria_diff": null,
            "accuracy_diff": null,
            "task_success_diff": null
          }
        ],
        "eligible": false,
        "ineligible_reasons": [
          "baseline:missing_grades",
          "candidate:missing_grades"
        ],
        "statistics": null
      },
      {
        "split": "development",
        "language": "de",
        "baseline_variant": "baseline",
        "candidate_variant": "candidate",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "complete": false,
            "passed_criteria_diff": null,
            "accuracy_diff": null,
            "task_success_diff": null
          },
          {
            "repeat": 1,
            "complete": false,
            "passed_criteria_diff": null,
            "accuracy_diff": null,
            "task_success_diff": null
          },
          {
            "repeat": 2,
            "complete": false,
            "passed_criteria_diff": null,
            "accuracy_diff": null,
            "task_success_diff": null
          }
        ],
        "eligible": false,
        "ineligible_reasons": [
          "baseline:missing_grades",
          "candidate:missing_grades"
        ],
        "statistics": null
      },
      {
        "split": "development",
        "language": "en",
        "baseline_variant": "baseline",
        "candidate_variant": "candidate",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "complete": false,
            "passed_criteria_diff": null,
            "accuracy_diff": null,
            "task_success_diff": null
          },
          {
            "repeat": 1,
            "complete": false,
            "passed_criteria_diff": null,
            "accuracy_diff": null,
            "task_success_diff": null
          },
          {
            "repeat": 2,
            "complete": false,
            "passed_criteria_diff": null,
            "accuracy_diff": null,
            "task_success_diff": null
          }
        ],
        "eligible": false,
        "ineligible_reasons": [
          "baseline:missing_grades",
          "candidate:missing_grades"
        ],
        "statistics": null
      },
      {
        "split": "development",
        "language": "es",
        "baseline_variant": "baseline",
        "candidate_variant": "candidate",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "complete": false,
            "passed_criteria_diff": null,
            "accuracy_diff": null,
            "task_success_diff": null
          },
          {
            "repeat": 1,
            "complete": false,
            "passed_criteria_diff": null,
            "accuracy_diff": null,
            "task_success_diff": null
          },
          {
            "repeat": 2,
            "complete": false,
            "passed_criteria_diff": null,
            "accuracy_diff": null,
            "task_success_diff": null
          }
        ],
        "eligible": false,
        "ineligible_reasons": [
          "baseline:missing_grades",
          "candidate:missing_grades"
        ],
        "statistics": null
      },
      {
        "split": "development",
        "language": "fr",
        "baseline_variant": "baseline",
        "candidate_variant": "candidate",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "complete": false,
            "passed_criteria_diff": null,
            "accuracy_diff": null,
            "task_success_diff": null
          },
          {
            "repeat": 1,
            "complete": false,
            "passed_criteria_diff": null,
            "accuracy_diff": null,
            "task_success_diff": null
          },
          {
            "repeat": 2,
            "complete": false,
            "passed_criteria_diff": null,
            "accuracy_diff": null,
            "task_success_diff": null
          }
        ],
        "eligible": false,
        "ineligible_reasons": [
          "baseline:missing_grades",
          "candidate:missing_grades"
        ],
        "statistics": null
      },
      {
        "split": "development",
        "language": "hi",
        "baseline_variant": "baseline",
        "candidate_variant": "candidate",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "complete": false,
            "passed_criteria_diff": null,
            "accuracy_diff": null,
            "task_success_diff": null
          },
          {
            "repeat": 1,
            "complete": false,
            "passed_criteria_diff": null,
            "accuracy_diff": null,
            "task_success_diff": null
          },
          {
            "repeat": 2,
            "complete": false,
            "passed_criteria_diff": null,
            "accuracy_diff": null,
            "task_success_diff": null
          }
        ],
        "eligible": false,
        "ineligible_reasons": [
          "baseline:missing_grades",
          "candidate:missing_grades"
        ],
        "statistics": null
      },
      {
        "split": "development",
        "language": "id",
        "baseline_variant": "baseline",
        "candidate_variant": "candidate",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "complete": false,
            "passed_criteria_diff": null,
            "accuracy_diff": null,
            "task_success_diff": null
          },
          {
            "repeat": 1,
            "complete": false,
            "passed_criteria_diff": null,
            "accuracy_diff": null,
            "task_success_diff": null
          },
          {
            "repeat": 2,
            "complete": false,
            "passed_criteria_diff": null,
            "accuracy_diff": null,
            "task_success_diff": null
          }
        ],
        "eligible": false,
        "ineligible_reasons": [
          "baseline:missing_grades",
          "candidate:missing_grades"
        ],
        "statistics": null
      },
      {
        "split": "development",
        "language": "ja",
        "baseline_variant": "baseline",
        "candidate_variant": "candidate",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "complete": false,
            "passed_criteria_diff": null,
            "accuracy_diff": null,
            "task_success_diff": null
          },
          {
            "repeat": 1,
            "complete": false,
            "passed_criteria_diff": null,
            "accuracy_diff": null,
            "task_success_diff": null
          },
          {
            "repeat": 2,
            "complete": false,
            "passed_criteria_diff": null,
            "accuracy_diff": null,
            "task_success_diff": null
          }
        ],
        "eligible": false,
        "ineligible_reasons": [
          "baseline:missing_grades",
          "candidate:missing_grades"
        ],
        "statistics": null
      },
      {
        "split": "development",
        "language": "ko",
        "baseline_variant": "baseline",
        "candidate_variant": "candidate",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "complete": false,
            "passed_criteria_diff": null,
            "accuracy_diff": null,
            "task_success_diff": null
          },
          {
            "repeat": 1,
            "complete": false,
            "passed_criteria_diff": null,
            "accuracy_diff": null,
            "task_success_diff": null
          },
          {
            "repeat": 2,
            "complete": false,
            "passed_criteria_diff": null,
            "accuracy_diff": null,
            "task_success_diff": null
          }
        ],
        "eligible": false,
        "ineligible_reasons": [
          "baseline:missing_grades",
          "candidate:missing_grades"
        ],
        "statistics": null
      },
      {
        "split": "development",
        "language": "mr",
        "baseline_variant": "baseline",
        "candidate_variant": "candidate",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "complete": false,
            "passed_criteria_diff": null,
            "accuracy_diff": null,
            "task_success_diff": null
          },
          {
            "repeat": 1,
            "complete": false,
            "passed_criteria_diff": null,
            "accuracy_diff": null,
            "task_success_diff": null
          },
          {
            "repeat": 2,
            "complete": false,
            "passed_criteria_diff": null,
            "accuracy_diff": null,
            "task_success_diff": null
          }
        ],
        "eligible": false,
        "ineligible_reasons": [
          "baseline:missing_grades",
          "candidate:missing_grades"
        ],
        "statistics": null
      },
      {
        "split": "development",
        "language": "pt",
        "baseline_variant": "baseline",
        "candidate_variant": "candidate",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "complete": false,
            "passed_criteria_diff": null,
            "accuracy_diff": null,
            "task_success_diff": null
          },
          {
            "repeat": 1,
            "complete": false,
            "passed_criteria_diff": null,
            "accuracy_diff": null,
            "task_success_diff": null
          },
          {
            "repeat": 2,
            "complete": false,
            "passed_criteria_diff": null,
            "accuracy_diff": null,
            "task_success_diff": null
          }
        ],
        "eligible": false,
        "ineligible_reasons": [
          "baseline:missing_grades",
          "candidate:missing_grades"
        ],
        "statistics": null
      },
      {
        "split": "development",
        "language": "ru",
        "baseline_variant": "baseline",
        "candidate_variant": "candidate",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "complete": false,
            "passed_criteria_diff": null,
            "accuracy_diff": null,
            "task_success_diff": null
          },
          {
            "repeat": 1,
            "complete": false,
            "passed_criteria_diff": null,
            "accuracy_diff": null,
            "task_success_diff": null
          },
          {
            "repeat": 2,
            "complete": false,
            "passed_criteria_diff": null,
            "accuracy_diff": null,
            "task_success_diff": null
          }
        ],
        "eligible": false,
        "ineligible_reasons": [
          "baseline:missing_grades",
          "candidate:missing_grades"
        ],
        "statistics": null
      },
      {
        "split": "development",
        "language": "te",
        "baseline_variant": "baseline",
        "candidate_variant": "candidate",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "complete": false,
            "passed_criteria_diff": null,
            "accuracy_diff": null,
            "task_success_diff": null
          },
          {
            "repeat": 1,
            "complete": false,
            "passed_criteria_diff": null,
            "accuracy_diff": null,
            "task_success_diff": null
          },
          {
            "repeat": 2,
            "complete": false,
            "passed_criteria_diff": null,
            "accuracy_diff": null,
            "task_success_diff": null
          }
        ],
        "eligible": false,
        "ineligible_reasons": [
          "baseline:missing_grades",
          "candidate:missing_grades"
        ],
        "statistics": null
      },
      {
        "split": "development",
        "language": "tr",
        "baseline_variant": "baseline",
        "candidate_variant": "candidate",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "complete": false,
            "passed_criteria_diff": null,
            "accuracy_diff": null,
            "task_success_diff": null
          },
          {
            "repeat": 1,
            "complete": false,
            "passed_criteria_diff": null,
            "accuracy_diff": null,
            "task_success_diff": null
          },
          {
            "repeat": 2,
            "complete": false,
            "passed_criteria_diff": null,
            "accuracy_diff": null,
            "task_success_diff": null
          }
        ],
        "eligible": false,
        "ineligible_reasons": [
          "baseline:missing_grades",
          "candidate:missing_grades"
        ],
        "statistics": null
      },
      {
        "split": "development",
        "language": "ur",
        "baseline_variant": "baseline",
        "candidate_variant": "candidate",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "complete": false,
            "passed_criteria_diff": null,
            "accuracy_diff": null,
            "task_success_diff": null
          },
          {
            "repeat": 1,
            "complete": false,
            "passed_criteria_diff": null,
            "accuracy_diff": null,
            "task_success_diff": null
          },
          {
            "repeat": 2,
            "complete": false,
            "passed_criteria_diff": null,
            "accuracy_diff": null,
            "task_success_diff": null
          }
        ],
        "eligible": false,
        "ineligible_reasons": [
          "baseline:missing_grades",
          "candidate:missing_grades"
        ],
        "statistics": null
      },
      {
        "split": "development",
        "language": "zh",
        "baseline_variant": "baseline",
        "candidate_variant": "candidate",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "complete": false,
            "passed_criteria_diff": null,
            "accuracy_diff": null,
            "task_success_diff": null
          },
          {
            "repeat": 1,
            "complete": false,
            "passed_criteria_diff": null,
            "accuracy_diff": null,
            "task_success_diff": null
          },
          {
            "repeat": 2,
            "complete": false,
            "passed_criteria_diff": null,
            "accuracy_diff": null,
            "task_success_diff": null
          }
        ],
        "eligible": false,
        "ineligible_reasons": [
          "baseline:missing_grades",
          "candidate:missing_grades"
        ],
        "statistics": null
      }
    ],
    "holdout_eligibility": {
      "split": "holdout",
      "present": false,
      "variants": {},
      "paired_eligible": false,
      "decision": null,
      "note": "Statistical eligibility only; this report adopts and enables nothing."
    }
  },
  "execution": {
    "status": "not_started",
    "rejected_records": 0,
    "note": "Budgets are checked before each batch. Calls already in flight (at most the worker count) can exceed call/token/time budgets; the adapter has a fixed per-call timeout and the provider offers no hard token cap. Reported usage is actual CLI-reported usage only."
  }
}
```
