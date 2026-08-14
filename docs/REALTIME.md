# Realtime transport

`RealtimePublisher` is the server-owned async interface used by the existing
WebSocket and SSE endpoints. `InMemoryPublisher` is the default and is suitable
for tests, a single local process, and the offline portfolio demo. The optional
`RedisPublisher` is selected with `REALTIME_BACKEND=redis` and the
`server[redis]` extra.

The transport publishes JSON events by channel and exposes async subscribers.
The old route shapes remain compatibility facades, so dashboard clients do not
need to know which publisher is selected. Redis, multi-worker coordination, and
hosted event delivery are optional integrations rather than default runtime
requirements.
