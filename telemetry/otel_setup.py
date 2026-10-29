"""
Bootstrap OpenTelemetry for the Runaway Agent Monitoring System.

Exports traces to:
  - Console (human-readable, colour-coded via Rich)
  - A local JSONL file at traces.jsonl (zero-dependency persistence)

Usage:
    from telemetry.otel_setup import setup_telemetry
    tracer = setup_telemetry("runaway-monitor")
"""
import json
import pathlib

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    ConsoleSpanExporter,
    SimpleSpanProcessor,
    SpanExporter,
    SpanExportResult,
)


class JsonlFileExporter(SpanExporter):
    """Writes finished spans as JSON lines to a local file."""

    def __init__(self, path: str = "traces.jsonl"):
        self._path = pathlib.Path(path)

    def export(self, spans):
        with self._path.open("a", encoding="utf-8") as fh:
            for span in spans:
                fh.write(
                    json.dumps(
                        {
                            "name": span.name,
                            "trace_id": format(span.context.trace_id, "032x"),
                            "span_id": format(span.context.span_id, "016x"),
                            "start_ns": span.start_time,
                            "end_ns": span.end_time,
                            "duration_ms": round(
                                (span.end_time - span.start_time) / 1_000_000, 3
                            )
                            if span.end_time
                            else None,
                            "status": span.status.status_code.name,
                            "attributes": dict(span.attributes or {}),
                            "events": [
                                {
                                    "name": e.name,
                                    "timestamp_ns": e.timestamp,
                                    "attributes": dict(e.attributes or {}),
                                }
                                for e in span.events
                            ],
                        }
                    )
                    + "\n"
                )
        return SpanExportResult.SUCCESS

    def shutdown(self):
        pass


def setup_telemetry(
    service_name: str = "runaway-monitor",
    traces_file: str = "traces.jsonl",
    console: bool = True,
) -> trace.Tracer:
    """
    Initialise a TracerProvider and return a named Tracer.

    Args:
        service_name: OTel service.name resource attribute.
        traces_file:  Path to local JSONL trace output file.
        console:      Whether to also emit spans to stdout.

    Returns:
        An opentelemetry.trace.Tracer ready to use.
    """
    resource = Resource.create({SERVICE_NAME: service_name})
    provider = TracerProvider(resource=resource)

    # Always write to file for offline persistence
    provider.add_span_processor(
        SimpleSpanProcessor(JsonlFileExporter(traces_file))
    )

    if console:
        provider.add_span_processor(
            SimpleSpanProcessor(ConsoleSpanExporter())
        )

    trace.set_tracer_provider(provider)
    return trace.get_tracer(service_name)
