---
name: voice-transcription
description: Fully local Voice Memos/audio transcription and routing through the official OpenWhispr desktop app and CLI. Use when the user drops an audio file to transcribe, says new voice memos or transcriptions are available, or asks about OpenWhispr notes. Never sends audio or transcripts to any cloud/remote service.
---

# Voice Transcription

Local-only pipeline: the official `@openwhispr/cli` plus the running OpenWhispr desktop
app, wrapped by the installed `voice-transcription` executable on PATH. The wrapper always calls
`openwhispr --local transcribe`: an authenticated `127.0.0.1` bridge receives only an
absolute path, and the desktop app reads the file and runs its downloaded local model.
`--remote` is never used, there is no auto-selection or cloud fallback, and an unavailable
CLI/bridge/local model fails explicitly. The default model ID is `large`, which OpenWhispr
maps to its non-quantized `ggml-large-v3.bin` model. Audio dedupe is a content hash of
*decoded* audio, computed for every file regardless of filename or metadata changes.

The helper retains its private ledger and full transcript/provenance artifacts under
`~/.local/state/voice-transcription/`. Model downloads and their integrity are owned by
the official desktop app; this helper never downloads a model or substitutes a model
silently.

**Always call the helper for the mechanics below.** Don't hand-roll ffmpeg/whisper
invocations, re-implement the content-hash ledger, or read `~/.local/state/voice-transcription/`
internals directly -- `voice-transcription --help` and its subcommands are the contract.

Shared use does not merge work and personal task context. Process only the sources
authorized for the current request; route each item within its owning context.
The helper and existing local state are dependencies, not bundled skill assets.

## Commands

- `voice-transcription transcribe <path> [--language LANG] [--model MODEL_ID] [--force]`
  Transcribe one explicit local audio file (mp3/m4a/wav/aac/flac/ogg/opus/webm/aiff/qta).
  Returns JSON: status, content_hash, artifact_dir, transcript_txt_path,
  transcript_json_path, duration_seconds, provider/model metadata, and a deterministic
  `routing_hint` (keyword/length heuristic -- **not** a summary; see Routing below).
- `voice-transcription scan [directory]` -- discover audio recursively and report ledger
  status (`new` / `already_transcribed` / `previously_failed_will_retry` / `decode_failed`)
  without transcribing. Each candidate that reaches decoding reports `duration_seconds`
  (a number when decoded, `null` on decode failure); source-unreadable entries have no
  duration. Defaults to the Voice Memos sync container at
  `~/Library/Group Containers/group.com.apple.VoiceMemos.shared/Recordings`;
  its internal edit-composition fragments are excluded, leaving only user-visible
  recordings. Native Voice Memos recordings may be `.m4a` or `.qta` (QuickTime audio);
  both are supported. Do not conclude that a visible memo is absent merely because a
  scan or ad-hoc expectation considers only `.m4a` files.
- `voice-transcription batch [directory]` -- scan, then transcribe everything eligible
  (new + previously-failed + decode-failed, so fixed files retry). Defaults to
  the local Voice Memos sync container above. One worker by default (large-v3 is
  memory-heavy); don't raise `--workers` unless you've verified headroom.
- `voice-transcription status` -- ledger counts, installed official CLI presence, selected
  default model ID, and local desktop bridge availability.
- `voice-transcription openwhispr status` / `openwhispr notes [--all]` -- local-only
  discovery of OpenWhispr desktop app notes (metadata only: id, title, type, source file,
  updated_at). Always forces the local backend. Returns `available: false` if the desktop
  app isn't running -- that's an expected local-only state, not an error, and never
  triggers a remote/cloud fallback. The OpenWhispr CLI has no file-transcription support;
  it's for note discovery only.

Never pass `--remote` or otherwise let OpenWhispr use its cloud backend.

## Handling "new voice memos/transcriptions are available"

Process the batch inline or delegate when the active platform supports it and
delegation is authorized. The worker must:

1. Run `voice-transcription batch` (default directory, or the directory the user named)
   and `voice-transcription openwhispr notes` for local OpenWhispr discovery.
