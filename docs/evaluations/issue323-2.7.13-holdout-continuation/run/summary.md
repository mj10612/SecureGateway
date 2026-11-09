# Reliable multilingual evaluation

Status: completed
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
            "graded_tasks": 1,
            "missing_tasks": 0,
            "possible_criteria": 4,
            "graded_criteria": 4,
            "passed_criteria": 3,
            "task_success": 0,
            "complete": true,
            "accuracy": 0.75,
            "observed_accuracy": 0.75
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 1,
            "missing_tasks": 0,
            "possible_criteria": 4,
            "graded_criteria": 4,
            "passed_criteria": 3,
            "task_success": 0,
            "complete": true,
            "accuracy": 0.75,
            "observed_accuracy": 0.75
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 1,
            "missing_tasks": 0,
            "possible_criteria": 4,
            "graded_criteria": 4,
            "passed_criteria": 3,
            "task_success": 0,
            "complete": true,
            "accuracy": 0.75,
            "observed_accuracy": 0.75
          }
        ],
        "complete_repeats": 3,
        "eligible": true,
        "ineligible_reasons": [],
        "statistics": {
          "accuracy": {
            "mean": 0.75,
            "sample_sd": 0.0,
            "n": 3
          },
          "passed_criteria": {
            "mean": 3.0,
            "sample_sd": 0.0,
            "n": 3
          },
          "task_success": {
            "mean": 0.0,
            "sample_sd": 0.0,
            "n": 3
          }
        },
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 3,
          "graded_criteria": 12,
          "passed_criteria": 9,
          "mean_observed_accuracy": 0.75
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
        "variant": "baseline",
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
            "passed_criteria": 1,
            "task_success": 0,
            "complete": true,
            "accuracy": 0.25,
            "observed_accuracy": 0.25
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
            "graded_tasks": 1,
            "missing_tasks": 0,
            "possible_criteria": 4,
            "graded_criteria": 4,
            "passed_criteria": 1,
            "task_success": 0,
            "complete": true,
            "accuracy": 0.25,
            "observed_accuracy": 0.25
          }
        ],
        "complete_repeats": 3,
        "eligible": true,
        "ineligible_reasons": [],
        "statistics": {
          "accuracy": {
            "mean": 0.25,
            "sample_sd": 0.0,
            "n": 3
          },
          "passed_criteria": {
            "mean": 1.0,
            "sample_sd": 0.0,
            "n": 3
          },
          "task_success": {
            "mean": 0.0,
            "sample_sd": 0.0,
            "n": 3
          }
        },
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 3,
          "graded_criteria": 12,
          "passed_criteria": 3,
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
            "graded_tasks": 1,
            "missing_tasks": 0,
            "possible_criteria": 4,
            "graded_criteria": 4,
            "passed_criteria": 2,
            "task_success": 0,
            "complete": true,
            "accuracy": 0.5,
            "observed_accuracy": 0.5
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
            "passed_criteria": 2,
            "task_success": 0,
            "complete": true,
            "accuracy": 0.5,
            "observed_accuracy": 0.5
          }
        ],
        "complete_repeats": 3,
        "eligible": true,
        "ineligible_reasons": [],
        "statistics": {
          "accuracy": {
            "mean": 0.6666666666666666,
            "sample_sd": 0.28867513459481287,
            "n": 3
          },
          "passed_criteria": {
            "mean": 2.6666666666666665,
            "sample_sd": 1.1547005383792515,
            "n": 3
          },
          "task_success": {
            "mean": 0.3333333333333333,
            "sample_sd": 0.5773502691896257,
            "n": 3
          }
        },
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 3,
          "graded_criteria": 12,
          "passed_criteria": 8,
          "mean_observed_accuracy": 0.6666666666666666
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
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 1,
            "missing_tasks": 0,
            "possible_criteria": 4,
            "graded_criteria": 4,
            "passed_criteria": 3,
            "task_success": 0,
            "complete": true,
            "accuracy": 0.75,
            "observed_accuracy": 0.75
          },
          {
            "repeat": 2,
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
          }
        ],
        "complete_repeats": 3,
        "eligible": true,
        "ineligible_reasons": [],
        "statistics": {
          "accuracy": {
            "mean": 0.4166666666666667,
            "sample_sd": 0.28867513459481287,
            "n": 3
          },
          "passed_criteria": {
            "mean": 1.6666666666666667,
            "sample_sd": 1.1547005383792515,
            "n": 3
          },
          "task_success": {
            "mean": 0.0,
            "sample_sd": 0.0,
            "n": 3
          }
        },
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 3,
          "graded_criteria": 12,
          "passed_criteria": 5,
          "mean_observed_accuracy": 0.4166666666666667
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
        "variant": "baseline",
        "language": "hi",
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
        "variant": "baseline",
        "language": "id",
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
            "passed_criteria": 1,
            "task_success": 0,
            "complete": true,
            "accuracy": 0.25,
            "observed_accuracy": 0.25
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
            "graded_tasks": 1,
            "missing_tasks": 0,
            "possible_criteria": 4,
            "graded_criteria": 4,
            "passed_criteria": 1,
            "task_success": 0,
            "complete": true,
            "accuracy": 0.25,
            "observed_accuracy": 0.25
          }
        ],
        "complete_repeats": 3,
        "eligible": true,
        "ineligible_reasons": [],
        "statistics": {
          "accuracy": {
            "mean": 0.25,
            "sample_sd": 0.0,
            "n": 3
          },
          "passed_criteria": {
            "mean": 1.0,
            "sample_sd": 0.0,
            "n": 3
          },
          "task_success": {
            "mean": 0.0,
            "sample_sd": 0.0,
            "n": 3
          }
        },
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 3,
          "graded_criteria": 12,
          "passed_criteria": 3,
          "mean_observed_accuracy": 0.25
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
        "variant": "baseline",
        "language": "ko",
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
            "passed_criteria": 3,
            "task_success": 0,
            "complete": true,
            "accuracy": 0.75,
            "observed_accuracy": 0.75
          }
        ],
        "complete_repeats": 3,
        "eligible": true,
        "ineligible_reasons": [],
        "statistics": {
          "accuracy": {
            "mean": 0.9166666666666666,
            "sample_sd": 0.14433756729740643,
            "n": 3
          },
          "passed_criteria": {
            "mean": 3.6666666666666665,
            "sample_sd": 0.5773502691896257,
            "n": 3
          },
          "task_success": {
            "mean": 0.6666666666666666,
            "sample_sd": 0.5773502691896257,
            "n": 3
          }
        },
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 3,
          "graded_criteria": 12,
          "passed_criteria": 11,
          "mean_observed_accuracy": 0.9166666666666666
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
            "graded_tasks": 1,
            "missing_tasks": 0,
            "possible_criteria": 4,
            "graded_criteria": 4,
            "passed_criteria": 1,
            "task_success": 0,
            "complete": true,
            "accuracy": 0.25,
            "observed_accuracy": 0.25
          }
        ],
        "complete_repeats": 3,
        "eligible": true,
        "ineligible_reasons": [],
        "statistics": {
          "accuracy": {
            "mean": 0.25,
            "sample_sd": 0.0,
            "n": 3
          },
          "passed_criteria": {
            "mean": 1.0,
            "sample_sd": 0.0,
            "n": 3
          },
          "task_success": {
            "mean": 0.0,
            "sample_sd": 0.0,
            "n": 3
          }
        },
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 3,
          "graded_criteria": 12,
          "passed_criteria": 3,
          "mean_observed_accuracy": 0.25
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
        "variant": "baseline",
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
            "passed_criteria": 2,
            "task_success": 0,
            "complete": true,
            "accuracy": 0.5,
            "observed_accuracy": 0.5
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 1,
            "missing_tasks": 0,
            "possible_criteria": 4,
            "graded_criteria": 4,
            "passed_criteria": 2,
            "task_success": 0,
            "complete": true,
            "accuracy": 0.5,
            "observed_accuracy": 0.5
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 1,
            "missing_tasks": 0,
            "possible_criteria": 4,
            "graded_criteria": 4,
            "passed_criteria": 2,
            "task_success": 0,
            "complete": true,
            "accuracy": 0.5,
            "observed_accuracy": 0.5
          }
        ],
        "complete_repeats": 3,
        "eligible": true,
        "ineligible_reasons": [],
        "statistics": {
          "accuracy": {
            "mean": 0.5,
            "sample_sd": 0.0,
            "n": 3
          },
          "passed_criteria": {
            "mean": 2.0,
            "sample_sd": 0.0,
            "n": 3
          },
          "task_success": {
            "mean": 0.0,
            "sample_sd": 0.0,
            "n": 3
          }
        },
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 3,
          "graded_criteria": 12,
          "passed_criteria": 6,
          "mean_observed_accuracy": 0.5
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
            "graded_tasks": 1,
            "missing_tasks": 0,
            "possible_criteria": 4,
            "graded_criteria": 4,
            "passed_criteria": 2,
            "task_success": 0,
            "complete": true,
            "accuracy": 0.5,
            "observed_accuracy": 0.5
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
            "graded_tasks": 1,
            "missing_tasks": 0,
            "possible_criteria": 4,
            "graded_criteria": 4,
            "passed_criteria": 1,
            "task_success": 0,
            "complete": true,
            "accuracy": 0.25,
            "observed_accuracy": 0.25
          }
        ],
        "complete_repeats": 3,
        "eligible": true,
        "ineligible_reasons": [],
        "statistics": {
          "accuracy": {
            "mean": 0.3333333333333333,
            "sample_sd": 0.14433756729740643,
            "n": 3
          },
          "passed_criteria": {
            "mean": 1.3333333333333333,
            "sample_sd": 0.5773502691896257,
            "n": 3
          },
          "task_success": {
            "mean": 0.0,
            "sample_sd": 0.0,
            "n": 3
          }
        },
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 3,
          "graded_criteria": 12,
          "passed_criteria": 4,
          "mean_observed_accuracy": 0.3333333333333333
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
            "graded_tasks": 1,
            "missing_tasks": 0,
            "possible_criteria": 4,
            "graded_criteria": 4,
            "passed_criteria": 3,
            "task_success": 0,
            "complete": true,
            "accuracy": 0.75,
            "observed_accuracy": 0.75
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
            "mean": 0.9166666666666666,
            "sample_sd": 0.14433756729740643,
            "n": 3
          },
          "passed_criteria": {
            "mean": 3.6666666666666665,
            "sample_sd": 0.5773502691896257,
            "n": 3
          },
          "task_success": {
            "mean": 0.6666666666666666,
            "sample_sd": 0.5773502691896257,
            "n": 3
          }
        },
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 3,
          "graded_criteria": 12,
          "passed_criteria": 11,
          "mean_observed_accuracy": 0.9166666666666666
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
        "variant": "baseline",
        "language": "zh",
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
            "passed_criteria": 3,
            "task_success": 0,
            "complete": true,
            "accuracy": 0.75,
            "observed_accuracy": 0.75
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 1,
            "missing_tasks": 0,
            "possible_criteria": 4,
            "graded_criteria": 4,
            "passed_criteria": 3,
            "task_success": 0,
            "complete": true,
            "accuracy": 0.75,
            "observed_accuracy": 0.75
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 1,
            "missing_tasks": 0,
            "possible_criteria": 4,
            "graded_criteria": 4,
            "passed_criteria": 3,
            "task_success": 0,
            "complete": true,
            "accuracy": 0.75,
            "observed_accuracy": 0.75
          }
        ],
        "complete_repeats": 3,
        "eligible": true,
        "ineligible_reasons": [],
        "statistics": {
          "accuracy": {
            "mean": 0.75,
            "sample_sd": 0.0,
            "n": 3
          },
          "passed_criteria": {
            "mean": 3.0,
            "sample_sd": 0.0,
            "n": 3
          },
          "task_success": {
            "mean": 0.0,
            "sample_sd": 0.0,
            "n": 3
          }
        },
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 3,
          "graded_criteria": 12,
          "passed_criteria": 9,
          "mean_observed_accuracy": 0.75
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
        "variant": "candidate",
        "language": "bn",
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
        "variant": "candidate",
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
        "variant": "candidate",
        "language": "en",
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
            "passed_criteria": 3,
            "task_success": 0,
            "complete": true,
            "accuracy": 0.75,
            "observed_accuracy": 0.75
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 1,
            "missing_tasks": 0,
            "possible_criteria": 4,
            "graded_criteria": 4,
            "passed_criteria": 3,
            "task_success": 0,
            "complete": true,
            "accuracy": 0.75,
            "observed_accuracy": 0.75
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
            "mean": 0.8333333333333334,
            "sample_sd": 0.14433756729740643,
            "n": 3
          },
          "passed_criteria": {
            "mean": 3.3333333333333335,
            "sample_sd": 0.5773502691896257,
            "n": 3
          },
          "task_success": {
            "mean": 0.3333333333333333,
            "sample_sd": 0.5773502691896257,
            "n": 3
          }
        },
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 3,
          "graded_criteria": 12,
          "passed_criteria": 10,
          "mean_observed_accuracy": 0.8333333333333334
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
            "graded_tasks": 1,
            "missing_tasks": 0,
            "possible_criteria": 4,
            "graded_criteria": 4,
            "passed_criteria": 2,
            "task_success": 0,
            "complete": true,
            "accuracy": 0.5,
            "observed_accuracy": 0.5
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 1,
            "missing_tasks": 0,
            "possible_criteria": 4,
            "graded_criteria": 4,
            "passed_criteria": 2,
            "task_success": 0,
            "complete": true,
            "accuracy": 0.5,
            "observed_accuracy": 0.5
          },
          {
            "repeat": 2,
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
          }
        ],
        "complete_repeats": 3,
        "eligible": true,
        "ineligible_reasons": [],
        "statistics": {
          "accuracy": {
            "mean": 0.4166666666666667,
            "sample_sd": 0.14433756729740643,
            "n": 3
          },
          "passed_criteria": {
            "mean": 1.6666666666666667,
            "sample_sd": 0.5773502691896257,
            "n": 3
          },
          "task_success": {
            "mean": 0.0,
            "sample_sd": 0.0,
            "n": 3
          }
        },
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 3,
          "graded_criteria": 12,
          "passed_criteria": 5,
          "mean_observed_accuracy": 0.4166666666666667
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
        "variant": "candidate",
        "language": "hi",
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
        "variant": "candidate",
        "language": "id",
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
            "passed_criteria": 2,
            "task_success": 0,
            "complete": true,
            "accuracy": 0.5,
            "observed_accuracy": 0.5
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
            "mean": 0.8333333333333334,
            "sample_sd": 0.28867513459481287,
            "n": 3
          },
          "passed_criteria": {
            "mean": 3.3333333333333335,
            "sample_sd": 1.1547005383792515,
            "n": 3
          },
          "task_success": {
            "mean": 0.6666666666666666,
            "sample_sd": 0.5773502691896257,
            "n": 3
          }
        },
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 3,
          "graded_criteria": 12,
          "passed_criteria": 10,
          "mean_observed_accuracy": 0.8333333333333334
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
        "variant": "candidate",
        "language": "ko",
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
        "variant": "candidate",
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
            "graded_tasks": 1,
            "missing_tasks": 0,
            "possible_criteria": 4,
            "graded_criteria": 4,
            "passed_criteria": 3,
            "task_success": 0,
            "complete": true,
            "accuracy": 0.75,
            "observed_accuracy": 0.75
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
            "mean": 0.9166666666666666,
            "sample_sd": 0.14433756729740643,
            "n": 3
          },
          "passed_criteria": {
            "mean": 3.6666666666666665,
            "sample_sd": 0.5773502691896257,
            "n": 3
          },
          "task_success": {
            "mean": 0.6666666666666666,
            "sample_sd": 0.5773502691896257,
            "n": 3
          }
        },
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 3,
          "graded_criteria": 12,
          "passed_criteria": 11,
          "mean_observed_accuracy": 0.9166666666666666
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
        "variant": "candidate",
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
            "passed_criteria": 2,
            "task_success": 0,
            "complete": true,
            "accuracy": 0.5,
            "observed_accuracy": 0.5
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 1,
            "missing_tasks": 0,
            "possible_criteria": 4,
            "graded_criteria": 4,
            "passed_criteria": 2,
            "task_success": 0,
            "complete": true,
            "accuracy": 0.5,
            "observed_accuracy": 0.5
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 1,
            "missing_tasks": 0,
            "possible_criteria": 4,
            "graded_criteria": 4,
            "passed_criteria": 2,
            "task_success": 0,
            "complete": true,
            "accuracy": 0.5,
            "observed_accuracy": 0.5
          }
        ],
        "complete_repeats": 3,
        "eligible": true,
        "ineligible_reasons": [],
        "statistics": {
          "accuracy": {
            "mean": 0.5,
            "sample_sd": 0.0,
            "n": 3
          },
          "passed_criteria": {
            "mean": 2.0,
            "sample_sd": 0.0,
            "n": 3
          },
          "task_success": {
            "mean": 0.0,
            "sample_sd": 0.0,
            "n": 3
          }
        },
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 3,
          "graded_criteria": 12,
          "passed_criteria": 6,
          "mean_observed_accuracy": 0.5
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
        "variant": "candidate",
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
        "variant": "candidate",
        "language": "ur",
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
        "variant": "candidate",
        "language": "zh",
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
            "passed_criteria": 3,
            "task_success": 0,
            "complete": true,
            "accuracy": 0.75,
            "observed_accuracy": 0.75
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 1,
            "missing_tasks": 0,
            "possible_criteria": 4,
            "graded_criteria": 4,
            "passed_criteria": 3,
            "task_success": 0,
            "complete": true,
            "accuracy": 0.75,
            "observed_accuracy": 0.75
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 1,
            "missing_tasks": 0,
            "possible_criteria": 4,
            "graded_criteria": 4,
            "passed_criteria": 3,
            "task_success": 0,
            "complete": true,
            "accuracy": 0.75,
            "observed_accuracy": 0.75
          }
        ],
        "complete_repeats": 3,
        "eligible": true,
        "ineligible_reasons": [],
        "statistics": {
          "accuracy": {
            "mean": 0.75,
            "sample_sd": 0.0,
            "n": 3
          },
          "passed_criteria": {
            "mean": 3.0,
            "sample_sd": 0.0,
            "n": 3
          },
          "task_success": {
            "mean": 0.0,
            "sample_sd": 0.0,
            "n": 3
          }
        },
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 3,
          "graded_criteria": 12,
          "passed_criteria": 9,
          "mean_observed_accuracy": 0.75
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
        "variant": "human",
        "language": "bn",
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
        "variant": "human",
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
        "variant": "human",
        "language": "en",
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
            "passed_criteria": 3,
            "task_success": 0,
            "complete": true,
            "accuracy": 0.75,
            "observed_accuracy": 0.75
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 1,
            "missing_tasks": 0,
            "possible_criteria": 4,
            "graded_criteria": 4,
            "passed_criteria": 3,
            "task_success": 0,
            "complete": true,
            "accuracy": 0.75,
            "observed_accuracy": 0.75
          }
        ],
        "complete_repeats": 3,
        "eligible": true,
        "ineligible_reasons": [],
        "statistics": {
          "accuracy": {
            "mean": 0.8333333333333334,
            "sample_sd": 0.14433756729740643,
            "n": 3
          },
          "passed_criteria": {
            "mean": 3.3333333333333335,
            "sample_sd": 0.5773502691896257,
            "n": 3
          },
          "task_success": {
            "mean": 0.3333333333333333,
            "sample_sd": 0.5773502691896257,
            "n": 3
          }
        },
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 3,
          "graded_criteria": 12,
          "passed_criteria": 10,
          "mean_observed_accuracy": 0.8333333333333334
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
            "passed_criteria": 3,
            "task_success": 0,
            "complete": true,
            "accuracy": 0.75,
            "observed_accuracy": 0.75
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
            "mean": 0.9166666666666666,
            "sample_sd": 0.14433756729740643,
            "n": 3
          },
          "passed_criteria": {
            "mean": 3.6666666666666665,
            "sample_sd": 0.5773502691896257,
            "n": 3
          },
          "task_success": {
            "mean": 0.6666666666666666,
            "sample_sd": 0.5773502691896257,
            "n": 3
          }
        },
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 3,
          "graded_criteria": 12,
          "passed_criteria": 11,
          "mean_observed_accuracy": 0.9166666666666666
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
        "variant": "human",
        "language": "hi",
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
        "variant": "human",
        "language": "id",
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
            "passed_criteria": 3,
            "task_success": 0,
            "complete": true,
            "accuracy": 0.75,
            "observed_accuracy": 0.75
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 1,
            "missing_tasks": 0,
            "possible_criteria": 4,
            "graded_criteria": 4,
            "passed_criteria": 3,
            "task_success": 0,
            "complete": true,
            "accuracy": 0.75,
            "observed_accuracy": 0.75
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 1,
            "missing_tasks": 0,
            "possible_criteria": 4,
            "graded_criteria": 4,
            "passed_criteria": 3,
            "task_success": 0,
            "complete": true,
            "accuracy": 0.75,
            "observed_accuracy": 0.75
          }
        ],
        "complete_repeats": 3,
        "eligible": true,
        "ineligible_reasons": [],
        "statistics": {
          "accuracy": {
            "mean": 0.75,
            "sample_sd": 0.0,
            "n": 3
          },
          "passed_criteria": {
            "mean": 3.0,
            "sample_sd": 0.0,
            "n": 3
          },
          "task_success": {
            "mean": 0.0,
            "sample_sd": 0.0,
            "n": 3
          }
        },
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 3,
          "graded_criteria": 12,
          "passed_criteria": 9,
          "mean_observed_accuracy": 0.75
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
        "variant": "human",
        "language": "ko",
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
        "variant": "human",
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
        "variant": "human",
        "language": "pt",
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
            "passed_criteria": 2,
            "task_success": 0,
            "complete": true,
            "accuracy": 0.5,
            "observed_accuracy": 0.5
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
            "passed_criteria": 2,
            "task_success": 0,
            "complete": true,
            "accuracy": 0.5,
            "observed_accuracy": 0.5
          }
        ],
        "complete_repeats": 3,
        "eligible": true,
        "ineligible_reasons": [],
        "statistics": {
          "accuracy": {
            "mean": 0.6666666666666666,
            "sample_sd": 0.28867513459481287,
            "n": 3
          },
          "passed_criteria": {
            "mean": 2.6666666666666665,
            "sample_sd": 1.1547005383792515,
            "n": 3
          },
          "task_success": {
            "mean": 0.3333333333333333,
            "sample_sd": 0.5773502691896257,
            "n": 3
          }
        },
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 3,
          "graded_criteria": 12,
          "passed_criteria": 8,
          "mean_observed_accuracy": 0.6666666666666666
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
        "variant": "human",
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
        "variant": "human",
        "language": "ur",
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
        "variant": "human",
        "language": "zh",
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
        "language": "ar",
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
        "language": "bn",
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
        "language": "en",
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
        "language": "es",
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
        "language": "hi",
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
        "language": "id",
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
            "passed_criteria": 3,
            "task_success": 0,
            "complete": true,
            "accuracy": 0.75,
            "observed_accuracy": 0.75
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 1,
            "missing_tasks": 0,
            "possible_criteria": 4,
            "graded_criteria": 4,
            "passed_criteria": 3,
            "task_success": 0,
            "complete": true,
            "accuracy": 0.75,
            "observed_accuracy": 0.75
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 1,
            "missing_tasks": 0,
            "possible_criteria": 4,
            "graded_criteria": 4,
            "passed_criteria": 3,
            "task_success": 0,
            "complete": true,
            "accuracy": 0.75,
            "observed_accuracy": 0.75
          }
        ],
        "complete_repeats": 3,
        "eligible": true,
        "ineligible_reasons": [],
        "statistics": {
          "accuracy": {
            "mean": 0.75,
            "sample_sd": 0.0,
            "n": 3
          },
          "passed_criteria": {
            "mean": 3.0,
            "sample_sd": 0.0,
            "n": 3
          },
          "task_success": {
            "mean": 0.0,
            "sample_sd": 0.0,
            "n": 3
          }
        },
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 3,
          "graded_criteria": 12,
          "passed_criteria": 9,
          "mean_observed_accuracy": 0.75
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
        "language": "pt",
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
            "passed_criteria": 2,
            "task_success": 0,
            "complete": true,
            "accuracy": 0.5,
            "observed_accuracy": 0.5
          },
          {
            "repeat": 1,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 1,
            "missing_tasks": 0,
            "possible_criteria": 4,
            "graded_criteria": 4,
            "passed_criteria": 2,
            "task_success": 0,
            "complete": true,
            "accuracy": 0.5,
            "observed_accuracy": 0.5
          },
          {
            "repeat": 2,
            "scheduled_tasks": 1,
            "rows_present": 1,
            "graded_tasks": 1,
            "missing_tasks": 0,
            "possible_criteria": 4,
            "graded_criteria": 4,
            "passed_criteria": 2,
            "task_success": 0,
            "complete": true,
            "accuracy": 0.5,
            "observed_accuracy": 0.5
          }
        ],
        "complete_repeats": 3,
        "eligible": true,
        "ineligible_reasons": [],
        "statistics": {
          "accuracy": {
            "mean": 0.5,
            "sample_sd": 0.0,
            "n": 3
          },
          "passed_criteria": {
            "mean": 2.0,
            "sample_sd": 0.0,
            "n": 3
          },
          "task_success": {
            "mean": 0.0,
            "sample_sd": 0.0,
            "n": 3
          }
        },
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 3,
          "graded_criteria": 12,
          "passed_criteria": 6,
          "mean_observed_accuracy": 0.5
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
        "language": "ur",
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
        "language": "zh",
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
            "graded_tasks": 17,
            "missing_tasks": 0,
            "possible_criteria": 68,
            "graded_criteria": 68,
            "passed_criteria": 47,
            "task_success": 7,
            "complete": true,
            "accuracy": 0.6911764705882353,
            "observed_accuracy": 0.6911764705882353
          },
          {
            "repeat": 1,
            "scheduled_tasks": 17,
            "rows_present": 17,
            "graded_tasks": 17,
            "missing_tasks": 0,
            "possible_criteria": 68,
            "graded_criteria": 68,
            "passed_criteria": 51,
            "task_success": 9,
            "complete": true,
            "accuracy": 0.75,
            "observed_accuracy": 0.75
          },
          {
            "repeat": 2,
            "scheduled_tasks": 17,
            "rows_present": 17,
            "graded_tasks": 17,
            "missing_tasks": 0,
            "possible_criteria": 68,
            "graded_criteria": 68,
            "passed_criteria": 46,
            "task_success": 7,
            "complete": true,
            "accuracy": 0.6764705882352942,
            "observed_accuracy": 0.6764705882352942
          }
        ],
        "complete_repeats": 3,
        "eligible": true,
        "ineligible_reasons": [],
        "statistics": {
          "accuracy": {
            "mean": 0.7058823529411765,
            "sample_sd": 0.03890810751565573,
            "n": 3
          },
          "passed_criteria": {
            "mean": 48.0,
            "sample_sd": 2.6457513110645907,
            "n": 3
          },
          "task_success": {
            "mean": 7.666666666666667,
            "sample_sd": 1.1547005383792515,
            "n": 3
          }
        },
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 3,
          "graded_criteria": 204,
          "passed_criteria": 144,
          "mean_observed_accuracy": 0.7058823529411765
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
            "graded_tasks": 17,
            "missing_tasks": 0,
            "possible_criteria": 68,
            "graded_criteria": 68,
            "passed_criteria": 62,
            "task_success": 13,
            "complete": true,
            "accuracy": 0.9117647058823529,
            "observed_accuracy": 0.9117647058823529
          },
          {
            "repeat": 1,
            "scheduled_tasks": 17,
            "rows_present": 17,
            "graded_tasks": 17,
            "missing_tasks": 0,
            "possible_criteria": 68,
            "graded_criteria": 68,
            "passed_criteria": 59,
            "task_success": 11,
            "complete": true,
            "accuracy": 0.8676470588235294,
            "observed_accuracy": 0.8676470588235294
          },
          {
            "repeat": 2,
            "scheduled_tasks": 17,
            "rows_present": 17,
            "graded_tasks": 17,
            "missing_tasks": 0,
            "possible_criteria": 68,
            "graded_criteria": 68,
            "passed_criteria": 62,
            "task_success": 14,
            "complete": true,
            "accuracy": 0.9117647058823529,
            "observed_accuracy": 0.9117647058823529
          }
        ],
        "complete_repeats": 3,
        "eligible": true,
        "ineligible_reasons": [],
        "statistics": {
          "accuracy": {
            "mean": 0.8970588235294118,
            "sample_sd": 0.02547133540542464,
            "n": 3
          },
          "passed_criteria": {
            "mean": 61.0,
            "sample_sd": 1.7320508075688772,
            "n": 3
          },
          "task_success": {
            "mean": 12.666666666666666,
            "sample_sd": 1.5275252316519468,
            "n": 3
          }
        },
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 3,
          "graded_criteria": 204,
          "passed_criteria": 183,
          "mean_observed_accuracy": 0.8970588235294118
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
            "graded_tasks": 17,
            "missing_tasks": 0,
            "possible_criteria": 68,
            "graded_criteria": 68,
            "passed_criteria": 65,
            "task_success": 15,
            "complete": true,
            "accuracy": 0.9558823529411765,
            "observed_accuracy": 0.9558823529411765
          },
          {
            "repeat": 1,
            "scheduled_tasks": 17,
            "rows_present": 17,
            "graded_tasks": 17,
            "missing_tasks": 0,
            "possible_criteria": 68,
            "graded_criteria": 68,
            "passed_criteria": 65,
            "task_success": 14,
            "complete": true,
            "accuracy": 0.9558823529411765,
            "observed_accuracy": 0.9558823529411765
          },
          {
            "repeat": 2,
            "scheduled_tasks": 17,
            "rows_present": 17,
            "graded_tasks": 17,
            "missing_tasks": 0,
            "possible_criteria": 68,
            "graded_criteria": 68,
            "passed_criteria": 64,
            "task_success": 14,
            "complete": true,
            "accuracy": 0.9411764705882353,
            "observed_accuracy": 0.9411764705882353
          }
        ],
        "complete_repeats": 3,
        "eligible": true,
        "ineligible_reasons": [],
        "statistics": {
          "accuracy": {
            "mean": 0.9509803921568628,
            "sample_sd": 0.00849044513514159,
            "n": 3
          },
          "passed_criteria": {
            "mean": 64.66666666666667,
            "sample_sd": 0.5773502691896257,
            "n": 3
          },
          "task_success": {
            "mean": 14.333333333333334,
            "sample_sd": 0.5773502691896257,
            "n": 3
          }
        },
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 3,
          "graded_criteria": 204,
          "passed_criteria": 194,
          "mean_observed_accuracy": 0.9509803921568628
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
            "graded_tasks": 17,
            "missing_tasks": 0,
            "possible_criteria": 68,
            "graded_criteria": 68,
            "passed_criteria": 65,
            "task_success": 15,
            "complete": true,
            "accuracy": 0.9558823529411765,
            "observed_accuracy": 0.9558823529411765
          },
          {
            "repeat": 1,
            "scheduled_tasks": 17,
            "rows_present": 17,
            "graded_tasks": 17,
            "missing_tasks": 0,
            "possible_criteria": 68,
            "graded_criteria": 68,
            "passed_criteria": 65,
            "task_success": 15,
            "complete": true,
            "accuracy": 0.9558823529411765,
            "observed_accuracy": 0.9558823529411765
          },
          {
            "repeat": 2,
            "scheduled_tasks": 17,
            "rows_present": 17,
            "graded_tasks": 17,
            "missing_tasks": 0,
            "possible_criteria": 68,
            "graded_criteria": 68,
            "passed_criteria": 65,
            "task_success": 15,
            "complete": true,
            "accuracy": 0.9558823529411765,
            "observed_accuracy": 0.9558823529411765
          }
        ],
        "complete_repeats": 3,
        "eligible": true,
        "ineligible_reasons": [],
        "statistics": {
          "accuracy": {
            "mean": 0.9558823529411765,
            "sample_sd": 0.0,
            "n": 3
          },
          "passed_criteria": {
            "mean": 65.0,
            "sample_sd": 0.0,
            "n": 3
          },
          "task_success": {
            "mean": 15.0,
            "sample_sd": 0.0,
            "n": 3
          }
        },
        "observed_partial": {
          "eligible": false,
          "repeats_with_grades": 3,
          "graded_criteria": 204,
          "passed_criteria": 195,
          "mean_observed_accuracy": 0.9558823529411765
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
            "complete": true,
            "passed_criteria_diff": 15,
            "accuracy_diff": 0.22058823529411764,
            "task_success_diff": 6
          },
          {
            "repeat": 1,
            "complete": true,
            "passed_criteria_diff": 8,
            "accuracy_diff": 0.11764705882352944,
            "task_success_diff": 2
          },
          {
            "repeat": 2,
            "complete": true,
            "passed_criteria_diff": 16,
            "accuracy_diff": 0.23529411764705876,
            "task_success_diff": 7
          }
        ],
        "eligible": true,
        "ineligible_reasons": [],
        "statistics": {
          "passed_criteria_diff": {
            "mean": 13.0,
            "sample_sd": 4.358898943540674,
            "n": 3
          },
          "accuracy_diff": {
            "mean": 0.19117647058823528,
            "sample_sd": 0.0641014550520687,
            "n": 3
          },
          "task_success_diff": {
            "mean": 5.0,
            "sample_sd": 2.6457513110645907,
            "n": 3
          }
        }
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
            "complete": true,
            "passed_criteria_diff": 1,
            "accuracy_diff": 0.25,
            "task_success_diff": 1
          },
          {
            "repeat": 1,
            "complete": true,
            "passed_criteria_diff": 1,
            "accuracy_diff": 0.25,
            "task_success_diff": 1
          },
          {
            "repeat": 2,
            "complete": true,
            "passed_criteria_diff": 1,
            "accuracy_diff": 0.25,
            "task_success_diff": 1
          }
        ],
        "eligible": true,
        "ineligible_reasons": [],
        "statistics": {
          "passed_criteria_diff": {
            "mean": 1.0,
            "sample_sd": 0.0,
            "n": 3
          },
          "accuracy_diff": {
            "mean": 0.25,
            "sample_sd": 0.0,
            "n": 3
          },
          "task_success_diff": {
            "mean": 1.0,
            "sample_sd": 0.0,
            "n": 3
          }
        }
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
            "complete": true,
            "passed_criteria_diff": 0,
            "accuracy_diff": 0.0,
            "task_success_diff": 0
          },
          {
            "repeat": 1,
            "complete": true,
            "passed_criteria_diff": 0,
            "accuracy_diff": 0.0,
            "task_success_diff": 0
          },
          {
            "repeat": 2,
            "complete": true,
            "passed_criteria_diff": 0,
            "accuracy_diff": 0.0,
            "task_success_diff": 0
          }
        ],
        "eligible": true,
        "ineligible_reasons": [],
        "statistics": {
          "passed_criteria_diff": {
            "mean": 0.0,
            "sample_sd": 0.0,
            "n": 3
          },
          "accuracy_diff": {
            "mean": 0.0,
            "sample_sd": 0.0,
            "n": 3
          },
          "task_success_diff": {
            "mean": 0.0,
            "sample_sd": 0.0,
            "n": 3
          }
        }
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
            "complete": true,
            "passed_criteria_diff": 3,
            "accuracy_diff": 0.75,
            "task_success_diff": 1
          },
          {
            "repeat": 1,
            "complete": true,
            "passed_criteria_diff": 3,
            "accuracy_diff": 0.75,
            "task_success_diff": 1
          },
          {
            "repeat": 2,
            "complete": true,
            "passed_criteria_diff": 3,
            "accuracy_diff": 0.75,
            "task_success_diff": 1
          }
        ],
        "eligible": true,
        "ineligible_reasons": [],
        "statistics": {
          "passed_criteria_diff": {
            "mean": 3.0,
            "sample_sd": 0.0,
            "n": 3
          },
          "accuracy_diff": {
            "mean": 0.75,
            "sample_sd": 0.0,
            "n": 3
          },
          "task_success_diff": {
            "mean": 1.0,
            "sample_sd": 0.0,
            "n": 3
          }
        }
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
            "complete": true,
            "passed_criteria_diff": 1,
            "accuracy_diff": 0.25,
            "task_success_diff": 0
          },
          {
            "repeat": 1,
            "complete": true,
            "passed_criteria_diff": -1,
            "accuracy_diff": -0.25,
            "task_success_diff": -1
          },
          {
            "repeat": 2,
            "complete": true,
            "passed_criteria_diff": 2,
            "accuracy_diff": 0.5,
            "task_success_diff": 1
          }
        ],
        "eligible": true,
        "ineligible_reasons": [],
        "statistics": {
          "passed_criteria_diff": {
            "mean": 0.6666666666666666,
            "sample_sd": 1.5275252316519468,
            "n": 3
          },
          "accuracy_diff": {
            "mean": 0.16666666666666666,
            "sample_sd": 0.3818813079129867,
            "n": 3
          },
          "task_success_diff": {
            "mean": 0.0,
            "sample_sd": 1.0,
            "n": 3
          }
        }
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
            "complete": true,
            "passed_criteria_diff": 1,
            "accuracy_diff": 0.25,
            "task_success_diff": 0
          },
          {
            "repeat": 1,
            "complete": true,
            "passed_criteria_diff": -1,
            "accuracy_diff": -0.25,
            "task_success_diff": 0
          },
          {
            "repeat": 2,
            "complete": true,
            "passed_criteria_diff": 0,
            "accuracy_diff": 0.0,
            "task_success_diff": 0
          }
        ],
        "eligible": true,
        "ineligible_reasons": [],
        "statistics": {
          "passed_criteria_diff": {
            "mean": 0.0,
            "sample_sd": 1.0,
            "n": 3
          },
          "accuracy_diff": {
            "mean": 0.0,
            "sample_sd": 0.25,
            "n": 3
          },
          "task_success_diff": {
            "mean": 0.0,
            "sample_sd": 0.0,
            "n": 3
          }
        }
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
            "complete": true,
            "passed_criteria_diff": 0,
            "accuracy_diff": 0.0,
            "task_success_diff": 0
          },
          {
            "repeat": 1,
            "complete": true,
            "passed_criteria_diff": 0,
            "accuracy_diff": 0.0,
            "task_success_diff": 0
          },
          {
            "repeat": 2,
            "complete": true,
            "passed_criteria_diff": 0,
            "accuracy_diff": 0.0,
            "task_success_diff": 0
          }
        ],
        "eligible": true,
        "ineligible_reasons": [],
        "statistics": {
          "passed_criteria_diff": {
            "mean": 0.0,
            "sample_sd": 0.0,
            "n": 3
          },
          "accuracy_diff": {
            "mean": 0.0,
            "sample_sd": 0.0,
            "n": 3
          },
          "task_success_diff": {
            "mean": 0.0,
            "sample_sd": 0.0,
            "n": 3
          }
        }
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
            "complete": true,
            "passed_criteria_diff": 0,
            "accuracy_diff": 0.0,
            "task_success_diff": 0
          },
          {
            "repeat": 1,
            "complete": true,
            "passed_criteria_diff": 0,
            "accuracy_diff": 0.0,
            "task_success_diff": 0
          },
          {
            "repeat": 2,
            "complete": true,
            "passed_criteria_diff": 0,
            "accuracy_diff": 0.0,
            "task_success_diff": 0
          }
        ],
        "eligible": true,
        "ineligible_reasons": [],
        "statistics": {
          "passed_criteria_diff": {
            "mean": 0.0,
            "sample_sd": 0.0,
            "n": 3
          },
          "accuracy_diff": {
            "mean": 0.0,
            "sample_sd": 0.0,
            "n": 3
          },
          "task_success_diff": {
            "mean": 0.0,
            "sample_sd": 0.0,
            "n": 3
          }
        }
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
            "complete": true,
            "passed_criteria_diff": 3,
            "accuracy_diff": 0.75,
            "task_success_diff": 1
          },
          {
            "repeat": 1,
            "complete": true,
            "passed_criteria_diff": 1,
            "accuracy_diff": 0.25,
            "task_success_diff": 0
          },
          {
            "repeat": 2,
            "complete": true,
            "passed_criteria_diff": 3,
            "accuracy_diff": 0.75,
            "task_success_diff": 1
          }
        ],
        "eligible": true,
        "ineligible_reasons": [],
        "statistics": {
          "passed_criteria_diff": {
            "mean": 2.3333333333333335,
            "sample_sd": 1.1547005383792515,
            "n": 3
          },
          "accuracy_diff": {
            "mean": 0.5833333333333334,
            "sample_sd": 0.28867513459481287,
            "n": 3
          },
          "task_success_diff": {
            "mean": 0.6666666666666666,
            "sample_sd": 0.5773502691896257,
            "n": 3
          }
        }
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
            "complete": true,
            "passed_criteria_diff": 0,
            "accuracy_diff": 0.0,
            "task_success_diff": 0
          },
          {
            "repeat": 1,
            "complete": true,
            "passed_criteria_diff": 0,
            "accuracy_diff": 0.0,
            "task_success_diff": 0
          },
          {
            "repeat": 2,
            "complete": true,
            "passed_criteria_diff": 0,
            "accuracy_diff": 0.0,
            "task_success_diff": 0
          }
        ],
        "eligible": true,
        "ineligible_reasons": [],
        "statistics": {
          "passed_criteria_diff": {
            "mean": 0.0,
            "sample_sd": 0.0,
            "n": 3
          },
          "accuracy_diff": {
            "mean": 0.0,
            "sample_sd": 0.0,
            "n": 3
          },
          "task_success_diff": {
            "mean": 0.0,
            "sample_sd": 0.0,
            "n": 3
          }
        }
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
            "complete": true,
            "passed_criteria_diff": 0,
            "accuracy_diff": 0.0,
            "task_success_diff": 0
          },
          {
            "repeat": 1,
            "complete": true,
            "passed_criteria_diff": 0,
            "accuracy_diff": 0.0,
            "task_success_diff": 0
          },
          {
            "repeat": 2,
            "complete": true,
            "passed_criteria_diff": 1,
            "accuracy_diff": 0.25,
            "task_success_diff": 1
          }
        ],
        "eligible": true,
        "ineligible_reasons": [],
        "statistics": {
          "passed_criteria_diff": {
            "mean": 0.3333333333333333,
            "sample_sd": 0.5773502691896257,
            "n": 3
          },
          "accuracy_diff": {
            "mean": 0.08333333333333333,
            "sample_sd": 0.14433756729740643,
            "n": 3
          },
          "task_success_diff": {
            "mean": 0.3333333333333333,
            "sample_sd": 0.5773502691896257,
            "n": 3
          }
        }
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
            "complete": true,
            "passed_criteria_diff": 3,
            "accuracy_diff": 0.75,
            "task_success_diff": 1
          },
          {
            "repeat": 1,
            "complete": true,
            "passed_criteria_diff": 2,
            "accuracy_diff": 0.5,
            "task_success_diff": 0
          },
          {
            "repeat": 2,
            "complete": true,
            "passed_criteria_diff": 3,
            "accuracy_diff": 0.75,
            "task_success_diff": 1
          }
        ],
        "eligible": true,
        "ineligible_reasons": [],
        "statistics": {
          "passed_criteria_diff": {
            "mean": 2.6666666666666665,
            "sample_sd": 0.5773502691896257,
            "n": 3
          },
          "accuracy_diff": {
            "mean": 0.6666666666666666,
            "sample_sd": 0.14433756729740643,
            "n": 3
          },
          "task_success_diff": {
            "mean": 0.6666666666666666,
            "sample_sd": 0.5773502691896257,
            "n": 3
          }
        }
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
            "complete": true,
            "passed_criteria_diff": 0,
            "accuracy_diff": 0.0,
            "task_success_diff": 0
          },
          {
            "repeat": 1,
            "complete": true,
            "passed_criteria_diff": 0,
            "accuracy_diff": 0.0,
            "task_success_diff": 0
          },
          {
            "repeat": 2,
            "complete": true,
            "passed_criteria_diff": 0,
            "accuracy_diff": 0.0,
            "task_success_diff": 0
          }
        ],
        "eligible": true,
        "ineligible_reasons": [],
        "statistics": {
          "passed_criteria_diff": {
            "mean": 0.0,
            "sample_sd": 0.0,
            "n": 3
          },
          "accuracy_diff": {
            "mean": 0.0,
            "sample_sd": 0.0,
            "n": 3
          },
          "task_success_diff": {
            "mean": 0.0,
            "sample_sd": 0.0,
            "n": 3
          }
        }
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
            "complete": true,
            "passed_criteria_diff": 0,
            "accuracy_diff": 0.0,
            "task_success_diff": 0
          },
          {
            "repeat": 1,
            "complete": true,
            "passed_criteria_diff": 0,
            "accuracy_diff": 0.0,
            "task_success_diff": 0
          },
          {
            "repeat": 2,
            "complete": true,
            "passed_criteria_diff": 0,
            "accuracy_diff": 0.0,
            "task_success_diff": 0
          }
        ],
        "eligible": true,
        "ineligible_reasons": [],
        "statistics": {
          "passed_criteria_diff": {
            "mean": 0.0,
            "sample_sd": 0.0,
            "n": 3
          },
          "accuracy_diff": {
            "mean": 0.0,
            "sample_sd": 0.0,
            "n": 3
          },
          "task_success_diff": {
            "mean": 0.0,
            "sample_sd": 0.0,
            "n": 3
          }
        }
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
            "complete": true,
            "passed_criteria_diff": 2,
            "accuracy_diff": 0.5,
            "task_success_diff": 1
          },
          {
            "repeat": 1,
            "complete": true,
            "passed_criteria_diff": 3,
            "accuracy_diff": 0.75,
            "task_success_diff": 1
          },
          {
            "repeat": 2,
            "complete": true,
            "passed_criteria_diff": 3,
            "accuracy_diff": 0.75,
            "task_success_diff": 1
          }
        ],
        "eligible": true,
        "ineligible_reasons": [],
        "statistics": {
          "passed_criteria_diff": {
            "mean": 2.6666666666666665,
            "sample_sd": 0.5773502691896257,
            "n": 3
          },
          "accuracy_diff": {
            "mean": 0.6666666666666666,
            "sample_sd": 0.14433756729740643,
            "n": 3
          },
          "task_success_diff": {
            "mean": 1.0,
            "sample_sd": 0.0,
            "n": 3
          }
        }
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
            "complete": true,
            "passed_criteria_diff": 1,
            "accuracy_diff": 0.25,
            "task_success_diff": 1
          },
          {
            "repeat": 1,
            "complete": true,
            "passed_criteria_diff": 0,
            "accuracy_diff": 0.0,
            "task_success_diff": 0
          },
          {
            "repeat": 2,
            "complete": true,
            "passed_criteria_diff": 0,
            "accuracy_diff": 0.0,
            "task_success_diff": 0
          }
        ],
        "eligible": true,
        "ineligible_reasons": [],
        "statistics": {
          "passed_criteria_diff": {
            "mean": 0.3333333333333333,
            "sample_sd": 0.5773502691896257,
            "n": 3
          },
          "accuracy_diff": {
            "mean": 0.08333333333333333,
            "sample_sd": 0.14433756729740643,
            "n": 3
          },
          "task_success_diff": {
            "mean": 0.3333333333333333,
            "sample_sd": 0.5773502691896257,
            "n": 3
          }
        }
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
            "complete": true,
            "passed_criteria_diff": 0,
            "accuracy_diff": 0.0,
            "task_success_diff": 0
          },
          {
            "repeat": 1,
            "complete": true,
            "passed_criteria_diff": 0,
            "accuracy_diff": 0.0,
            "task_success_diff": 0
          },
          {
            "repeat": 2,
            "complete": true,
            "passed_criteria_diff": 0,
            "accuracy_diff": 0.0,
            "task_success_diff": 0
          }
        ],
        "eligible": true,
        "ineligible_reasons": [],
        "statistics": {
          "passed_criteria_diff": {
            "mean": 0.0,
            "sample_sd": 0.0,
            "n": 3
          },
          "accuracy_diff": {
            "mean": 0.0,
            "sample_sd": 0.0,
            "n": 3
          },
          "task_success_diff": {
            "mean": 0.0,
            "sample_sd": 0.0,
            "n": 3
          }
        }
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
            "complete": true,
            "passed_criteria_diff": 0,
            "accuracy_diff": 0.0,
            "task_success_diff": 0
          },
          {
            "repeat": 1,
            "complete": true,
            "passed_criteria_diff": 0,
            "accuracy_diff": 0.0,
            "task_success_diff": 0
          },
          {
            "repeat": 2,
            "complete": true,
            "passed_criteria_diff": 0,
            "accuracy_diff": 0.0,
            "task_success_diff": 0
          }
        ],
        "eligible": true,
        "ineligible_reasons": [],
        "statistics": {
          "passed_criteria_diff": {
            "mean": 0.0,
            "sample_sd": 0.0,
            "n": 3
          },
          "accuracy_diff": {
            "mean": 0.0,
            "sample_sd": 0.0,
            "n": 3
          },
          "task_success_diff": {
            "mean": 0.0,
            "sample_sd": 0.0,
            "n": 3
          }
        }
      }
    ],
    "holdout_eligibility": {
      "split": "holdout",
      "present": true,
      "variants": {
        "baseline": {
          "eligible": true,
          "ineligible_reasons": []
        },
        "candidate": {
          "eligible": true,
          "ineligible_reasons": []
        },
        "human": {
          "eligible": true,
          "ineligible_reasons": []
        },
        "original": {
          "eligible": true,
          "ineligible_reasons": []
        }
      },
      "paired_eligible": true,
      "decision": null,
      "note": "Statistical eligibility only; this report adopts and enables nothing."
    }
  },
  "execution": {
    "status": "open",
    "stop_reason": null,
    "budget": {
      "max_calls": 411,
      "max_seconds": 7200,
      "max_reported_tokens": 12000000,
      "workers": 3
    },
    "calls": 411,
    "by_status": {
      "completed": 408,
      "interrupted": 3
    },
    "reported_tokens": 6497711,
    "unknown_usage_calls": 3,
    "max_in_flight": 3,
    "rejected_records": 0,
    "elapsed_seconds": 1720.7743616000007,
    "note": "Budgets are checked before each batch. Calls already in flight (at most the worker count) can exceed call/token/time budgets; the adapter has a fixed per-call timeout and the provider offers no hard token cap. Reported usage is actual CLI-reported usage only."
  }
}
```
