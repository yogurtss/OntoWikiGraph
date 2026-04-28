---
name: doc-sync-and-push-main
description: Use this skill when working in OntoWikiGraph and the goal is to publish current changes to main with documentation synchronized first. Before committing, inspect all local changes and update documentation to match them: algorithm, pipeline, schema, storage, extraction, or other implementation-detail changes go to docs/; frontend changes and user-visible new features go to the root README.md. After documentation is updated, commit the relevant changes and push the current branch state to origin/main.
---

# Doc Sync And Push Main

## Overview

This skill standardizes the release flow for this repository: synchronize documentation with the actual code changes first, then commit and push to `main`.

## Workflow

1. Inspect the current worktree with `git status --short`, `git diff --stat`, and targeted diffs for changed files.
2. Classify the changes before editing docs.

Use these documentation rules:

- If the changes affect algorithms, data flow, pipeline behavior, extractors, ontology handling, storage behavior, validation, or other implementation details, update the relevant files under `docs/`.
- If the changes affect frontend behavior, usage flow, setup instructions, or introduce a user-visible feature, update the root `README.md`.
- If both apply, update both `docs/` and `README.md`.

3. Keep documentation edits specific to the actual behavior change. Do not add speculative documentation.
4. Re-check the worktree to confirm the intended code and doc changes are included.
5. Commit the synchronized changes with a concise message.
6. Push to `origin/main`.

## Repository Guidance

- Prefer existing documentation locations before creating new files.
- For algorithm or pipeline updates, first inspect `docs/kg_workbench/` and `docs/README.md`.
- For frontend and top-level usage updates, prefer the root `README.md`.
- Exclude obvious local-only artifacts from commits unless the user explicitly asks for them.

## Commit And Push Rules

- Do not push code changes without first checking whether the docs need updates.
- If there are no meaningful documentation changes required, say so briefly in the final response and proceed with commit/push.
- Keep unrelated untracked local artifacts out of the commit.
- Push using `git push origin main` after the commit is created.

## Typical Invocation

Use this skill when the user asks for any variation of:

- "把当前改动整理文档后推到 main"
- "先更新 README/docs，再 push"
- "同步文档并发布这次改动"
