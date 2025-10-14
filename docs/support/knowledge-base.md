# BeatHub (CD-Collector) Knowledge Base

## Getting Started

1. **Sign in** with the credentials provided by your administrator.
2. **Submit a download request**
   - Navigate to **Discover → Download**.
   - Paste a Spotify album, playlist, or track URL.
   - Click **Download**. Requests enter the processing queue; the progress panel shows status.
3. **Monitor history**
   - Go to **My Previous Downloads** to view completed items.
   - Select an item to inspect metadata, track list, and available lyrics.

## Rate Limits & Quotas

| Limit | Default | Notes |
| --- | --- | --- |
| Concurrent downloads | 2 per user | Additional requests wait in queue. |
| API requests | 120/min per IP | Excess traffic returns HTTP 429. |
| Storage retention | 30 days | Older downloads may be purged automatically. |

Administrators can adjust these values via environment variables (`DOWNLOAD_QUEUE_WORKERS`, rate limiting settings, etc.).

## Frequently Asked Questions

### “Queued” status – what does it mean?
The platform processes jobs sequentially. When workers are busy you’ll see “Queued”. You can continue browsing; the download automatically progresses once workers free up. Admins monitor `/readyz` to ensure the queue remains healthy.

### Can I download FLAC or other formats?
Hosted environments default to MP3. Contact support if you require an alternate format—admins can change `SPOTDL_FORMAT` for your tenant.

### Lyrics say “Not found”.
Not all sources include embedded lyrics. Re-open the lyrics panel after a few minutes; if still unavailable, provide the track URL to support for manual review.

### How do I report abuse or takedown requests?
Email `abuse@example.com` (see [Trust & Safety playbook](trust-and-safety.md) for details).

### Who do I contact for help?
- General support: `support@example.com`
- Status updates: https://status.example.com
- Slack (internal): `#cd-collector-support`

## Troubleshooting

- **429 Rate limit**: Wait 60 seconds and retry. Persistent issues may indicate automated traffic; reach out to support.
- **Download failed**: Retry once. If it fails again, note the error code and the `X-Request-ID` header displayed in the UI; include both in your support ticket.
- **Login denied**: Use “Forgot password” or contact support to unlock your account.
- **No items in history**: Ensure you’re signed in. Downloads only appear if the job completed successfully.

## Escalation

If you encounter errors affecting multiple users (service outage, repeated failures), escalate to on-call via PagerDuty (`CD-Collector Prod` schedule) and reference the request IDs involved.
