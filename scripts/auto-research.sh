#!/bin/bash
set -euo pipefail
vault_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd -- "$vault_dir"
# 예약 수집은 로컬 저장만 한다. 셸과 외부 서비스 도구로 전송하지 않는다.
claude -p "SKILL.md를 읽고 이번 주 조경BIM과 자연자본 자료를 수집해 Research 폴더의 새 마크다운 리포트에만 저장해줘. 기존 파일과 설정을 수정하지 말고, 커밋·push·외부 업로드를 하지 마." \
  --tools "Read,WebSearch,WebFetch,Write" \
  --allowedTools "Read,WebSearch,WebFetch,Write" \
  --disallowedTools "Bash" "mcp__*"
