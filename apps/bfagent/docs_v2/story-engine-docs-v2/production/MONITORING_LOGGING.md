# Story Engine - Monitoring & Logging

> **Focus**: Observability, Monitoring, Structured Logging  
> **Status**: Production Planning  
> **Updated**: 2025-11-09

---

## 📋 Table of Contents

1. [Logging Strategy](#logging-strategy)
2. [Metrics & Monitoring](#metrics--monitoring)
3. [Alerting](#alerting)
4. [Distributed Tracing](#distributed-tracing)
5. [Dashboards](#dashboards)

---

## 📝 Logging Strategy

### Structured Logging with structlog

```python
# config/logging.py
import structlog
import logging.config

def configure_logging():
    """Configure structured logging for production"""
    
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processor": structlog.processors.JSONRenderer(),
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "json",
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": "/var/log/storyengine/app.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "formatter": "json",
            },
        },
        "root": {
            "handlers": ["console", "file"],
            "level": "INFO",
        },
    })
```

### Usage in Code

```python
# apps/story_engine/agents/base_agent.py
import structlog

logger = structlog.get_logger()

class BaseStoryAgent:
    async def execute(self, state):
        # Bind context to logger
        log = logger.bind(
            agent=self.agent_name,
            beat_id=state.beat_id,
            iteration=state.iteration
        )
        
        log.info("agent_execution_started")
        
        try:
            result = await self._execute_internal(state)
            log.info(
                "agent_execution_completed",
                duration_seconds=result.duration,
                tokens_used=result.tokens
            )
            return result
            
        except Exception as e:
            log.error(
                "agent_execution_failed",
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True
            )
            raise
```

### Log Levels

```python
"""
Log Level Guidelines:

DEBUG: Detailed diagnostic info (disabled in production)
  - LLM prompts
  - Full API responses
  - State transitions

INFO: General informational messages
  - Agent executions
  - Chapter generation started/completed
  - Performance metrics

WARNING: Something unexpected but handled
  - Retries triggered
  - Fallback models used
  - Quality score below threshold

ERROR: Errors that were handled
  - Agent failures with recovery
  - Validation errors
  - Retry exhausted

CRITICAL: Errors requiring immediate attention
  - Database connection lost
  - All models failed
  - Data corruption detected
"""
```

### Sensitive Data Filtering

```python
# apps/story_engine/logging/filters.py
import structlog

class SensitiveDataFilter:
    """Filter sensitive data from logs"""
    
    SENSITIVE_KEYS = {
        'api_key', 'password', 'secret', 'token',
        'authorization', 'cookie', 'session'
    }
    
    def __call__(self, logger, method_name, event_dict):
        """Filter sensitive data"""
        
        for key in event_dict.keys():
            if any(s in key.lower() for s in self.SENSITIVE_KEYS):
                event_dict[key] = '***REDACTED***'
        
        # Truncate long content
        if 'content' in event_dict:
            content = event_dict['content']
            if len(content) > 500:
                event_dict['content'] = content[:500] + '...[truncated]'
        
        return event_dict

# Add to processor chain
structlog.configure(
    processors=[
        SensitiveDataFilter(),
        # ... other processors
    ]
)
```

---

## 📊 Metrics & Monitoring

### Custom Metrics with Datadog

```python
# apps/story_engine/monitoring/metrics.py
from datadog import statsd
import structlog
from contextlib import contextmanager
from time import perf_counter
from typing import Dict, List

logger = structlog.get_logger()

class MetricsCollector:
    """
    Collect and report metrics to Datadog.
    
    Metrics Categories:
    - Business: chapters_generated, quality_scores
    - Performance: agent_duration, llm_latency
    - Resources: token_usage, api_calls
    - Errors: error_rate, retry_count
    """
    
    def __init__(self, prefix: str = "storyengine"):
        self.prefix = prefix
    
    @contextmanager
    def timer(self, metric_name: str, tags: List[str] = None):
        """
        Context manager for timing operations.
        
        Usage:
            with metrics.timer("agent.execution", tags=["agent:architect"]):
                result = await agent.execute(state)
        """
        tags = tags or []
        start = perf_counter()
        
        try:
            yield
            
            duration = perf_counter() - start
            
            statsd.histogram(
                f"{self.prefix}.{metric_name}.duration",
                duration,
                tags=tags
            )
            
            statsd.increment(
                f"{self.prefix}.{metric_name}.success",
                tags=tags
            )
            
        except Exception as e:
            duration = perf_counter() - start
            
            statsd.histogram(
                f"{self.prefix}.{metric_name}.duration",
                duration,
                tags=tags + [f"error:{type(e).__name__}"]
            )
            
            statsd.increment(
                f"{self.prefix}.{metric_name}.error",
                tags=tags + [f"error_type:{type(e).__name__}"]
            )
            
            raise
    
    def gauge(self, metric_name: str, value: float, tags: List[str] = None):
        """Report a gauge metric (current value)"""
        statsd.gauge(
            f"{self.prefix}.{metric_name}",
            value,
            tags=tags or []
        )
    
    def increment(self, metric_name: str, value: int = 1, tags: List[str] = None):
        """Increment a counter"""
        statsd.increment(
            f"{self.prefix}.{metric_name}",
            value,
            tags=tags or []
        )
    
    def histogram(self, metric_name: str, value: float, tags: List[str] = None):
        """Report a histogram value"""
        statsd.histogram(
            f"{self.prefix}.{metric_name}",
            value,
            tags=tags or []
        )
    
    # ========== Business Metrics ==========
    
    def record_chapter_generated(
        self,
        word_count: int,
        quality_score: float,
        generation_time: float,
        agent_iterations: int
    ):
        """Record chapter generation metrics"""
        
        tags = [
            f"quality_tier:{self._quality_tier(quality_score)}",
            f"iterations:{agent_iterations}"
        ]
        
        self.increment("chapters.generated", tags=tags)
        self.histogram("chapters.word_count", word_count, tags=tags)
        self.histogram("chapters.quality_score", quality_score, tags=tags)
        self.histogram("chapters.generation_time", generation_time, tags=tags)
    
    def record_agent_execution(
        self,
        agent_name: str,
        duration: float,
        tokens_used: int,
        success: bool
    ):
        """Record agent execution metrics"""
        
        tags = [
            f"agent:{agent_name}",
            f"success:{success}"
        ]
        
        self.histogram("agent.duration", duration, tags=tags)
        self.histogram("agent.tokens", tokens_used, tags=tags)
        self.increment("agent.executions", tags=tags)
    
    def record_llm_call(
        self,
        model: str,
        duration: float,
        tokens_input: int,
        tokens_output: int,
        success: bool
    ):
        """Record LLM API call metrics"""
        
        tags = [
            f"model:{model}",
            f"success:{success}"
        ]
        
        self.histogram("llm.latency", duration, tags=tags)
        self.histogram("llm.tokens.input", tokens_input, tags=tags)
        self.histogram("llm.tokens.output", tokens_output, tags=tags)
        self.increment("llm.calls", tags=tags)
    
    # ========== Resource Metrics ==========
    
    def record_database_query(self, query_type: str, duration: float):
        """Record database query performance"""
        
        tags = [f"query_type:{query_type}"]
        self.histogram("db.query.duration", duration, tags=tags)
    
    def record_cache_hit(self, cache_type: str, hit: bool):
        """Record cache hit/miss"""
        
        tags = [
            f"cache:{cache_type}",
            f"hit:{hit}"
        ]
        self.increment("cache.access", tags=tags)
    
    # ========== Error Metrics ==========
    
    def record_error(
        self,
        error_type: str,
        severity: str,
        component: str
    ):
        """Record error occurrence"""
        
        tags = [
            f"error_type:{error_type}",
            f"severity:{severity}",
            f"component:{component}"
        ]
        
        self.increment("errors.count", tags=tags)
    
    def record_retry(
        self,
        operation: str,
        attempt: int,
        success: bool
    ):
        """Record retry attempt"""
        
        tags = [
            f"operation:{operation}",
            f"attempt:{attempt}",
            f"success:{success}"
        ]
        
        self.increment("retries.count", tags=tags)
    
    # ========== Helper Methods ==========
    
    @staticmethod
    def _quality_tier(score: float) -> str:
        """Convert quality score to tier"""
        if score >= 0.9:
            return "excellent"
        elif score >= 0.8:
            return "good"
        elif score >= 0.7:
            return "acceptable"
        else:
            return "poor"

# Global instance
metrics = MetricsCollector()
```

### Usage in Agents

```python
# apps/story_engine/agents/base_agent.py
from apps.story_engine.monitoring.metrics import metrics

class BaseStoryAgent:
    async def safe_llm_call(self, prompt: str) -> str:
        """LLM call with automatic metrics"""
        
        start = perf_counter()
        
        try:
            response = await self.llm.ainvoke(prompt)
            
            duration = perf_counter() - start
            
            # Record metrics
            metrics.record_llm_call(
                model=self.config.model,
                duration=duration,
                tokens_input=len(prompt.split()),
                tokens_output=len(response.content.split()),
                success=True
            )
            
            return response.content
            
        except Exception as e:
            duration = perf_counter() - start
            
            metrics.record_llm_call(
                model=self.config.model,
                duration=duration,
                tokens_input=0,
                tokens_output=0,
                success=False
            )
            
            raise
```

---

## 🚨 Alerting

### Alert Rules

```yaml
# alerts/storyengine.yaml
alerts:
  # Business Metrics
  - name: low_chapter_quality
    condition: avg(storyengine.chapters.quality_score) < 0.7
    window: 1h
    severity: warning
    notification: slack, email
    message: "Average chapter quality below threshold"
  
  # Performance
  - name: high_agent_latency
    condition: p95(storyengine.agent.duration) > 120
    window: 15m
    severity: warning
    notification: slack
    message: "Agent execution time high (p95 > 120s)"
  
  - name: llm_api_slow
    condition: p95(storyengine.llm.latency) > 30
    window: 5m
    severity: warning
    notification: slack
    message: "LLM API latency high (p95 > 30s)"
  
  # Errors
  - name: high_error_rate
    condition: rate(storyengine.errors.count) > 0.1
    window: 5m
    severity: critical
    notification: pagerduty, slack, email
    message: "Error rate above 10%"
  
  - name: agent_failures
    condition: rate(storyengine.agent.executions[success:false]) > 0.2
    window: 10m
    severity: critical
    notification: pagerduty
    message: "Agent failure rate > 20%"
  
  # Resources
  - name: high_token_usage
    condition: sum(storyengine.llm.tokens.output) > 1000000
    window: 1h
    severity: warning
    notification: slack, email
    message: "Token usage high (>1M tokens/hour)"
  
  - name: database_slow
    condition: p95(storyengine.db.query.duration) > 1.0
    window: 5m
    severity: warning
    notification: slack
    message: "Database queries slow (p95 > 1s)"
  
  # Infrastructure
  - name: app_down
    condition: sum(up{job="storyengine-app"}) == 0
    window: 2m
    severity: critical
    notification: pagerduty, slack
    message: "All app instances down"
  
  - name: db_connection_errors
    condition: rate(storyengine.errors.count[error_type:DatabaseError]) > 0
    window: 2m
    severity: critical
    notification: pagerduty
    message: "Database connection errors"
```

### Alert Manager

```python
# apps/story_engine/monitoring/alerts.py
import structlog
from typing import List, Dict
from dataclasses import dataclass
from datetime import datetime
import aiohttp

logger = structlog.get_logger()

@dataclass
class Alert:
    """Alert definition"""
    
    name: str
    severity: str  # 'info', 'warning', 'critical'
    message: str
    details: Dict
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class AlertManager:
    """
    Manage and send alerts to various channels.
    
    Channels:
    - Slack: For warnings and critical
    - Email: For critical alerts
    - PagerDuty: For critical system failures
    """
    
    def __init__(self):
        self.slack_webhook = os.getenv('SLACK_WEBHOOK_URL')
        self.pagerduty_key = os.getenv('PAGERDUTY_INTEGRATION_KEY')
        self.email_recipients = os.getenv('ALERT_EMAIL_RECIPIENTS', '').split(',')
    
    async def send_alert(self, alert: Alert):
        """
        Send alert to appropriate channels.
        
        Routing:
        - info → logs only
        - warning → logs + slack
        - critical → logs + slack + email + pagerduty
        """
        
        logger.bind(
            alert_name=alert.name,
            severity=alert.severity
        ).log(
            self._severity_to_level(alert.severity),
            "alert_triggered",
            message=alert.message,
            details=alert.details
        )
        
        # Route based on severity
        if alert.severity == 'warning':
            await self._send_slack(alert)
        
        elif alert.severity == 'critical':
            await asyncio.gather(
                self._send_slack(alert),
                self._send_email(alert),
                self._send_pagerduty(alert)
            )
    
    async def _send_slack(self, alert: Alert):
        """Send alert to Slack"""
        
        if not self.slack_webhook:
            logger.warning("slack_webhook_not_configured")
            return
        
        color = {
            'info': '#36a64f',
            'warning': '#ff9900',
            'critical': '#ff0000'
        }[alert.severity]
        
        payload = {
            "attachments": [{
                "color": color,
                "title": f"[{alert.severity.upper()}] {alert.name}",
                "text": alert.message,
                "fields": [
                    {
                        "title": key,
                        "value": str(value),
                        "short": True
                    }
                    for key, value in alert.details.items()
                ],
                "footer": "Story Engine Monitoring",
                "ts": int(alert.timestamp.timestamp())
            }]
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.slack_webhook,
                    json=payload
                ) as response:
                    if response.status != 200:
                        logger.error(
                            "slack_alert_failed",
                            status=response.status
                        )
        
        except Exception as e:
            logger.error(
                "slack_alert_error",
                error=str(e),
                exc_info=True
            )
    
    async def _send_email(self, alert: Alert):
        """Send alert via email"""
        
        from django.core.mail import send_mail
        
        subject = f"[{alert.severity.upper()}] {alert.name}"
        
        message = f"""
Alert: {alert.name}
Severity: {alert.severity}
Time: {alert.timestamp.isoformat()}

Message:
{alert.message}

Details:
{json.dumps(alert.details, indent=2)}
"""
        
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email='alerts@storyengine.com',
                recipient_list=self.email_recipients,
                fail_silently=False
            )
            
            logger.info("email_alert_sent", recipients=len(self.email_recipients))
            
        except Exception as e:
            logger.error(
                "email_alert_failed",
                error=str(e),
                exc_info=True
            )
    
    async def _send_pagerduty(self, alert: Alert):
        """Send alert to PagerDuty"""
        
        if not self.pagerduty_key:
            logger.warning("pagerduty_key_not_configured")
            return
        
        payload = {
            "routing_key": self.pagerduty_key,
            "event_action": "trigger",
            "payload": {
                "summary": alert.message,
                "severity": alert.severity,
                "source": "storyengine",
                "timestamp": alert.timestamp.isoformat(),
                "custom_details": alert.details
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://events.pagerduty.com/v2/enqueue",
                    json=payload
                ) as response:
                    if response.status != 202:
                        logger.error(
                            "pagerduty_alert_failed",
                            status=response.status
                        )
        
        except Exception as e:
            logger.error(
                "pagerduty_alert_error",
                error=str(e),
                exc_info=True
            )
    
    @staticmethod
    def _severity_to_level(severity: str) -> str:
        """Map severity to log level"""
        return {
            'info': 'info',
            'warning': 'warning',
            'critical': 'error'
        }[severity]

# Global instance
alert_manager = AlertManager()
```

---

## 🔍 Distributed Tracing

### OpenTelemetry Integration

```python
# apps/story_engine/monitoring/tracing.py
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.django import DjangoInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor

def setup_tracing():
    """Setup distributed tracing"""
    
    # Create tracer provider
    trace.set_tracer_provider(TracerProvider())
    
    # Configure OTLP exporter (Datadog, Jaeger, etc.)
    otlp_exporter = OTLPSpanExporter(
        endpoint=os.getenv('OTLP_ENDPOINT', 'localhost:4317')
    )
    
    # Add span processor
    trace.get_tracer_provider().add_span_processor(
        BatchSpanProcessor(otlp_exporter)
    )
    
    # Auto-instrument
    DjangoInstrumentor().instrument()
    Psycopg2Instrumentor().instrument()
    RedisInstrumentor().instrument()

# Usage in code
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

class BaseStoryAgent:
    async def execute(self, state):
        with tracer.start_as_current_span(
            f"{self.agent_name}.execute",
            attributes={
                "beat_id": state.beat_id,
                "iteration": state.iteration
            }
        ) as span:
            
            result = await self._execute_internal(state)
            
            span.set_attribute("tokens_used", result.tokens)
            span.set_attribute("quality_score", result.quality_score)
            
            return result
```

---

## 📈 Dashboards

### Datadog Dashboard Configuration

```json
{
  "title": "Story Engine - Production Dashboard",
  "description": "Main production monitoring dashboard",
  "widgets": [
    {
      "definition": {
        "title": "Chapter Generation Rate",
        "type": "timeseries",
        "requests": [
          {
            "q": "sum:storyengine.chapters.generated{*}.as_rate()",
            "display_type": "line"
          }
        ]
      }
    },
    {
      "definition": {
        "title": "Average Quality Score",
        "type": "timeseries",
        "requests": [
          {
            "q": "avg:storyengine.chapters.quality_score{*}",
            "display_type": "line"
          }
        ]
      }
    },
    {
      "definition": {
        "title": "Agent Performance",
        "type": "timeseries",
        "requests": [
          {
            "q": "avg:storyengine.agent.duration{*} by {agent}",
            "display_type": "line"
          }
        ]
      }
    },
    {
      "definition": {
        "title": "LLM Token Usage (hourly)",
        "type": "query_value",
        "requests": [
          {
            "q": "sum:storyengine.llm.tokens.output{*}.as_count()"
          }
        ]
      }
    },
    {
      "definition": {
        "title": "Error Rate",
        "type": "timeseries",
        "requests": [
          {
            "q": "sum:storyengine.errors.count{*}.as_rate()",
            "display_type": "bars",
            "style": {
              "palette": "warm"
            }
          }
        ]
      }
    }
  ]
}
```

---

## 📚 See Also

- [STORY_ENGINE_ARCHITECTURE.md](./STORY_ENGINE_ARCHITECTURE.md) - System architecture
- [ERROR_HANDLING.md](./ERROR_HANDLING.md) - Error handling
- [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) - Deployment
- [TESTING_STRATEGY.md](./TESTING_STRATEGY.md) - Testing

---

**Monitoring & Logging Version**: 1.0  
**Last Updated**: 2025-11-09  
**Status**: Production-Ready Observability
