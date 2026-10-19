# Set up in your own environment

**English** · [Türkçe](tr/setup.md)

Follow these steps with your agent using your existing ChatGPT/Codex environment
and connections. Setup grants no general permission to send email, create
schedules, or expand access. The [onboarding workflow](onboarding.md) provides
the user prompt and concrete Gmail/Library call sequence; the agent fills in
technical tool fields.

## 1. Verify capabilities

Check the actual runtime, repository path/revision, file and shell access,
Python, source-reading tools, image inspection, email tools, durable record,
and scheduler. Seeing a tool name is insufficient. Consider plan and workspace
limits in the [support matrix](support-matrix.md).

For an existing email connection, harmlessly read the selected account profile
and match it to the intended sender. Do not guess identities. Report reconnect,
sign-in, or approval dependencies. Do not create accounts, credentials, plugins,
or permission scopes as part of setup.

Describe gaps concretely: “Python and files are available; an email draft tool
is missing. HTML preparation is ready; sending is not configured.” Without a
scheduler, manual preparation remains available. This package does not require
`cloud_threads` or a particular Library tool.

## 2. Choose a profile and one durable record

Ask “Should your newsletter be in Turkish or English?” with the other newsletter
preferences, unless the user has already specified a language. Use `tr` for
Turkish and `en` for English. Chat language does not decide newsletter language.
The following commands show an English installation; use `--language tr` when
Turkish was selected.

```sh
bash scripts/setup.sh
python3 -m sincap init --language en
```

`init` creates only a new directory and never resets existing records. It writes
`.local/profile.json`, `capabilities.json`, `state.json`, and `installation.json`.
Installation references for the account, shared record, and scheduler start
empty. Independent profiles need separate directories and identities from the
start, for example:

```sh
python3 -m sincap init --language en --directory .local/reading --profile-id reading
```

Choose topics, source discovery URLs and priorities, and excluded source IDs.
Listing a source does not certify its readability or quality. Configure the
language as described below. Set target reading minutes and mandatory minimum
and maximum word counts. Reading time assumes approximately 200 words/minute;
the word check includes the opening, summaries, and commentary.

Article URLs must share the discovery URL's host by default. When a feed and
publication use different hosts, explicitly add the selected publication hosts
to that source's `article_hosts` list.

Choose sender, recipients, and signature. Use bare addresses; there is no Cc/Bcc.
This version uses one shared To envelope, so multiple recipients see one
another's addresses. Do not expand that scope without the user's choice. A
personal newsletter should use only the owner's verified address. Set an IANA
timezone and `HH:MM` delivery time. Keep delivery and schedule flags disabled
during setup; enabling JSON flags does not configure external services.

`state.json` must be the profile's single canonical record. Do not change the
profile ID after setup to create a fresh publication history. `LocalStore`
provides CAS on the same filesystem; separate worktrees and Cloud tasks do not
automatically share `.local`. Recurring delivery needs verified atomic access
to the same record across runs; see [adapters](adapters.md).

## Language selection

`init --language en` creates an English starter; `init --language tr` creates a
Turkish starter. English is the default for direct CLI use. Agent-led setup
uses the user's explicit language preference. Each preset includes matching
topic titles, source names, greeting, signature, and all five `labels` entries.
English examples are in `examples/`; Turkish examples are in `examples/tr/`.
Use a matching profile and synthetic issue:

```sh
python3 -m sincap prepare --demo --profile examples/profile.json --input examples/issue.json --at 2030-01-02T08:30:00Z --out .local/demo-en
python3 -m sincap prepare --demo --profile examples/tr/profile.json --input examples/tr/issue.json --at 2030-01-02T08:30:00Z --out .local/demo-tr
```

For an existing installation, edit the canonical profile; do not rerun `init`.
Update `language`, `greeting`, `signature`, `labels`, topic titles, and display
source names together. Preserve the profile ID, real sources, addresses,
timezone, preferences, and publication history. If automation already uses a
shared record, commit the change there using CAS and readback.

