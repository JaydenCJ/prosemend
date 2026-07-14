---
title: Release notes workflow
status: draft
---

# How we ship release notes

Every release, one writer drafts the notes and a reviewer polishes them before the tag is cut, so nothing half-baked reaches the changelog.

Keep sentences short. Name the feature, the fix, and the person to thank.

| step   | owner  |
|--------|--------|
| draft  | writer |
| review | editor |

```sh
git tag -a v1.3.0 -m "release"
git push origin v1.3.0
```
