# Reliable multilingual evaluation

Status: incomplete
Split: holdout; repeats: 3; grading policy: 2

Privacy and task-response scores are separate. Development scores cannot authorize adoption.
Capture reports retain synthetic alias-to-original source maps for owner-side grading. They are synthetic evaluation artifacts for owner review, not production privacy data or shareable results.

```json
{
  "privacy": {
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
  },
  "repeated_statistics": {
    "schema_version": 1,
    "expected_repeats": 3,
    "minimum_repeats": 3,
    "groups": [
      {
        "split": "holdout",
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
        "split": "holdout",
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
            "graded_tasks": 1,
            "missing_tasks": 0,
            "possible_criteria": 4,
            "graded_criteria": 4,
            "passed_criteria": 4,
            "task_success": 1,
            "complete": true,
            "accuracy": 1.0,
            "observed_accuracy": 1.0
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
        "complete_repeats": 1,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 1,
          "graded_criteria": 4,
          "passed_criteria": 4,
          "mean_observed_accuracy": 1.0
        }
      },
      {
        "split": "holdout",
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
            "graded_tasks": 1,
            "missing_tasks": 0,
            "possible_criteria": 4,
            "graded_criteria": 4,
            "passed_criteria": 1,
            "task_success": 0,
            "complete": true,
            "accuracy": 0.25,
            "observed_accuracy": 0.25
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
        "complete_repeats": 1,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 1,
          "graded_criteria": 4,
          "passed_criteria": 1,
          "mean_observed_accuracy": 0.25
        }
      },
      {
        "split": "holdout",
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
            "graded_tasks": 1,
            "missing_tasks": 0,
            "possible_criteria": 4,
            "graded_criteria": 4,
            "passed_criteria": 4,
            "task_success": 1,
            "complete": true,
            "accuracy": 1.0,
            "observed_accuracy": 1.0
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
        "complete_repeats": 1,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 1,
          "graded_criteria": 4,
          "passed_criteria": 4,
          "mean_observed_accuracy": 1.0
        }
      },
      {
        "split": "holdout",
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
        "split": "holdout",
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
        "split": "holdout",
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
            "graded_tasks": 1,
            "missing_tasks": 0,
            "possible_criteria": 4,
            "graded_criteria": 4,
            "passed_criteria": 4,
            "task_success": 1,
            "complete": true,
            "accuracy": 1.0,
            "observed_accuracy": 1.0
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
        "complete_repeats": 1,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 1,
          "graded_criteria": 4,
          "passed_criteria": 4,
          "mean_observed_accuracy": 1.0
        }
      },
      {
        "split": "holdout",
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
        "split": "holdout",
        "variant": "baseline",
        "language": "ja",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 1,
            "missing_tasks": 0,
            "possible_criteria": 4,
            "graded_criteria": 4,
            "passed_criteria": 4,
            "task_success": 1,
            "complete": true,
            "accuracy": 1.0,
            "observed_accuracy": 1.0
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
            "graded_tasks": 1,
            "missing_tasks": 0,
            "possible_criteria": 4,
            "graded_criteria": 4,
            "passed_criteria": 4,
            "task_success": 1,
            "complete": true,
            "accuracy": 1.0,
            "observed_accuracy": 1.0
          }
        ],
        "complete_repeats": 2,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 2,
          "graded_criteria": 8,
          "passed_criteria": 8,
          "mean_observed_accuracy": 1.0
        }
      },
      {
        "split": "holdout",
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
        "split": "holdout",
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
        "split": "holdout",
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
            "graded_tasks": 1,
            "missing_tasks": 0,
            "possible_criteria": 4,
            "graded_criteria": 4,
            "passed_criteria": 4,
            "task_success": 1,
            "complete": true,
            "accuracy": 1.0,
            "observed_accuracy": 1.0
          }
        ],
        "complete_repeats": 1,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 1,
          "graded_criteria": 4,
          "passed_criteria": 4,
          "mean_observed_accuracy": 1.0
        }
      },
      {
        "split": "holdout",
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
        "split": "holdout",
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
        "split": "holdout",
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
            "graded_tasks": 1,
            "missing_tasks": 0,
            "possible_criteria": 4,
            "graded_criteria": 4,
            "passed_criteria": 4,
            "task_success": 1,
            "complete": true,
            "accuracy": 1.0,
            "observed_accuracy": 1.0
          }
        ],
        "complete_repeats": 1,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 1,
          "graded_criteria": 4,
          "passed_criteria": 4,
          "mean_observed_accuracy": 1.0
        }
      },
      {
        "split": "holdout",
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
        "split": "holdout",
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
        "split": "holdout",
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
        "split": "holdout",
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
        "split": "holdout",
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
            "graded_tasks": 1,
            "missing_tasks": 0,
            "possible_criteria": 4,
            "graded_criteria": 4,
            "passed_criteria": 4,
            "task_success": 1,
            "complete": true,
            "accuracy": 1.0,
            "observed_accuracy": 1.0
          }
        ],
        "complete_repeats": 1,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 1,
          "graded_criteria": 4,
          "passed_criteria": 4,
          "mean_observed_accuracy": 1.0
        }
      },
      {
        "split": "holdout",
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
            "graded_tasks": 1,
            "missing_tasks": 0,
            "possible_criteria": 4,
            "graded_criteria": 4,
            "passed_criteria": 4,
            "task_success": 1,
            "complete": true,
            "accuracy": 1.0,
            "observed_accuracy": 1.0
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 1,
            "missing_tasks": 0,
            "possible_criteria": 4,
            "graded_criteria": 4,
            "passed_criteria": 4,
            "task_success": 1,
            "complete": true,
            "accuracy": 1.0,
            "observed_accuracy": 1.0
          }
        ],
        "complete_repeats": 2,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 2,
          "graded_criteria": 8,
          "passed_criteria": 8,
          "mean_observed_accuracy": 1.0
        }
      },
      {
        "split": "holdout",
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
            "graded_tasks": 1,
            "missing_tasks": 0,
            "possible_criteria": 4,
            "graded_criteria": 4,
            "passed_criteria": 4,
            "task_success": 1,
            "complete": true,
            "accuracy": 1.0,
            "observed_accuracy": 1.0
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
        "complete_repeats": 1,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 1,
          "graded_criteria": 4,
          "passed_criteria": 4,
          "mean_observed_accuracy": 1.0
        }
      },
      {
        "split": "holdout",
        "variant": "human",
        "language": "fr",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 1,
            "missing_tasks": 0,
            "possible_criteria": 4,
            "graded_criteria": 4,
            "passed_criteria": 4,
            "task_success": 1,
            "complete": true,
            "accuracy": 1.0,
            "observed_accuracy": 1.0
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 1,
            "missing_tasks": 0,
            "possible_criteria": 4,
            "graded_criteria": 4,
            "passed_criteria": 4,
            "task_success": 1,
            "complete": true,
            "accuracy": 1.0,
            "observed_accuracy": 1.0
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
        "complete_repeats": 2,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 2,
          "graded_criteria": 8,
          "passed_criteria": 8,
          "mean_observed_accuracy": 1.0
        }
      },
      {
        "split": "holdout",
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
        "split": "holdout",
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
        "split": "holdout",
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
        "split": "holdout",
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
        "split": "holdout",
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
        "split": "holdout",
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
        "split": "holdout",
        "variant": "human",
        "language": "ru",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 1,
            "missing_tasks": 0,
            "possible_criteria": 4,
            "graded_criteria": 4,
            "passed_criteria": 4,
            "task_success": 1,
            "complete": true,
            "accuracy": 1.0,
            "observed_accuracy": 1.0
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
        "complete_repeats": 1,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 1,
          "graded_criteria": 4,
          "passed_criteria": 4,
          "mean_observed_accuracy": 1.0
        }
      },
      {
        "split": "holdout",
        "variant": "human",
        "language": "te",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 1,
            "missing_tasks": 0,
            "possible_criteria": 4,
            "graded_criteria": 4,
            "passed_criteria": 4,
            "task_success": 1,
            "complete": true,
            "accuracy": 1.0,
            "observed_accuracy": 1.0
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
        "complete_repeats": 1,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 1,
          "graded_criteria": 4,
          "passed_criteria": 4,
          "mean_observed_accuracy": 1.0
        }
      },
      {
        "split": "holdout",
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
            "graded_tasks": 1,
            "missing_tasks": 0,
            "possible_criteria": 4,
            "graded_criteria": 4,
            "passed_criteria": 4,
            "task_success": 1,
            "complete": true,
            "accuracy": 1.0,
            "observed_accuracy": 1.0
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
        "complete_repeats": 1,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 1,
          "graded_criteria": 4,
          "passed_criteria": 4,
          "mean_observed_accuracy": 1.0
        }
      },
      {
        "split": "holdout",
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
        "split": "holdout",
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
        "split": "holdout",
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
        "split": "holdout",
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
            "graded_tasks": 1,
            "missing_tasks": 0,
            "possible_criteria": 4,
            "graded_criteria": 4,
            "passed_criteria": 4,
            "task_success": 1,
            "complete": true,
            "accuracy": 1.0,
            "observed_accuracy": 1.0
          }
        ],
        "complete_repeats": 1,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 1,
          "graded_criteria": 4,
          "passed_criteria": 4,
          "mean_observed_accuracy": 1.0
        }
      },
      {
        "split": "holdout",
        "variant": "original",
        "language": "de",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 1,
            "missing_tasks": 0,
            "possible_criteria": 4,
            "graded_criteria": 4,
            "passed_criteria": 4,
            "task_success": 1,
            "complete": true,
            "accuracy": 1.0,
            "observed_accuracy": 1.0
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 1,
            "missing_tasks": 0,
            "possible_criteria": 4,
            "graded_criteria": 4,
            "passed_criteria": 4,
            "task_success": 1,
            "complete": true,
            "accuracy": 1.0,
            "observed_accuracy": 1.0
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
        "complete_repeats": 2,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 2,
          "graded_criteria": 8,
          "passed_criteria": 8,
          "mean_observed_accuracy": 1.0
        }
      },
      {
        "split": "holdout",
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
        "split": "holdout",
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
            "graded_tasks": 1,
            "missing_tasks": 0,
            "possible_criteria": 4,
            "graded_criteria": 4,
            "passed_criteria": 4,
            "task_success": 1,
            "complete": true,
            "accuracy": 1.0,
            "observed_accuracy": 1.0
          }
        ],
        "complete_repeats": 1,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 1,
          "graded_criteria": 4,
          "passed_criteria": 4,
          "mean_observed_accuracy": 1.0
        }
      },
      {
        "split": "holdout",
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
        "split": "holdout",
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
        "split": "holdout",
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
        "split": "holdout",
        "variant": "original",
        "language": "ja",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 1,
            "missing_tasks": 0,
            "possible_criteria": 4,
            "graded_criteria": 4,
            "passed_criteria": 4,
            "task_success": 1,
            "complete": true,
            "accuracy": 1.0,
            "observed_accuracy": 1.0
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 1,
            "missing_tasks": 0,
            "possible_criteria": 4,
            "graded_criteria": 4,
            "passed_criteria": 4,
            "task_success": 1,
            "complete": true,
            "accuracy": 1.0,
            "observed_accuracy": 1.0
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 1,
            "missing_tasks": 0,
            "possible_criteria": 4,
            "graded_criteria": 4,
            "passed_criteria": 4,
            "task_success": 1,
            "complete": true,
            "accuracy": 1.0,
            "observed_accuracy": 1.0
          }
        ],
        "complete_repeats": 3,
        "eligible": true,
        "ineligible_reasons": [],
        "statistics": {
          "accuracy": {
            "mean": 1.0,
            "sample_sd": 0.0,
            "n": 3
          },
          "passed_criteria": {
            "mean": 4.0,
            "sample_sd": 0.0,
            "n": 3
          },
          "task_success": {
            "mean": 1.0,
            "sample_sd": 0.0,
            "n": 3
          }
        },
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 3,
          "graded_criteria": 12,
          "passed_criteria": 12,
          "mean_observed_accuracy": 1.0
        }
      },
      {
        "split": "holdout",
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
        "split": "holdout",
        "variant": "original",
        "language": "mr",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 1,
            "missing_tasks": 0,
            "possible_criteria": 4,
            "graded_criteria": 4,
            "passed_criteria": 4,
            "task_success": 1,
            "complete": true,
            "accuracy": 1.0,
            "observed_accuracy": 1.0
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
        "complete_repeats": 1,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 1,
          "graded_criteria": 4,
          "passed_criteria": 4,
          "mean_observed_accuracy": 1.0
        }
      },
      {
        "split": "holdout",
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
        "split": "holdout",
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
        "split": "holdout",
        "variant": "original",
        "language": "te",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 1,
            "missing_tasks": 0,
            "possible_criteria": 4,
            "graded_criteria": 4,
            "passed_criteria": 4,
            "task_success": 1,
            "complete": true,
            "accuracy": 1.0,
            "observed_accuracy": 1.0
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
        "complete_repeats": 1,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 1,
          "graded_criteria": 4,
          "passed_criteria": 4,
          "mean_observed_accuracy": 1.0
        }
      },
      {
        "split": "holdout",
        "variant": "original",
        "language": "tr",
        "scheduled_tasks": 1,
        "possible_criteria_per_repeat": 4,
        "repeats": [
          {
            "repeat": 0,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 1,
            "missing_tasks": 0,
            "possible_criteria": 4,
            "graded_criteria": 4,
            "passed_criteria": 4,
            "task_success": 1,
            "complete": true,
            "accuracy": 1.0,
            "observed_accuracy": 1.0
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
            "graded_tasks": 1,
            "missing_tasks": 0,
            "possible_criteria": 4,
            "graded_criteria": 4,
            "passed_criteria": 4,
            "task_success": 1,
            "complete": true,
            "accuracy": 1.0,
            "observed_accuracy": 1.0
          }
        ],
        "complete_repeats": 2,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 2,
          "graded_criteria": 8,
          "passed_criteria": 8,
          "mean_observed_accuracy": 1.0
        }
      },
      {
        "split": "holdout",
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
        "split": "holdout",
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
            "graded_tasks": 1,
            "missing_tasks": 0,
            "possible_criteria": 4,
            "graded_criteria": 4,
            "passed_criteria": 4,
            "task_success": 1,
            "complete": true,
            "accuracy": 1.0,
            "observed_accuracy": 1.0
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
        "complete_repeats": 1,
        "eligible": false,
        "ineligible_reasons": [
          "missing_grades"
        ],
        "statistics": null,
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 1,
          "graded_criteria": 4,
          "passed_criteria": 4,
          "mean_observed_accuracy": 1.0
        }
      }
    ],
    "aggregates": [
      {
        "split": "holdout",
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
            "graded_tasks": 1,
            "missing_tasks": 16,
            "possible_criteria": 68,
            "graded_criteria": 4,
            "passed_criteria": 4,
            "task_success": 1,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": 1.0
          },
          {
            "repeat": 1,
            "scheduled_tasks": 17,
            "rows_present": 17,
            "graded_tasks": 4,
            "missing_tasks": 13,
            "possible_criteria": 68,
            "graded_criteria": 16,
            "passed_criteria": 13,
            "task_success": 3,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": 0.8125
          },
          {
            "repeat": 2,
            "scheduled_tasks": 17,
            "rows_present": 17,
            "graded_tasks": 3,
            "missing_tasks": 14,
            "possible_criteria": 68,
            "graded_criteria": 12,
            "passed_criteria": 12,
            "task_success": 3,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": 1.0
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
          "repeats_with_grades": 3,
          "graded_criteria": 32,
          "passed_criteria": 29,
          "mean_observed_accuracy": 0.9375
        }
      },
      {
        "split": "holdout",
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
            "graded_tasks": 3,
            "missing_tasks": 14,
            "possible_criteria": 68,
            "graded_criteria": 12,
            "passed_criteria": 12,
            "task_success": 3,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": 1.0
          },
          {
            "repeat": 1,
            "scheduled_tasks": 17,
            "rows_present": 17,
            "graded_tasks": 4,
            "missing_tasks": 13,
            "possible_criteria": 68,
            "graded_criteria": 16,
            "passed_criteria": 16,
            "task_success": 4,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": 1.0
          },
          {
            "repeat": 2,
            "scheduled_tasks": 17,
            "rows_present": 17,
            "graded_tasks": 2,
            "missing_tasks": 15,
            "possible_criteria": 68,
            "graded_criteria": 8,
            "passed_criteria": 8,
            "task_success": 2,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": 1.0
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
          "repeats_with_grades": 3,
          "graded_criteria": 36,
          "passed_criteria": 36,
          "mean_observed_accuracy": 1.0
        }
      },
      {
        "split": "holdout",
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
            "graded_tasks": 5,
            "missing_tasks": 12,
            "possible_criteria": 68,
            "graded_criteria": 20,
            "passed_criteria": 20,
            "task_success": 5,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": 1.0
          },
          {
            "repeat": 1,
            "scheduled_tasks": 17,
            "rows_present": 17,
            "graded_tasks": 3,
            "missing_tasks": 14,
            "possible_criteria": 68,
            "graded_criteria": 12,
            "passed_criteria": 12,
            "task_success": 3,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": 1.0
          },
          {
            "repeat": 2,
            "scheduled_tasks": 17,
            "rows_present": 17,
            "graded_tasks": 4,
            "missing_tasks": 13,
            "possible_criteria": 68,
            "graded_criteria": 16,
            "passed_criteria": 16,
            "task_success": 4,
            "complete": false,
            "accuracy": null,
            "observed_accuracy": 1.0
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
          "repeats_with_grades": 3,
          "graded_criteria": 48,
          "passed_criteria": 48,
          "mean_observed_accuracy": 1.0
        }
      }
    ],
    "paired": [],
    "holdout_eligibility": {
      "split": "holdout",
      "present": true,
      "variants": {
        "baseline": {
          "eligible": false,
          "ineligible_reasons": [
            "missing_grades"
          ]
        },
        "human": {
          "eligible": false,
          "ineligible_reasons": [
            "missing_grades"
          ]
        },
        "original": {
          "eligible": false,
          "ineligible_reasons": [
            "missing_grades"
          ]
        }
      },
      "paired_eligible": false,
      "decision": null,
      "note": "Statistical eligibility only; this report adopts and enables nothing."
    }
  },
  "execution": {
    "status": "stopped",
    "stop_reason": "Worker error or rejected record.",
    "budget": {
      "max_calls": 306,
      "max_seconds": 7200.0,
      "max_reported_tokens": 12000000,
      "workers": 3
    },
    "calls": 183,
    "by_status": {
      "completed": 182,
      "error": 1
    },
    "reported_tokens": 2861052,
    "unknown_usage_calls": 1,
    "max_in_flight": 3,
    "rejected_records": 0,
    "elapsed_seconds": 886.7960000000003,
    "note": "Budgets are checked before each batch. Calls already in flight (at most the worker count) can exceed call/token/time budgets; the adapter has a fixed per-call timeout and the provider offers no hard token cap. Reported usage is actual CLI-reported usage only."
  }
}
```