Each subsequent issue must match the profile's `language`. Have the agent write
the opening, titles, article kinds, summaries, commentary, closing question, and
image alternative text/credits in that language, retaining necessary proper
names and attribution. Python does not translate existing articles. A changed
profile hash requires renewed evidence for affected capability checks.

`scheduled_test_prompt(..., language="en")` produces English operational
instructions by default; `language="tr"` selects Turkish. This is separate
from the newsletter content language. Custom profiles and matching issue inputs
can use other content languages; built-in starters cover English and Turkish.
CLI commands, diagnostics, and JSON keys use English; do not translate schema keys.

## 3. Test sources and review HTML

Read a small sample from every enabled source, verifying the publication date
and enough visible body text. RSS/search snippets and HTTP success are insufficient.
Disable inaccessible sources when needed; do not report them as working. This
check does not send a production issue.

Start with the synthetic demo in the README. For real issues the agent reads
fresh sources daily and creates `.local/today.json` using `examples/issue.json`
as the schema. Include the real `issue_date`, `researched_at`, chosen language,
and `synthetic: false`. URL/DOI/event keys support deduplication; a meaningful
new development requires a new revision, real update timestamp, and explicit
`development_note`.

Use real story-matching images under the [editorial guide](editorial.md) and
[image contract](adapters.md#image-handoff). Keep image files and reviews in `.local`.

```sh
python3 -m sincap prepare --input .local/today.json --state .local/state.json --out .local/preview-today
```

Review `preview.html` at wide and narrow widths for overflow, story/image/comment
order, alt text, credits, and source links. `newsletter.html` and `newsletter.eml`
retain CID links; the browser preview uses local assets paths. All output is private.

## 4. Test to yourself with explicit authorization

After the user's explicit test instruction, restrict the recipient to their own
address verified by a harmless read on the existing connection. Use a separate
test state/directory and a `test/` issue key, preserving production history and
numbering. Show the concrete HTML/plain text and recipient before sending.

If supported, create a provider draft, read it back, and verify From/To/Subject,
plain/HTML, and every CID byte. Send using only the verified connection and real
draft ID. If the tool cannot accept local `.eml` files, map the verified MIME tree
to its supported fields. Preserve native approvals.

Record the provider result and matching Sent evidence; verify Inbox appearance
and rendering separately. Never resend on uncertainty. A requested three-image
test must render all three with correct bytes/CIDs. Offline CID tests do not
replace this real-client check.

## 5. Verify a real scheduled run

Do not enable recurring delivery before the email test passes. With an available
scheduler and user authorization, first schedule a real one-time self-test using
separate test state. A manual “run now” call is not equivalent evidence.

During the actual trigger, recheck runtime, repo revision, profile/hash, the same
canonical record, and the correct email account. Inspect where execution really
occurs; a plausible target label is insufficient. Stop before sending if file,
connection, or time gates fail.

Use the user's IANA timezone for both the schedule and real-time gate. Do not
send early. Use supported rescheduling or a new trigger at the intended time;
do not assume a continuously running VM. Local tasks need the computer and app
running. Exact-minute delivery is not guaranteed.

Schedule acceptance, execution in the correct runtime, provider acceptance, and
Inbox rendering are separate evidence. Do not change or reactivate automations
belonging to other projects.

## Evidence records

After real operations, update context and checks in `.local/capabilities.json`.
Evidence must match this runtime/repo revision and the current `profile_sha256`
reported by `doctor`. Each `verified` check needs an actual operation description
and timezone-aware ISO `checked_at`. Checks expire after 24 hours; repeat affected
checks when the profile, account, or environment changes. Keep identifiers and
detailed results private.

```sh
python3 -m sincap doctor --stage self-test
python3 -m sincap doctor --stage scheduled
```

`mail_draft_roundtrip` requires a draft created under explicit test authorization.
`scheduler_execution` requires an actually triggered scheduled test. Exit code
`0` means recorded evidence is complete and current, not that remote services
were independently certified. Keep flags disabled and report incomplete setup
until blockers are resolved.
