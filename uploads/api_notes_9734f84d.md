# Internal API Notes

## Authentication

Clients must send `Authorization: Bearer <token>` on every request.
Tokens expire after 24 hours. Refresh using `POST /v1/auth/refresh`.

## Rate limits

Free tier: 100 requests per minute.
Pro tier: 1000 requests per minute.

## Error format

All errors return JSON:

```json
{"error": {"code": "string", "message": "human-readable detail"}}
```

Common codes: `invalid_request`, `unauthorized`, `rate_limited`.
