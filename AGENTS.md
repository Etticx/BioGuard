# BioGuard project instructions

These instructions apply throughout BioGuard. Follow applicable nested instructions, including `mobile/AGENTS.md` for mobile work.

## Agent roles

Project role profiles live in `.codex/agents/`: `orchestrator`, `coder`, `reviewer`, and `tester`. They inherit the session model and permissions. The main conversation normally acts as orchestrator; do not recursively spawn another orchestrator.

For substantial implementation work, delegate bounded tasks to the relevant roles. Give one coder ownership of affected files, ask a reviewer for an independent read-only review, and ask a tester for focused verification using isolated fixtures. Coordinate file ownership before concurrent work. Tiny changes do not require every role. Agents report to the parent and do not subdelegate.

- Orchestrator: scope work, preserve context, resolve findings, and present verified outcomes.
- Coder: implement the assigned behavior and run appropriate focused checks.
- Reviewer: inspect changes read-only and report concrete regressions with paths and lines.
- Tester: verify using disposable data and report results and coverage limits.

## Preserve project and user work

- Inspect current changes first. Preserve user and Codex CLI edits; do not overwrite, discard, reset, commit, or change branches unless asked.
- Do not expose real credentials, reports, photos, or private records in output, fixtures, screenshots, or source control.
- Do not change live passwords, databases, or running servers unless authorized by the current task.
- Keep private beta data separate from original data. Use temporary databases and clearly synthetic photos and records for tests.
- Keep the current model unless the user requests a model change. Never treat a model prediction as reviewed ground truth.
- Preserve officer confirmation of identification and invasive status before removal is assigned.
- The project is a private beta. Do not publish, deploy externally, submit to stores, or change accounts or credentials without authorization.

## Verification and reporting

Run checks appropriate to the change and follow nested requirements. Do not claim physical phone, camera, fresh-field, signed-build, or deployment testing succeeded without direct evidence. Clearly separate automated results from work awaiting a device, reviewed field examples, hosting, or an account. Keep user-facing explanations concise and nontechnical unless detail is useful.
