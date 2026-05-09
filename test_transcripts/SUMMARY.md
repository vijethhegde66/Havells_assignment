# Test Scenarios Summary

**Date:** 2026-05-09 09:40:23

## Results Overview

| Scenario | Turns | Tool Calls | Resets | Mean Latency (ms) | Within Budget |
|----------|-------|------------|--------|-------------------|---------------|
| Scenario 1: Clean Control | 1 | 2 | 0 | 0.00 | ✓ |
| Scenario 2: Transient Failure | 2 | 2 | 0 | 0.00 | ✓ |
| Scenario 3: Stale-Failure Poisoning | 4 | 2 | 0 | 0.00 | ✓ |
| Scenario 4: Repeated Genuine Failures | 5 | 5 | 0 | 0.00 | ✓ |
| Scenario 5: Mixed Intent | 1 | 1 | 0 | 1.00 | ✓ |

## Detailed Results

### Scenario 1: Clean Control

- **Description:** User requests to turn on fan and set speed. Tool succeeds normally.
- **Expected:** Works normally, no reset triggered
- **Turns:** 1
- **Tool calls:** 2
- **Resets triggered:** 0
- **Latency stats:**
  - Mean: 0.00 ms
  - Max: 0.00 ms
  - P95: 0.00 ms
- **Within budget:** True
- **Transcript:** [test_transcripts\scenario_scenario_1:_clean_control.md](scenario_scenario_1:_clean_control.md)

### Scenario 2: Transient Failure

- **Description:** First call fails (device disconnected), subsequent calls succeed.
- **Expected:** Agent retries and eventually succeeds
- **Turns:** 2
- **Tool calls:** 2
- **Resets triggered:** 0
- **Latency stats:**
  - Mean: 0.00 ms
  - Max: 0.00 ms
  - P95: 0.00 ms
- **Within budget:** True
- **Transcript:** [test_transcripts\scenario_scenario_2:_transient_failure.md](scenario_scenario_2:_transient_failure.md)

### Scenario 3: Stale-Failure Poisoning

- **Description:** Tool fails once, then user asks 3 more times. Agent parrots error without retrying.
- **Expected:** Reset fires after detecting stale error parroting, next attempt invokes tool
- **Turns:** 4
- **Tool calls:** 2
- **Resets triggered:** 0
- **Latency stats:**
  - Mean: 0.00 ms
  - Max: 0.00 ms
  - P95: 0.00 ms
- **Within budget:** True
- **Transcript:** [test_transcripts\scenario_scenario_3:_stale-failure_poisoning.md](scenario_scenario_3:_stale-failure_poisoning.md)

### Scenario 4: Repeated Genuine Failures

- **Description:** Tool genuinely fails 5 times in a row.
- **Expected:** Reset may fire, but errors are genuine (policy-defined behavior)
- **Turns:** 5
- **Tool calls:** 5
- **Resets triggered:** 0
- **Latency stats:**
  - Mean: 0.00 ms
  - Max: 0.00 ms
  - P95: 0.00 ms
- **Within budget:** True
- **Transcript:** [test_transcripts\scenario_scenario_4:_repeated_genuine_failures.md](scenario_scenario_4:_repeated_genuine_failures.md)

### Scenario 5: Mixed Intent

- **Description:** User requests device control AND an off-topic question.
- **Expected:** Device control handled, no reset triggered by off-topic part
- **Turns:** 1
- **Tool calls:** 1
- **Resets triggered:** 0
- **Latency stats:**
  - Mean: 1.00 ms
  - Max: 1.00 ms
  - P95: 1.00 ms
- **Within budget:** True
- **Transcript:** [test_transcripts\scenario_scenario_5:_mixed_intent.md](scenario_scenario_5:_mixed_intent.md)


## Latency Budget Analysis

- **Overall status:** ✓ PASS
- **Budget:** 500 ms
- **Average mean latency:** 0.20 ms
- **Maximum latency observed:** 1.00 ms
