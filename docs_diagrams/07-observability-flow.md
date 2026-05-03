```mermaid
flowchart TD
    API[FastAPI App] --> ACT[/metrics Endpoint]
    API --> LOGS[Application Logs]

    ACT --> PROM[Prometheus]
    PROM --> GRAF[Grafana]

    GRAF --> P1[Request Count]
    GRAF --> P2[Latency P95]
    GRAF --> P3[Model Version]
    GRAF --> P4[Prediction Count]
    GRAF --> P5[Error Rate]
```