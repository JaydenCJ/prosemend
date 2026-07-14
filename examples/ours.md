---
title: Release notes workflow
status: in-review
---

# How we ship release notes

Every release, one writer outlines the notes and a reviewer polishes them before the tag is cut, so nothing vague reaches the changelog.

Keep sentences short. Name the feature, the fix, and the person to thank.

| step   | owner    |
|--------|----------|
| draft  | writer   |
| review | reviewer |

```sh
git tag -a v1.2.0 -m "release"
git push origin v1.2.0
```
