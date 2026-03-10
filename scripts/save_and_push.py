#!/usr/bin/env python3
"""
save_and_push.py
옵시디언 볼트에 마크다운 리포트를 저장하고 GitHub에 자동 push하는 스크립트.

사용법:
    python3 save_and_push.py --vault-path ~/Documents/orion --content "마크다운내용"
    python3 save_and_push.py --vault-path ~/Documents/orion --file input.md
    python3 save_and_push.py --vault-path ~/Documents/orion --content "내용" --name "custom-report"
"""

import argparse
import os
import subprocess
import sys
from datetime import datetime


def ensure_research_folder(vault_path: str) -> str:
    """Research 폴더가 없으면 생성"""
    research_dir = os.path.join(vault_path, "Research")
    os.makedirs(research_dir, exist_ok=True)
    return research_dir


def generate_filename(custom_name: str = None) -> str:
    """날짜 기반 파일명 생성"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    if custom_name:
        return f"{date_str}-{custom_name}.md"
    return f"{date_str}-research-report.md"


def save_report(research_dir: str, filename: str, content: str) -> str:
    """리포트를 Research 폴더에 저장"""
    filepath = os.path.join(research_dir, filename)
    
    # 같은 이름 파일이 있으면 번호 추가
    if os.path.exists(filepath):
        base, ext = os.path.splitext(filepath)
        counter = 2
        while os.path.exists(f"{base}-{counter}{ext}"):
            counter += 1
        filepath = f"{base}-{counter}{ext}"
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    
    return filepath


def git_push(vault_path: str, commit_message: str = None) -> bool:
    """Git add, commit, push 실행"""
    if not commit_message:
        date_str = datetime.now().strftime("%Y-%m-%d")
        commit_message = f"📋 Research report: {date_str}"
    
    try:
        os.chdir(vault_path)
        
        # git add
        result = subprocess.run(
            ["git", "add", "."],
            capture_output=True, text=True, cwd=vault_path
        )
        if result.returncode != 0:
            print(f"❌ git add 실패: {result.stderr}")
            return False
        
        # git commit
        result = subprocess.run(
            ["git", "commit", "-m", commit_message],
            capture_output=True, text=True, cwd=vault_path
        )
        if result.returncode != 0:
            if "nothing to commit" in result.stdout:
                print("ℹ️ 변경사항 없음, 커밋 스킵")
                return True
            print(f"❌ git commit 실패: {result.stderr}")
            return False
        
        # git push
        result = subprocess.run(
            ["git", "push"],
            capture_output=True, text=True, cwd=vault_path
        )
        if result.returncode != 0:
            print(f"❌ git push 실패: {result.stderr}")
            return False
        
        print("✅ GitHub push 완료!")
        return True
        
    except Exception as e:
        print(f"❌ Git 오류: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="옵시디언 볼트에 리포트 저장 + GitHub push")
    parser.add_argument("--vault-path", required=True, help="옵시디언 볼트 경로 (예: ~/Documents/orion)")
    parser.add_argument("--content", help="마크다운 내용 (직접 입력)")
    parser.add_argument("--file", help="마크다운 파일 경로 (파일에서 읽기)")
    parser.add_argument("--name", help="커스텀 파일명 (날짜 뒤에 붙음)")
    parser.add_argument("--commit-msg", help="커스텀 커밋 메시지")
    parser.add_argument("--push-only", action="store_true", help="저장 없이 push만 실행")
    
    args = parser.parse_args()
    vault_path = os.path.expanduser(args.vault_path)
    
    # 볼트 경로 확인
    if not os.path.isdir(vault_path):
        print(f"❌ 볼트 경로가 존재하지 않음: {vault_path}")
        sys.exit(1)
    
    # push만 실행
    if args.push_only:
        success = git_push(vault_path, args.commit_msg)
        sys.exit(0 if success else 1)
    
    # 내용 가져오기
    content = None
    if args.content:
        content = args.content
    elif args.file:
        file_path = os.path.expanduser(args.file)
        if not os.path.isfile(file_path):
            print(f"❌ 파일이 존재하지 않음: {file_path}")
            sys.exit(1)
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        # stdin에서 읽기
        if not sys.stdin.isatty():
            content = sys.stdin.read()
        else:
            print("❌ --content 또는 --file 옵션이 필요합니다")
            sys.exit(1)
    
    # 저장
    research_dir = ensure_research_folder(vault_path)
    filename = generate_filename(args.name)
    filepath = save_report(research_dir, filename, content)
    print(f"📁 저장 완료: {filepath}")
    
    # Git push
    success = git_push(vault_path, args.commit_msg)
    
    if success:
        print(f"\n✅ 전체 완료!")
        print(f"   📁 파일: {filepath}")
        print(f"   🔗 GitHub에 push 완료")
    else:
        print(f"\n⚠️ 파일은 저장됨, GitHub push 실패")
        print(f"   📁 파일: {filepath}")
        print(f"   수동으로 push 필요: cd {vault_path} && git add . && git commit -m 'report' && git push")


if __name__ == "__main__":
    main()
