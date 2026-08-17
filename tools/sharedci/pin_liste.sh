#!/usr/bin/env bash
while read -r repo path; do
  [ -z "$repo" ] && continue
  ref=$(gh api "repos/$repo/contents/$path" -q .content 2>/dev/null | base64 -d 2>/dev/null \
        | grep -o '_ci-python\.yml@[A-Za-z0-9._/-]*' | sort -u | tr '\n' ' ')
  [ -n "$ref" ] && echo "$repo|$path|$ref"
done
