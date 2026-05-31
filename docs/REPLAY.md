# Replay

## How Replay Works

AgentTrace captures enough state during a run to enable step-by-step replay and debugging.

## Capture Phase

During a run, the SDK records:
1. **Input state**: Every function argument, prompt, and configuration
2. **Output state**: Every return value, completion, and side-effect description
3. **Decision points**: Which branch the agent took and why
4. **Timing**: Exact duration of each step
5. **Cost**: Per-step cost attribution

## Restore Phase

Replay reconstructs a run by:
1. Loading all spans for a run ordered by `start_time`
2. Replaying the timeline in the dashboard
3. Highlighting each span's input/output at each step
4. Showing the decision flow between spans

## Step-Through Debugging

The dashboard provides a "replay mode" that:
- Steps through spans sequentially
- Shows the state of the agent at each point
- Highlights where errors occurred
- Displays cumulative cost and token usage as the run progresses

## Limitations

| Limitation | Reason |
|---|---|
| **No re-execution** | Replay is read-only; it shows recorded data, not live execution |
| **Non-deterministic LLM outputs** | Same prompt may produce different results on re-run |
| **Side effects** | Tool calls that mutate external state are not rolled back |
| **Missing context** | Only captured metadata is available; full program state is not recorded |

## Future Enhancements

- **Prompt replay**: Re-send recorded prompts to compare model behavior over time
- **Trace diffing**: Compare two runs side-by-side to identify divergence points
- **Mock replay**: Substitute recorded outputs for live API calls during testing
