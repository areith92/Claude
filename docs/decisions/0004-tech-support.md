# 0004: Tech Support
Decision: failing health checks raise incidents; a Claude Tech Support agent proposes a fix as exact file changes; scripts test it in a scratch copy, apply it on a branch,
and verify it in the working tree; the owner pushes and merges; the fix is verified again after the pull.
Safety: the model's output is data, never commands. Only fixed file operations are applied, to allowed folders. Owner-only files (governance, models, workflows, permissions,
safety scripts) need --include-owner-files. No push, no merge, no live actions. Attempts are limited and every call is inside the AI spend caps.
"Live environment" means your real working tree. There is no customer-facing system to touch in Phase 1.
