from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

def setup_tracing(app, service_name: str, otlp_endpoint: str) -> None:
    resource = Resource.create({"service.name": service_name})
    
    exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
    
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    
    trace.set_tracer_provider(provider)
    
    FastAPIInstrumentor.instrument_app(app)