from app.shadow_mode import AtlasTraceRingBuffer


def test_shadow_ring_buffer_capacity_and_eviction(shadow_trace_factory) -> None:
    buffer = AtlasTraceRingBuffer(capacity=3)

    for index in range(5):
        buffer.append(shadow_trace_factory(f"request-{index}"))

    traces = buffer.snapshot()
    assert len(traces) == 3
    assert [trace.request_id for trace in traces] == ["request-2", "request-3", "request-4"]
