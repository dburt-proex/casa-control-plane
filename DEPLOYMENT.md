# CASA Control Plane: Production Deployment Guide

## Overview

This guide covers shipping CASA to production environments with security, observability, and operational excellence.

---

## Quick Start (5 minutes)

### 1. Clone & Install

```bash
git clone https://github.com/dburt-proex/casa-control-plane.git
cd casa-control-plane
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your production values
# CRITICAL: Change CASA_API_KEY to a strong random value
```

Generate a strong API key:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 3. Run Tests

```bash
pytest tests/ -v
# Should see: 88 passed
```

### 4. Start API Server

```bash
python -m uvicorn governance_api:app --host 0.0.0.0 --port 8000
```

API is now running at `http://localhost:8000`

---

## Deployment Options

### Docker (Recommended)

```dockerfile
FROM python:3.13-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV CASA_API_KEY=your-strong-key-here
ENV ENVIRONMENT=production

CMD ["uvicorn", "governance_api:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build & run:

```bash
docker build -t casa:latest .
docker run -p 8000:8000 \
  -e CASA_API_KEY=your-key \
  -e ENVIRONMENT=production \
  -v /data/ledger:/app/ledger \
  casa:latest
```

### Kubernetes (Helm)

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: casa-config
data:
  ENVIRONMENT: production
  LOG_LEVEL: INFO
  POLICY_FILE: /etc/casa/policy.json
  LEDGER_PATH: /data/ledger.log
---
apiVersion: v1
kind: Secret
metadata:
  name: casa-secrets
type: Opaque
stringData:
  CASA_API_KEY: <generate-strong-key>
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: casa-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: casa
  template:
    metadata:
      labels:
        app: casa
    spec:
      containers:
      - name: api
        image: casa:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: casa-config
        - secretRef:
            name: casa-secrets
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
        resources:
          requests:
            cpu: 100m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
        volumeMounts:
        - name: ledger
          mountPath: /data
      volumes:
      - name: ledger
        persistentVolumeClaim:
          claimName: casa-ledger-pvc
```

### Cloud Platforms

#### Heroku

```bash
heroku create casa-governance
heroku config:set CASA_API_KEY=<strong-key>
heroku config:set ENVIRONMENT=production
git push heroku main
heroku logs --tail
```

#### AWS ECS

```bash
# Push image to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 123456789.dkr.ecr.us-east-1.amazonaws.com

docker tag casa:latest 123456789.dkr.ecr.us-east-1.amazonaws.com/casa:latest
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/casa:latest

# Create ECS task definition with environment variables
# Deploy via CloudFormation or AWS CLI
```

---

## Security Hardening

### 1. API Authentication

**CASA requires Bearer token authentication** on all protected endpoints.

All requests must include:

```bash
curl -H "Authorization: Bearer $CASA_API_KEY" http://localhost:8000/evaluate
```

**⚠️ PRODUCTION REQUIREMENTS:**

- [ ] Change `CASA_API_KEY` from default value
- [ ] Use strong random key (32+ characters)
- [ ] Rotate key every 90 days minimum
- [ ] Store in secure secret manager (AWS Secrets Manager, HashiCorp Vault, etc.)
- [ ] Never commit API keys to git

### 2. Network Security

- [ ] **HTTPS/TLS only** in production (reverse proxy with SSL termination)
- [ ] **Firewall rules**: Restrict API endpoint access to known agent IPs
- [ ] **VPC/Private network**: Run CASA in private subnet, expose via VPN/proxy
- [ ] **Rate limiting**: Implement external rate limiting (nginx, API gateway)

### 3. Ledger Security

