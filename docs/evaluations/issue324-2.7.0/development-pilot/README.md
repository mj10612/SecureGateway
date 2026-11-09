# Development-only capture pilot

These immutable copies were captured before the final 2.7.0 runner safeguards,
with package metadata 2.6.2 and scoring version 2. They are development evidence,
not holdout adoption results or actual model task-response scores.

The real loopback privacy capture measured all 102 requests and 786 private
occurrences: 751 protected, 35 full exposures, no partial/ambiguous exposures.
Public controls: 110 of 186 overmasked. Two Chinese/Japanese Claude responses
failed restoration after their masked payloads reached the fixture provider:
100/102 restored/replayed successfully, 102/102 outbound payload replays matched.
The separate task capture has 17 tasks; no interpretations were executed in this
pilot. Source/setting hashes and per-language/policy denominators are in the reports.

An earlier development reference audit passed 68/68, but it preceded the final
explicit length-counting policy. Its grades are not reused as final-policy audit
evidence. The separately frozen holdout reference audit uses the final policy.
