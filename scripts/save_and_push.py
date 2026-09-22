#!/usr/bin/env python3
"""리포트는 기본적으로 로컬에만 저장한다. --publish로 검토한 한 파일만 전송한다."""

import argparse
from datetime import datetime
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile


def git(root, *args):
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError("Git 작업 실패: " + args[0] + ". 로컬에서 상태를 확인하세요.")
    return result.stdout.strip()


def save_report(root, content, name=None):
    if name and not re.fullmatch(r"[\w-]{1,100}", name):
        raise ValueError("이름에는 문자, 숫자, 밑줄, 하이픈만 사용할 수 있습니다.")
    folder = root / "Research"
    if folder.is_symlink():
        raise ValueError("Research 폴더의 심볼릭 링크는 허용하지 않습니다.")
    folder.mkdir(exist_ok=True)
    stem = datetime.now().strftime("%Y-%m-%d") + "-" + (name or "research-report")
    for number in range(1, 10000):
        target = folder / (stem + (f"-{number}" if number > 1 else "") + ".md")
        try:
            with target.open("x", encoding="utf-8") as stream:
                stream.write(content)
            return target
        except FileExistsError:
            continue
    raise RuntimeError("사용 가능한 파일명을 찾지 못했습니다.")


def check_report(content):
    patterns = [
        r"(?i)(?:/Users/|/home/|[A-Z]:\\Users\\|/mnt/[a-z]/Users/)[^/\\\s`]+",
        r"(?i)[\w.+-]+@(?:gmail|naver|daum|hanmail|icloud)\.(?:com|net)",
        r"(?<!\d)01[016789][- .]?\d{3,4}[- .]?\d{4}(?!\d)",
    ]
    if any(re.search(pattern, content) for pattern in patterns):
        raise ValueError("개인 경로·이메일·전화번호 형식이 발견되어 전송을 중단했습니다.")
    executable = shutil.which("gitleaks")
    if not executable:
        raise RuntimeError("Gitleaks가 없어 전송을 중단했습니다. 공식 배포본을 설치하세요.")
    with tempfile.TemporaryDirectory(prefix="report-check-") as tmp:
        base = Path(tmp)
        scan = base / "input"
        scan.mkdir()
        (scan / "report.md").write_text(content, encoding="utf-8")
        config = base / "default.toml"
        config.write_text("[extend]\nuseDefault = true\n", encoding="utf-8")
        ignore = base / "empty-ignore"
        ignore.touch()
        result = subprocess.run([
            executable, "dir", str(scan), "--config", str(config),
            "--gitleaks-ignore-path", str(ignore), "--ignore-gitleaks-allow",
            "--redact=100", "--no-banner", "--no-color",
        ], capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError("비밀정보 검사 미통과: 파일은 보존하고 전송은 중단했습니다.")


def publish_report(root, report, message=None):
    relative = report.relative_to(root).as_posix()
    if report.is_symlink() or report.parent != root / "Research" or report.suffix != ".md":
        raise ValueError("Research 폴더의 일반 Markdown 파일 한 개만 전송할 수 있습니다.")
    if Path(git(root, "rev-parse", "--show-toplevel")).resolve() != root:
        raise ValueError("볼트 경로는 저장소 최상위 폴더여야 합니다.")
    if git(root, "diff", "--cached", "--name-only"):
        raise RuntimeError("이미 추가된 다른 변경이 있어 전송을 중단했습니다.")
    branch = git(root, "symbolic-ref", "--short", "HEAD")
    if git(root, "config", f"branch.{branch}.remote") != "origin":
        raise RuntimeError("origin 원격 추적 브랜치를 먼저 설정하세요.")
    merge = git(root, "config", f"branch.{branch}.merge")
    if merge != f"refs/heads/{branch}":
        raise RuntimeError("로컬과 원격 브랜치 이름이 달라 전송을 중단했습니다.")
    before = git(root, "rev-parse", "HEAD")
    remote = git(root, "ls-remote", "origin", merge).split()
    if not remote or remote[0] != before:
        raise RuntimeError("기존 미전송 커밋 또는 원격 변경이 있습니다. 먼저 동기화하세요.")
    for field in ("GIT_AUTHOR_IDENT", "GIT_COMMITTER_IDENT"):
        if not re.search(r"<[^<>]+@users\.noreply\.github\.com>", git(root, "var", field)):
            raise RuntimeError("작성자와 커미터 모두 GitHub noreply 이메일을 사용해야 합니다.")
    content = report.read_text(encoding="utf-8")
    check_report(content)
    if message:
        check_report(message)
    if report.read_text(encoding="utf-8") != content:
        raise RuntimeError("검사 중 파일이 바뀌어 전송을 중단했습니다.")
    git(root, "add", "--", relative)
    git(root, "commit", "--only", "-m", message or "Add reviewed research report", "--", relative)
    after = git(root, "rev-parse", "HEAD")
    changed = git(root, "diff-tree", "--no-commit-id", "--name-only", "-z", "-r", after).strip("\0").split("\0")
    if git(root, "rev-parse", "HEAD^") != before or changed != [relative]:
        raise RuntimeError("커밋 범위가 예상과 달라 전송을 중단했습니다.")
    if git(root, "show", f"{after}:{relative}") != content.strip():
        raise RuntimeError("커밋 내용이 검사 결과와 달라 전송을 중단했습니다.")
    identities = git(root, "show", "-s", "--format=%ae%n%ce", after).splitlines()
    if not all(email.endswith("@users.noreply.github.com") for email in identities):
        raise RuntimeError("커밋 이메일 확인에 실패해 전송을 중단했습니다.")
    check_report(git(root, "show", "-s", "--format=%B", after))
    git(root, "-c", "push.followTags=false", "push", "origin", f"{after}:{merge}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault-path", required=True)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--content")
    source.add_argument("--file")
    source.add_argument("--report", help="이미 저장하고 검토한 Research/*.md 파일")
    parser.add_argument("--name")
    parser.add_argument("--commit-msg")
    parser.add_argument("--publish", action="store_true", help="내용 검토 후 지정한 보고서만 검사·전송")
    parser.add_argument("--push-only", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.push_only:
        parser.error("전체 변경 전송은 제거됐습니다. --report와 --publish를 사용하세요.")
    try:
        root = Path(args.vault_path).expanduser().resolve(strict=True)
        if args.report:
            report = root / args.report
            if report.is_symlink() or (root / "Research").is_symlink():
                raise ValueError("심볼릭 링크는 전송할 수 없습니다.")
            report = report.resolve(strict=True)
            if report.parent != root / "Research" or report.suffix != ".md":
                raise ValueError("Research 폴더의 Markdown 파일을 지정하세요.")
        else:
            content = args.content
            if args.file:
                content = Path(args.file).expanduser().read_text(encoding="utf-8")
            if content is None and not sys.stdin.isatty():
                content = sys.stdin.read()
            if not content or not content.strip():
                raise ValueError("저장할 내용이 없습니다.")
            report = save_report(root, content, args.name)
        print("로컬 파일: " + report.relative_to(root).as_posix())
        if args.publish:
            publish_report(root, report, args.commit_msg)
            print("검토한 보고서 한 개를 전송했습니다.")
        else:
            print("로컬에만 저장했습니다. 내용 검토 후 --report와 --publish로 전송하세요.")
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
