# Portable core and environment adapters

**English** · [Türkçe](tr/adapters.md)

Python modules make no remote calls. `core` validates profiles, dates and
preferences and deduplicates URL/DOI/events; `render` builds HTML/plain text and
checks image reviews; `mime` builds related → alternative + inline PNG/JPEG;
`delivery` handles recipients and send transitions; `store` provides CAS on the
same filesystem. The CLI offers only `init`, `doctor`, and `prepare`.

An email/scheduler adapter is not a preinstalled service in this repository.
`sincap.onboarding` prepares Gmail draft arguments/raw verification and Library
guarded replacement/readback. The [onboarding workflow](onboarding.md) supplies
the call sequence and two-Cloud-task CAS test. Apply this contract to the actual
available tool schemas. Never simulate success when a tool or required field
is missing.

## Email and durable state

The private record's `data` contains `profile_id`, `history`, and `deliveries`.
Create a delivery only once for each daily issue key; do not replace or reset
an existing record with `new_delivery`. `prepare` leaves history unchanged and
creates only a local package, not a provider draft.

1. Read user authorization, the verified connection profile, actual time, latest
   canonical state, and relevant Sent evidence. Use `delivery.assert_send_allowed`
   to check profile flags, local day/time, and self-test scope. Passing
   `user_authorized=True` does not create authorization.
2. Package reviewed HTML/plain text and image bytes with `mime.package`, obtaining
   `editorial_sha256` and a recipient snapshot. This hash is recipient-independent.
   Bind day/issue number, content, and `recipient_set_hash` to durable state.
   Use `delivery.to_header` for eligible remaining recipients only; no Cc/Bcc.
3. Inspect the actual mail schema. If full MIME or an equivalent structured MIME
   tree is supported, create one draft. Carry large byte/base64 inputs
   programmatically, never in model output or logs. Read the draft back and check
   From/To/Subject, plain/HTML, and CID hashes. `mime.verify` is an offline
   tree/byte check; the provider draft still needs its own readback.
4. Persist `delivery.reserve` in the current record using CAS and verify the
   committed version/readback. `LocalStore.cas(expected_version, data)` locks,
   checks the version, and verifies exact bytes. External stores need an
   equivalent atomic contract. Local locking is insufficient across isolated
   Cloud workspaces. Complete every read page for the same file/version; truncated
   JSON or old bytes returned with a new version label are not current state.
5. Recheck envelope, time, account, and record immediately before sending. Call
   `send_draft` once using only the connection and actual draft ID. Do not use a
   large full-MIME send, blind `update_draft`, or automatic retry with a new draft.
   An approval loop must not be bypassed by weakening approvals; keep the result
   uncertain and reconcile.
6. Apply `delivery.record_result` per recipient. `provider_accepted` needs the
   real message ID, matching Sent record, and evidence. `definitively_rejected`
   needs explicit non-acceptance evidence. Timeouts, cancellation, or missing
   results remain `uncertain`. Preserve successful recipients and block new sends
   while a recipient or attempt is uncertain.
7. `delivery.advance_once` advances the counter only on the first confirmed
   acceptance. Commit `core.record_publication` history/cutoff and delivery
   results in the same CAS. Partial repair retains the issue and excludes
   successful recipients. If state persistence fails, repair it from Sent without
   resending. A later bounce does not permit resetting accepted recipients to pending.

`provider_accepted` does not establish Inbox delivery; check the receiving
mailbox separately. An empty Sent search alone does not establish non-acceptance.

Local CAS is tested for processes sharing one canonical file on the same disk.
Network filesystems and other operating systems are unverified. A leftover lock
or conflict does not authorize breaking the lock or resending. Keep state backups
private and reconcile with Sent after restoration. Never put live ledgers in Git
or environment snapshots.

## Image handoff

Code cannot prove a photograph's relevance to a story. The agent actually checks
pixels, event/date, credit, source, and use rights; code checks completeness and
byte/hash binding. Every article needs an `image_decision`. A selected image has:

| Field | Contract |
| --- | --- |
| `article_id`, `event_key`, `issue_date` | Bind to the same story, event, and issue date. |
| `file` | Relative regular file under `--images-root`; symlinks and `..` are rejected. |
| `source_page`, `observed_on`, `image_url`, `observed_via` | Actually observed on the page/RSS; never an invented URL. |
| `use_scope`, `role` | `newsletter` for real issues, `contract_test` for tests; `story` or `explanatory`. |
| `sha256`, `mime_type`, `size_bytes`, `width`, `height` | Match actual bytes and decoding. |
| `alt`, `credit`, `rights_note`, `selection_reason` | Accurate short alt text/credit and private rights/choice rationale. |
| `access_status`, `review` | `normal_public_access`; `pixels_viewed`, `context_verified`, `date_verified`, `credit_verified`, and `rights_verified_for_scope` all true, plus a note. |

Use `render.inspect_image(Path(...))` on real PNG/JPEG files acquired normally.
Check for an existing decoder first. If installation would be needed, report the
capability gap; do not include unverified files. WebP conversion is unsupported.
Limits are 10 MiB/image, 20 MiB total, and 40 million pixels/image; lower provider
limits still apply.

If another existing tool supports acquisition, private handoff records must bind
issue key, preparation owner, article/event/observed URL, a single collector
claim, file reference/version, hash, and review. Commit and read back the claim
using CAS before downloading. The same claim never authorizes another download;
reconcile receipt/import conflicts. This repository assumes neither Library
xattrs nor a parent worker. Without a concrete adapter and real environment test,
report handoff as unverified and use an alternative image or a justified omission.

Stop a downloader on a direct security denial. A supported normal browser's
normal access to the same public source may be recorded separately; if it also
shows CAPTCHA/security/access restrictions, stop. Do not bypass with proxies,
impersonation, or hidden endpoints. Do not automatically reuse yesterday's or a
test issue's image.

## Scheduling and runtime context

An accepted schedule is not execution evidence. Verify the user's actual
timezone and target project. During the first real scheduled trigger, record the
correct runtime/repo revision, same durable state, email account, and self-test
scope. A returned chat ID is not a substitute.

`cloud_threads` and parent/child dispatch are not general APIs. Some environments
may have an existing verified dispatch route; do not assume it exists for a new
user. Use only verified methods. This package creates no scheduler adapter,
continuous worker, or Cloud environment.
