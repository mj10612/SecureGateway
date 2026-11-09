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
        "split": "holdout",
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
        "split": "holdout",
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
        "split": "holdout",
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
        "split": "holdout",
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
        "split": "holdout",
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
        "split": "holdout",
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
        "split": "holdout",
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
        "split": "holdout",
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
        "split": "holdout",
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
        "split": "holdout",
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
        "split": "holdout",
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
        "split": "holdout",
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
        "split": "holdout",
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
        "split": "holdout",
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
        "split": "holdout",
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
        "split": "holdout",
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
        "split": "holdout",
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
        "split": "holdout",
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
        "split": "holdout",
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
        "split": "holdout",
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
        "split": "holdout",
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
        "split": "holdout",
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
        "split": "holdout",
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
        "split": "holdout",
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
        "split": "holdout",
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
        "split": "holdout",
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
        "split": "holdout",
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
        "split": "holdout",
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
        "split": "holdout",
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
        "split": "holdout",
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
        "split": "holdout",
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
        "split": "holdout",
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
        "split": "holdout",
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
        "split": "holdout",
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
        "split": "holdout",
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
      "present": true,
      "variants": {
        "baseline": {
          "eligible": false,
          "ineligible_reasons": [
            "missing_grades"
          ]
        },
        "candidate": {
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
    "stop_reason": "Interrupted call has unknown usage; no automatic retry.",
    "budget": {
      "max_calls": 408,
      "max_seconds": 7200.0,
      "max_reported_tokens": 12000000,
      "workers": 3
    },
    "calls": 66,
    "by_status": {
      "completed": 63,
      "running": 3
    },
    "reported_tokens": 972859,
    "unknown_usage_calls": 3,
    "max_in_flight": 3,
    "rejected_records": 0,
    "elapsed_seconds": 0.0,
    "note": "Budgets are checked before each batch. Calls already in flight (at most the worker count) can exceed call/token/time budgets; the adapter has a fixed per-call timeout and the provider offers no hard token cap. Reported usage is actual CLI-reported usage only."
  }
}
```