- [ ] **Persistent storage**: Mount ledger to persistent volume (don't lose data on restart)
- [ ] **Backup ledger daily** to secure storage (S3, GCS, Azure Blob)
- [ ] **Ledger integrity**: Verify SHA-256 hash chain on startup
  ```bash
  python -c "from CASA.audit_ledger import verify_ledger_integrity; print(verify_ledger_integrity())"
  ```
- [ ] **Access control**: Restrict ledger file read/write permissions (mode 600)

### 4. Policy Security

- [ ] **Version control policy changes**: Track all policy.json modifications in git
- [ ] **Dry-run before deploy**: Always use `/policy/dryrun` endpoint before applying new policies
- [ ] **Code review**: Require peer review of policy changes
- [ ] **Audit trail**: Log all policy changes to immutable ledger

### 5. Observability & Monitoring

Recommended monitoring stack:

| Component | Tool | Purpose |
|-----------|------|---------|
| **Metrics** | Prometheus | Scrape /metrics endpoint |
| **Logging** | ELK Stack / CloudWatch | Centralize all logs |
| **Tracing** | Jaeger / Datadog | Trace request flow |
| **Alerting** | PagerDuty / Opsgenie | On-call alerts |

Key metrics to monitor:

```
casa_requests_total{endpoint, status_code}
casa_decision_distribution{route: ALLOW|REVIEW|HALT}
casa_halt_rate_percent
casa_drift_index
casa_ledger_size_bytes
casa_policy_version
casa_api_latency_ms
```

### 6. Compliance & Audit

- [ ] **Audit log retention**: Keep ledger for 7+ years (compliance requirement)
- [ ] **Decision replay**: Use `/decision-replay/all` for regulatory audits
- [ ] **Decision immutability**: Cryptographic hash chain prevents tampering
- [ ] **Policy audit trail**: Every policy change recorded with version, timestamp, reason
- [ ] **Access logging**: Log all API requests with caller identity, action, timestamp

---

## Configuration

### Environment Variables

Required for production:

```bash
# Security
CASA_API_KEY=<strong-random-32-char-key>

# Infrastructure
ENVIRONMENT=production
LOG_LEVEL=INFO

# Paths
POLICY_FILE=/etc/casa/policy.json
LEDGER_PATH=/data/ledger.log

# CORS (restrict to your domains)
CORS_ORIGINS=https://app.example.com,https://api.example.com
```

### Policy Configuration

`policy.json` defines governance rules:

```json
{
  "policy_version": "1.0.0",
  "agents": {
    "agent_01": ["read_database", "write_database"],
    "analytics_agent": ["read_database"],
    "admin_agent": ["read_database", "write_database", "delete_database"]
  },
  "review": ["write_database"],
  "forbidden": ["delete_database"],
  "tier_rules": {
    "tier_0": {"max_risk": 25, "decision": "AUTO_ALLOW"},
    "tier_1": {"max_risk": 50, "decision": "REVIEW"},
    "tier_2": {"max_risk": 75, "decision": "REVIEW"},
    "tier_3": {"decision": "HALT"}
  }
}
```

---

## Health Checks

### Liveness Probe

```bash
curl http://localhost:8000/health
```

Response:

```json
{
  "status": "CASA Governance API running",
  "environment": "production",
  "log_level": "INFO",
  "policy_file": "/etc/casa/policy.json",
  "ledger_path": "/data/ledger.log"
}
```

### Readiness Probe

```bash
# Verify ledger is accessible
curl -H "Authorization: Bearer $CASA_API_KEY" http://localhost:8000/dashboard
```

---

## Testing in Production

### 1. Verify API Authentication

```bash
# Should fail (no auth)
curl http://localhost:8000/evaluate

# Should succeed
curl -H "Authorization: Bearer $CASA_API_KEY" \
  -X POST http://localhost:8000/evaluate \
  -H "Content-Type: application/json" \
  -d '{"agent":"agent_01", "action":"read_database", "signals":{}}'
```

### 2. Verify Policy Dry-Run

Before deploying new policy:

```bash
curl -H "Authorization: Bearer $CASA_API_KEY" \
  -X POST http://localhost:8000/policy/dryrun \
  -H "Content-Type: application/json" \
  -d '{"policy_candidate_path":"policy.v2.json"}'
```

### 3. Verify Decision Replay

Audit historical decisions:

```bash
curl -H "Authorization: Bearer $CASA_API_KEY" \
  http://localhost:8000/decision-replay/all
```

### 4. Verify Ledger Integrity

```bash
python -c "
from CASA.audit_ledger import verify_ledger_integrity
result = verify_ledger_integrity()
print(f\"Ledger valid: {result['valid']}\")
print(f\"Total entries: {result['total_entries']}\")
"
```

---

## Troubleshooting

### API Won't Start

```bash
# Check ports in use
lsof -i :8000

# Check Python version (need 3.11+)
python --version

# Verify imports
python -c "import governance_api; print('OK')"

# Check syntax errors
python -m py_compile governance_api.py
```

### Authentication Failures

```bash
# Verify API key is set
echo $CASA_API_KEY

# Verify in request header
curl -v -H "Authorization: Bearer test-key" http://localhost:8000/health
# Look for 403 Forbidden if key is wrong
```

### Ledger Issues

```bash
# Check file permissions
ls -la CASA/ledger.log

# Verify ledger readable
python -c "from CASA.audit_ledger import read_ledger; print(len(read_ledger()))"

# Verify hash chain
python -c "from CASA.audit_ledger import verify_ledger_integrity; print(verify_ledger_integrity())"
```

### Policy Issues

```bash
# Validate JSON syntax
python -c "import json; json.load(open('policy.json'))"

# Check policy loads
python -c "from CASA.policy_loader import load_policy; print(load_policy())"
```

---

## Performance Tuning

### Vertical Scaling

For high decision volume (1000+/sec):

- Allocate 2+ CPU cores
- Allocate 1-2 GB RAM minimum
- Use SSD for ledger storage
- Enable HTTP/2

### Horizontal Scaling

- Run multiple CASA instances behind load balancer
- Use shared ledger storage (NFS, S3, database)
- Implement sticky sessions if needed (usually not required)

### Decision Latency

Typical latency:

- `/evaluate`: < 10ms
- `/policy/dryrun`: 100-500ms (depends on ledger size)
- `/decision-replay/all`: 1-5s (depends on ledger size)

---

## Support & Issues

- **GitHub Issues**: https://github.com/dburt-proex/casa-control-plane/issues
- **Documentation**: See README.md for API details
- **Security**: Report vulns to security@casa-example.com
