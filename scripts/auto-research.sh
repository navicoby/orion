#!/bin/bash
cd ~/Documents/orion
claude -p "SKILL.md를 읽고 이번 주 조경BIM, 자연자본 자료를 수집해서 Research 폴더에 마크다운 리포트로 저장하고 git add, commit, push까지 실행해줘. 중간에 질문하지 말고 바로 진행해." --allowedTools "WebSearch,Write,Bash"