2. For each successful result, **read the transcript file itself** (`transcript_txt_path`)
   -- the helper deliberately does not fabricate a semantic summary -- and write a very
   short (1-3 sentence) human-readable routing summary per item.
3. For every actionable memo, separately extract the complete ordered directives,
   prerequisites, validation requirements, explicit sequencing, and "do not proceed
   until" gates. Preserve these operational details even when the routing summary is
   intentionally brief; the summary is not a substitute for an execution contract.
4. Apply the routing policy below and report back a structured list, one entry per item,
   with: source name/path, content hash, transcript path, detected language, the brief
   summary, extracted ordered directives/gates when actionable, and the chosen route
   (with a one-line reason).
5. Surface failures (`status: failed`) with their diagnostic error rather than silently
   dropping them; they'll retry automatically on the next `batch` run.

The parent coordinator must not perform side effects from the brief routing summary
alone. Before launching agents, creating work, or changing project state, it must use
the extracted directives/gates as the authoritative handoff and confirm that every
prerequisite is satisfied. When extraction is uncertain, route the memo for clarification
instead of guessing or collapsing a multi-phase request into its final outcome.

## Routing policy

Raw transcripts and their provenance stay local (under
`~/.local/state/voice-transcription/artifacts/`) and are never written into any
project's `docs/` or other repo-tracked files by this skill/helper itself -- routing
means handing off a short summary and pointers, not moving content, and the receiving
project agent owns whatever it decides to do with it next.

- **Action items** (explicit asks, reminders, follow-ups) -> hand off to the relevant
  project's task/todo management (not this skill, and not `docs/`).
- **Durable facts / meeting-style content** (decisions, notes, context worth keeping) ->
  hand off to the target project's own agent, with the brief summary, source path, and
  transcript path -- that project agent decides how/whether to incorporate it into its
  own living docs or journal. This skill never edits a project's `docs/` directly and
  never stores raw transcripts there.
- **Ambiguous or cross-cutting content** -> hand off to the current coordinating
  agent for a judgment call, rather than guessing a project.

A single memo may need to be split across multiple routes (e.g. an action item plus
unrelated notes) -- don't force one label per file.

## Privacy and error handling

- The default Apple Voice Memos container is protected by macOS privacy controls. To
  ingest synced recordings without manually exporting them, grant **Full Disk Access**
  to the terminal application that launched the active agent, then restart that terminal/CLI.
  The helper fails explicitly if this permission is absent; do not bypass TCC or automate
  the Voice Memos GUI. Voice Memos provides no supported automation interface.
- Treat top-level `.qta` files in the native recording container as ordinary synced Voice
  Memos. They are QuickTime audio recordings, not iCloud placeholders or edit fragments.
  Continue excluding only paths under a `<recording>.composition` directory, which are
  internal edit fragments rather than separately user-visible memos.
- Don't read, list, or otherwise process recordings outside of calling the helper's
  `scan`/`batch` commands on the configured source directory.
- Don't print full transcripts into the main conversation by default; reference the
  `transcript_txt_path` and quote only what's needed for routing/summary context.
- OpenWhispr note content must never be written into a project's `docs/` or other
  repo-tracked files -- if anything beyond metadata needs caching, it belongs only under
  `~/.local/state/voice-transcription/`.
- `failed` and `decode_failed` statuses persist a diagnostic error in the ledger and are
  retried automatically on the next `batch`/`transcribe` call for that path -- don't
  manually retry-loop or suppress them.
- If the official CLI or local desktop bridge is unavailable, or the helper exits non-zero
  for reasons other than a single file's decode failure, stop and surface the error. Do
  not attempt an alternate cloud, standalone-inference, or GUI-automation path.

## Alternatives considered (context, not exhaustive)

- The desktop also supports downloaded Parakeet, Nemotron, Cohere, and Orukeet local
  models. Do not change the default from `large` without an explicit user request and an
  appropriate local quality evaluation. A user may pass an already-downloaded model ID
  with `--model`; the desktop rejects unavailable models rather than downloading one.
