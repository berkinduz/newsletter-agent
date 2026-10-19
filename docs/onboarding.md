# Actionable setup workflow for the agent

**English** · [Türkçe](tr/onboarding.md)

The user can open the repository in their own ChatGPT/Codex environment and say:

> Set up Sincap Post for me. Follow AGENTS.md and docs/onboarding.md.
> Check the available tools first and show me the synthetic preview. Ask me only
> for my newsletter preferences and required action permissions; discover and
> fill in the technical fields yourself.

This is an agent/tool integration. Helpers below prepare and verify real
Gmail/Library call inputs; the agent makes external calls. Python commands do
not send email. A setup request is not unlimited external-action permission.
Use authorization already given; request missing test/send/schedule permission
after preparing a concrete preview. Developing this guide or testing it offline
does not authorize creating provider drafts, email, or schedules.

## 1. Discover capabilities, ask preferences, create private records

Read README/setup/AGENTS and run `bash scripts/setup.sh`. If `.local` exists,
resume the current stage; do not reset it with `init`. For a new installation,
`python3 -m sincap init --language en` also creates private `installation.json`.
Use `--language tr` if the user chooses Turkish.

Inspect actual schemas in the tool catalog. The minimum usable route is:

| Task | Required existing tools and fields |
| --- | --- |
| Account | Gmail `get_profile(link_id)`; choose a link only from the current schema's account list. |
| Draft | `create_draft(link_id, from_address, to, subject, payload)` with nested MIME, content_id, and base64_url_content. |
| Readback | `read_email(link_id, message_id, format="raw")`; this route is incomplete if full raw bytes are unavailable. |
| Send | `send_draft(link_id, draft_id)` and matching Sent search/read. |
| Shared record | Library create/read/replace with `expected_current_version` and complete file reads. |
| Schedule | Existing scheduler create plus a target or supported dispatch route that actually reaches this repo/shell. |

When a tool is missing, explain which stage remains usable. Tool visibility is
not connection success. Do not install new services, credentials, or plugins.

Collect missing newsletter preferences together, in the user's conversation
language. Do not ask again for answers already provided:

- Topics and preferred/excluded sources; the agent can research source choices.
- **“Should your newsletter be in Turkish or English?”**
  In Turkish: **“Bültenin Türkçe mi, İngilizce mi olmasını istersiniz?”**
  Record `tr` or `en` in `profile.language`. Do not infer this from chat language
  or silently choose the CLI default during agent-led setup.
- Reading length, greeting/signature, recipients, local delivery time, and timezone.

Use the selected language for the starter profile and matching synthetic issue,
then apply it to labels, topics, source display names, greeting, signature, and
all agent-written issue text. Preserve proper names and attribution. For an
existing profile, edit the same canonical record rather than initializing new
history; revalidate affected capability evidence after the profile hash changes.

If several mail accounts are suitable, offer readable account names for the
user to choose. Do not inherit another project's account/state/automation. On
the selected account, make a harmless `get_profile` call; respect any reconnect
or approval dependency. With the actual successful `structuredContent` object:

```python
from sincap import onboarding as o
installation["mail"] = o.mail_connection(selected_link, profile_reply["structuredContent"])
profile["delivery"]["sender"] = installation["mail"]["email"]
```

Discover identifiers yourself; do not ask for link/file/draft/environment IDs.
Record the actual runtime, Git origin/HEAD, and profile hash privately. Put the
user's chosen recipients in the profile; the first test is narrowed below.
Keep `delivery.enabled` and `schedule.enabled` false at this stage.

## 2. Produce a preview and prepare tool inputs

Use a sample profile, not a customized production profile, for the first demo.
Choose the command matching the user's language answer:

```sh
# English
python3 -m sincap prepare --demo --profile examples/profile.json --input examples/issue.json --at 2030-01-02T08:30:00Z --out .local/setup-preview-en
# Turkish
python3 -m sincap prepare --demo --profile examples/tr/profile.json --input examples/tr/issue.json --at 2030-01-02T08:30:00Z --out .local/setup-preview-tr
```

Show `preview.html` at wide and narrow widths. Apply the user's topics, sources,
language, length, signature, and time to the actual private profile. For a real
issue read sufficient source bodies and verify dates; inspect image access,
bytes, and pixels. Synthetic data is not real source-reading evidence.

