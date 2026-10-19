# 🐿️ Sincap Post

**English** · [Türkçe](README.tr.md)

A small starter kit for a personal newsletter prepared with your own
ChatGPT/Codex agent. Choose your topics, sources, language, length, recipients,
delivery time, and signature, using an email connection you already have.

The Python core validates profiles, selects fresh articles, removes duplicates,
renders HTML and plain text, packages inline CID images, and tracks delivery
state. Your agent researches sources and uses the email and scheduling tools
actually available in your environment. Gmail MIME and Library CAS helpers
prepare and verify tool inputs; the agent makes external calls. Email and
scheduled delivery require separate verification in your own account.

## Set up with your agent

Open this repository in your own ChatGPT/Codex environment and say:

> Set up Sincap Post for me. Follow AGENTS.md and docs/onboarding.md.
> Check the available tools first and show me the synthetic preview. Ask me only
> for my newsletter preferences and any required action permissions; discover
> and fill in the technical fields yourself.

During setup, your agent asks **“Should your newsletter be in Turkish or
English?”**, unless you already specified a language. This choice controls the
newsletter content and profile text, independently of the language of your chat.

The [onboarding guide](docs/onboarding.md) covers Gmail draft → raw verification
→ send, a versioned shared record, and a real scheduled test. The agent discovers
account and file identifiers and keeps them in private installation records.

## Try the offline preview

Python 3.9+ and its standard library are enough for text preparation. No package
installation or model API key is required. Run from the repository directory:

```sh
bash scripts/setup.sh
python3 -m sincap init --language en
python3 -m sincap prepare --demo --input examples/issue.json --at 2030-01-02T08:30:00Z --out .local/demo
```

Open `.local/demo/preview.html` in a browser. The publications and stories are
fictional, addresses use the reserved `example.invalid` domain, and the demo
includes no photographs. Clock overrides work only with `--demo`. Preparation
creates local HTML, plain text, MIME, and a report; it does not create a provider
draft, send email, or advance publication history. Existing output directories
are never overwritten.

Image validation requires an existing Pillow decoder for real PNG/JPEG bytes.
The setup script does not install it. Three CID tests create temporary synthetic
PNGs; skipped image tests mean image support has not been verified.

## Choose a language

English is the default CLI starter language. Agent-led setup uses your answer to
the language question. Both presets include matching topic and source names,
greeting, signature, and newsletter labels:

| Starter | Initialize | Synthetic issue |
| --- | --- | --- |
| English | `python3 -m sincap init --language en` | `examples/issue.json` |
| Turkish | `python3 -m sincap init --language tr` | `examples/tr/issue.json` |

For a separate Turkish demo alongside an existing installation:

```sh
python3 -m sincap init --language tr --directory .local/turkish --profile-id turkish-demo
python3 -m sincap prepare --demo --profile .local/turkish/profile.json --input examples/tr/issue.json --at 2030-01-02T08:30:00Z --out .local/turkish/demo
```

The profile and issue must have the same `language`. Your agent writes stories
in that language; Python does not translate existing content. Other content
languages can use a custom profile and matching input. Read
[language configuration](docs/setup.md#language-selection) before changing an
existing profile. CLI commands, JSON keys, and diagnostics use English.

## Make it your own

1. Follow the [setup guide](docs/setup.md), beginning with harmless capability
   and connection reads.
2. Replace sample sources and addresses in `.local/profile.json` with your
   preferences. Keep `delivery.enabled` and `schedule.enabled` set to `false`
   during initial setup.
3. Have your agent read current sources and record that day's articles and image
   decisions privately. Follow the [editorial rules](docs/editorial.md) and
   [adapter contract](docs/adapters.md).
4. Review the HTML preview. Within your explicit authorization, test only to your
   own verified address. Check matching Sent evidence and recipient rendering
   separately.
5. Verify a real scheduled test in the correct runtime, using the same durable
   record and email account, before treating recurring delivery as ready.

Prepare real content against the existing canonical record:

```sh
python3 -m sincap prepare --profile .local/profile.json --input .local/today.json --state .local/state.json --out .local/preview-today
python3 -m sincap doctor --stage self-test
```

The agent creates `today.json` using the example schema, actual date, fresh
research, chosen language, and `synthetic: false`. `doctor` checks local
conditions and agent-recorded evidence. It makes no connection calls and returns
exit code `2` for missing or stale evidence. Manually marking a check as
`verified` does not replace a real test.

## Support and cost

The [support matrix](docs/support-matrix.md) distinguishes offline tests from
documented product capabilities and integrations still requiring live tests.
Gmail, Library, `cloud_threads`, and schedulers are not available in every
account. Separate Cloud workspaces do not automatically share a publication
record. Local scheduled tasks require the computer and app to remain running.

The source is MIT licensed. AI usage and hosting remain subject to your plan's
limits and applicable fees. See [Codex usage and plan information](https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan).
This starter does not require a new account, API key, or paid service.

## Contributing and privacy

`MANIFEST.txt` explicitly lists distributable source files. `.local/` is for
private runtime data; `.gitignore` alone is not a security boundary. Keep real
addresses, connection identifiers, state ledgers, email, MIME, images, and logs
out of Git.

```sh
bash scripts/setup.sh
python3 scripts/preflight.py --staged
python3 scripts/preflight.py --manifest
```

The setup script runs checks without network or email access. Review the staged
diff together with the index scan before committing. Automated scanning does
not replace manual privacy review. Agent responsibilities are in
[AGENTS.md](AGENTS.md).
