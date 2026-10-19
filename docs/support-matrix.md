# Support and verification limits

**English** · [Türkçe](tr/support-matrix.md)

Review date: **19 October 2026**. A documented capability does not establish an
end-to-end test in this repository or the user's account. Product surface, plan,
workspace, region, and connection permissions may differ.

| Layer/environment | Status in this starter | Verification needed |
| --- | --- | --- |
| Python + standard library | Offline tests cover profiles, selection, HTML/plain/MIME, local CAS, and recipient protection. Gmail MIME/raw and Library CAS argument/readback helpers have synthetic tests. | Shell/file access and Python 3.9+ in the user's runtime; helper tests do not establish provider success. |
| English/Turkish starters | Matching profiles, synthetic issues, labels, HTML/plain/MIME, and CLI initialization have offline tests for both languages. | Confirm the user's content language during onboarding and review real agent-written content in that language. Python does not translate it. |
| PNG/JPEG + existing Pillow | Three CID byte-preservation tests use temporary synthetic PNGs when the decoder is available. | Real decoding, pixel/event/rights review, and a real email client. Skipped tests do not verify support. |
| ChatGPT/Codex Cloud | Shell/Python, offline core, and Pillow tests passed in a clean repository task. Official docs describe a separate workspace per task; this starter has no live email/scheduler test. | Actual task startup with the user's repo and shared atomic state access. [Cloud environments](https://learn.chatgpt.com/docs/environments/cloud-environments). |
| ChatGPT web tasks | Documentation describes tools/files available to current context; it does not promise a local directory persists across tasks. | Verify files, tools, and durable state during a real scheduled run. [Scheduled tasks](https://learn.chatgpt.com/docs/automations). |
| Desktop project tasks | Documented local project/worktree scheduling requires the computer and app running; no desktop scheduler test was performed here. | Same private state file and actual trigger test. [Scheduled tasks](https://learn.chatgpt.com/docs/automations). |
| Codex CLI / IDE | Core runs with file/shell access. Documentation does not provide the Scheduled management UI on these surfaces. | An existing supported scheduling surface; the repo does not install cron/services. [Scheduled tasks](https://learn.chatgpt.com/docs/automations). |
| Email connection | Gmail structured MIME/raw/send_draft schemas were inspected; agent workflow and offline helpers exist. No live draft/send test in this starter. | Existing account profile read, MIME draft roundtrip, authorized self-test. [Onboarding](onboarding.md), [Connected apps](https://help.openai.com/en/articles/11487775-connected-apps-in-chatgpt). |
| Library shared state | Create/read/expected_current_version schemas were inspected; candidate, guarded replace, and complete readback helpers exist. | Test a separate disposable synthetic probe across two actual Cloud tasks first. A stale write must conflict and leave content unchanged. Do not test CAS on a canonical ledger. Offline simulation is not a live CAS test. |
| Cloud scheduler target | A create schema exists; the inspected tool exposed no Cloud-environment target/dispatch field. | Do not create a schedule without a real execution route to the correct project; record acceptance is insufficient. |
| Library / cloud_threads / custom dispatch | Not core dependencies; no universal support claim. | Actual tool access and account/runtime tests before claiming handoff or dispatch support. |
| End-to-end daily delivery | Not yet verified for this starter. | Complete the user's own test email, correct state access, and a real scheduled test. |

Connections vary between accounts and plans; preserve any required action
approvals. [Connected apps](https://help.openai.com/en/articles/11487775-connected-apps-in-chatgpt).
Free source code does not change AI usage limits or hosting entitlements. Plan,
credit, and fee terms still apply; a separate API is not required by this starter.
[Codex plans and usage](https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan).

This table is not a live support certificate for an account. Record actual
installation results privately in `.local/capabilities.json`; do not add runtime
outputs or private identifiers to public source files.