`prepare` writes the envelope, content hash, and image manifest in `delivery.json`.
In the agent's private Python work:

```python
bundle = o.load_bundle(preview_directory)
test = o.self_test_bundle(bundle, installation["mail"], unique_test_key)
request = o.gmail_draft_args(test, installation["mail"])
```

Generate a unique `test/` key and record it privately. `request` is the complete
`create_draft` input: retain it in private JSON and transfer it programmatically
to the tool. Do not print base64 bytes in model output or logs. Show the changed
From/To/Subject to the user. Do not make the external call yet.

## 3. Verify CAS on a disposable probe, then bind canonical state

Without Library, manual use on one filesystem remains possible; recurring
publication across isolated Cloud tasks is not ready. Follow the current
Library skill's full-read, materialization, xattr, and writeback rules.

First create a separate private, synthetic, disposable Library probe, for example
`{"version":0,"data":{"probe_only":true,"marker":"initial"}}`. Include no real
profile, ledger, recipients, email, or history. Store its returned reference in
`installation.shared_state.probe_library_file_id`, separate from canonical
`library_file_id`.

Never test CAS by writing to the real canonical ledger before CAS is verified.
When resuming an installation, only read its canonical reference: do not reset
it, substitute a probe, or copy live data into a probe. All capability/stale
writes below target only the new disposable probe.

Every task must fully read the same reference. Complete all `has_more` pages
for one file/version, or materialize the full file under current Library rules.
Require successful `json.loads`/`JSON.parse` and a concrete current provider
version, such as actual materialization metadata's `current_version_number`.
Do not confuse this with the JSON domain `version`. A missing/non-integer
provider version leaves CAS unverified. Provider version `0` is valid for a new
file. `last_observed_version` is only a private note; reread the current remote
version before each operation. Do not assume canonical JSON contains its own
current provider version.

Write and readback sequence, targeting only the probe until CAS is established:

```python
candidate = o.library_candidate(snapshot, changed_data, unique_operation_id)
# Write candidate to a new private JSON file with mode 0600.
request = o.library_replace_args(probe_library_ref, actual_provider_version, candidate_path)
# Agent: library_replace_library_file(**request), then read the same entire file back.
o.verify_library_commit(candidate, full_readback, actual_provider_version, returned_new_version)
```

On conflict, reread and reconcile; never retry old bytes or remove the version
precondition. On timeout/uncertainty, reconcile full readback and `last_operation`
first. If the send reservation cannot be committed, do not send email.

**Real two-Cloud-task test**; this guide and offline tests do not establish it:

1. In task A read only the probe's provider version N, write a random A marker
   with CAS N, then verify full readback and new provider version M. Prepare a
   private continuation prompt containing the probe reference, expected Git
   origin/HEAD, N/M, and full candidate content hash. Needed setup preferences
   may go in this private prompt, never in the synthetic probe's content.
2. The user opens another task in the same saved Cloud project and supplies
   that prompt. Task B independently reads the same **probe**, verifies A's
   version/hash, and never writes the canonical ledger.
3. B attempts guarded replacement using only synthetic probe content and
   **stale N**. Require a definite version conflict. Fully reread the probe:
   A's hash and M must be unchanged. If the provider ignores the precondition,
   only the disposable probe is affected; CAS verification fails and canonical
   writes/sending remain disabled. Stop on another writer, unexpected version,
   or uncertain results, without compensating experiments on live state.
4. B also updates the probe at current M and verifies full readback. Record the
   successful cross-task CAS evidence for this connection/tool/runtime privately.
   Never turn the probe reference into the canonical reference or reuse it in production.

After this passes, a new installation may add `profile`, `installation`, and
`capabilities` copies to the local `state.json` envelope's `data`, then create
one separate canonical Library file via `create_library_file(file=...)`. Resume
an existing installation only with its existing canonical reference. Store it
as `installation.shared_state.library_file_id`. For canonical updates, use
that reference and its newly read provider version, never the probe's reference
or version. A changed connection/CAS route needs another new disposable probe test.

Users do not fill technical fields manually. The agent prepares the continuation
prompt and the user can open the next task in the supported UI. Do not invent
an API or parent worker when callable dispatch is unavailable.

