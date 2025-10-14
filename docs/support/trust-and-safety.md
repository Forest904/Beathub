# Trust & Safety Playbook

## Contact Channels
- Abuse reports: `abuse@example.com`
- DMCA takedowns: `dmca@example.com`
- Law enforcement: `legal@example.com`
- Escalation Slack: `#cd-collector-safety`

## Intake Workflow
1. Acknowledge receipt within 1 business day.
2. Create ticket in the safety tracker with severity and reporter details.
3. Pull request logs using `request_id` if provided; store evidence in restricted bucket.

## Abuse Categories
- **Copyright / DMCA**: Forward to legal, disable download access for offending user, remove references.
- **Malicious use** (e.g., mass scraping): Temporarily suspend account; adjust rate limits.
- **Harassment / policy violations**: Investigate user account, issue warning, suspend if repeated.
- **Data deletion (GDPR/CCPA)**: Verify identity, purge user records from database and downloads directory, confirm completion.

## Response Actions
| Severity | Action | SLA |
| --- | --- | --- |
| Critical (legal/LE request) | Suspend account, disable downloads, notify legal | 4 hours |
| High (valid DMCA) | Remove requested content, notify user, track strikes | 24 hours |
| Medium (policy abuse) | Warning or temporary suspension | 48 hours |
| Low (spam/feedback) | Respond, log for product follow-up | 5 days |

## Takedown Procedure
1. Identify offending downloads via metadata (Spotify ID, user ID).
2. Delete local files or S3 objects and purge database rows.
3. Confirm removal with automated smoke check (download endpoint returns 404).
4. Update takedown log; send confirmation to reporter.

## Offboarding
- Disable login (`users.is_active = false`).
- Remove access tokens / sessions.
- Export user data if requested (JSON package).
- Delete residual downloads after 30-day grace unless legally required.

## Record Keeping
- Maintain incident log with timestamps, handlers, outcome.
- Retain DMCA records in compliance archive for 5 years.
- Review monthly for patterns requiring product or tooling updates.
