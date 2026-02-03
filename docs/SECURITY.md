# Security & Compliance Notes (Reference Implementation)
This is a reference build; swap stubs for enterprise controls.

## Data Minimization
- Adam ingests **control-health** metrics (queues, latency, SLA rates), not customer PII or transactions.
- Preferred ingestion is read-only + aggregation upstream.

## AuthN / AuthZ
- API uses an `X-API-Key` header stub (`api/main.py`).
- Replace with OAuth2/OIDC + RBAC and/or mTLS.

## Audit Logging
- Add structured logs for: forecast requests, replay requests, config changes.
- Forward to SIEM.

## Encryption
- TLS in transit everywhere; secrets in KMS/Vault.

## Multi-Tenancy
- Separate tenant configs (ontology) and datasets by namespace, enforce per-tenant auth boundaries.