Test content must also be available to subsequent tasks. Retain the approved
synthetic bundle's exact `raw` bytes in a separate private immutable `.eml`
Library file. Record its actual file/version reference and `o.bundle_contract(bundle)`
in canonical `data.onboarding_artifact`; the manifest does not duplicate image
bytes. The next task retrieves that version's actual bytes, restores them using
`o.restore_bundle(raw_bytes, saved_contract)`, verifies hashes/envelope/CIDs, and
creates a self-test bundle with a fresh test key. Do not assume old `.local`
files or an already sent provider draft can be reused.

## 4. Authorized Gmail draft → verification → send

Proceed only with authorization to test to the user's own verified address.
First read this test key's results/draft intent in canonical state. Do not start
a new call if a create result is uncertain or the send is sent/sending/uncertain.

1. Persist `data.draft_intents[test_key]` with account, content/recipient hashes,
   one operation ID, and `requested` status using CAS and readback.
2. Call Gmail `create_draft` with the prepared request. Record the returned
   **actual draft_id and message_id**. If ambiguous, resolve the actual draft
   with available `list_drafts` metadata; never substitute a message ID for a
   draft ID. Reconcile an uncertain creation with existing drafts before doing
   anything else; do not create another draft.
3. Read the same account's actual message via `read_email(format="raw")`.
   Verify its full base64url raw field with `o.verify_gmail_raw(test, returned_raw)`.
   This checks envelope, plain/HTML, and all CID hashes/bytes. Commit the successful
   roundtrip and actual draft/message identifiers using CAS.
4. Build `candidate = o.reserve_bundle(latest_snapshot, test, attempt_id)`;
   commit guarded replacement and use `verify_library_commit` to confirm
   **sending** state. Recheck real time, account, recipient, and explicit
   authorization immediately before sending. For `delivery.assert_send_allowed`,
   use only this account's self-test profile, `self_test=True`, and the `test/` key.
5. Call only `send_draft(link_id=verified_link, draft_id=actual_draft_id)`.
   Read the returned provider message and matching Sent evidence on the same
   account. Verify envelope/content/CIDs again and check Inbox rendering separately.
6. Commit `delivery.record_result` into `data.test_deliveries[test_key]` with
   CAS/readback. Never call `advance_once`/`record_publication` for tests;
   production history/counter stay unchanged. Timeout/cancellation remains uncertain;
   no blind retry.

Production uses the same helper/CAS route with a newly prepared bundle every
day. Check the real day/time and profile flags with `delivery.assert_send_allowed`.
Commit result + `advance_once` + `core.record_publication` in the same CAS.
For partial repair preserve existing delivery and eligible recipients;
`reserve_bundle` creates a new issue, never resets an existing one.

## 5. Scheduled test and completion

Do not create recurring publication before both the email test and two-task CAS
test pass. If the scheduler cannot target the correct Cloud project and actual
repo/shell access cannot be verified, stop at **manual use ready, automation
incomplete**. Asking the user for API fields or dispatching to another project
is not a solution.

With a supported target and explicit schedule authorization, generate a private
prompt with `o.scheduled_test_prompt`, including the actual canonical reference,
repo revision, and a new `test/` key. Operational prompts default to English;
pass `language="tr"` for Turkish instructions. This does not override the saved
newsletter content language. Supply `title`, this `prompt`, an actual future
`schedule` in the user's timezone, and appropriate `timing_mode` to the supported
automation tool. Use only target fields exposed by the current schema/UI; do
not invent an environment parameter. Schedule acceptance only establishes acceptance.

At the actual trigger, prove repo/runtime, same Library record/CAS, same Gmail
account, local time gate, and self-test result again. Wait for the real scheduled
time; `now/run_now` is not a scheduler trigger. Write results in the same private
record. `doctor --stage scheduled` requires actual current evidence; manually
setting flags or evidence fields does not establish setup.

Then, within the user's recurring-publication authorization, enable profile
flags and the approved time in the same canonical record. Convert the existing
test schedule to daily fresh research/prepare/CAS/draft/verify/send; do not create
a second sender/schedule. Match time/topic/recipient changes to the authorization
scope. Since enabled flags change the profile hash, rebind affected evidence
using actual reads and the active profile. Do not reuse a doctor result from
an older profile.
