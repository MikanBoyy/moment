from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
ENTRY_POINT = SRC_DIR / "main.pine"
OUTPUT_FILE = ROOT_DIR / "dist" / "moment.pine"
INCLUDE_PATTERN = re.compile(r'^\s*//#include\s+"([^"\\]+)"\s*$', re.MULTILINE)
VERSION_PRAGMA_PATTERN = re.compile(r'^\s*//@version=6\s*\n?', re.MULTILINE)


# `file_path` を起点に `//#include "..."` を再帰的に展開し、単一の Pine Script
# ソースを返す。include の相対パスは常に `src/` 基準で解決するため、各モジュールが
# 置かれたディレクトリには依存しない。`include_stack` は循環参照の検出に使う。
#
# @param file_path 読み込む `.pine` ファイルの絶対または相対パス。
# @param include_stack 入口から現在のファイルまでの解決済みファイル列。
# @returns include 行を実ファイルの内容へ置換した Pine Script ソース。入口以外の
#     モジュールにある `//@version=6` は、結合後の version pragma を一意に保つため除去する。
# @throws ValueError 循環 include、`src/` 外への参照、BOM、または UTF-8 で読めない入力時。
# @throws FileNotFoundError 指定された include ファイルが存在しない場合。
def resolve_includes(file_path: Path, include_stack: tuple[Path, ...] = ()) -> str:
    resolved_path = file_path.resolve()
    if resolved_path in include_stack:
        cycle = " -> ".join(str(path.relative_to(SRC_DIR)) for path in (*include_stack, resolved_path))
        raise ValueError(f"循環 include を検出しました: {cycle}")

    try:
        source = resolved_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(f"UTF-8 で読み込めません: {resolved_path}") from error

    if source.startswith("\ufeff"):
        raise ValueError(f"UTF-8 BOM が含まれています: {resolved_path}")

    # 正規表現に一致した1つの include を実ファイルの内容へ置換する。
    # 結合後の Pine Script には名前空間がないため、ここでは内容の変換は行わず、
    # パスの安全性と存在だけを検証して再帰展開へ委譲する。
    #
    # @param match `INCLUDE_PATTERN` に一致した include 行の正規表現マッチ。
    # @returns include 先を再帰的に展開したソース文字列。
    # @throws ValueError `src/` 外を指す include が指定された場合。
    # @throws FileNotFoundError include 先のファイルが存在しない場合。
    def replace_include(match: re.Match[str]) -> str:
        include_path = (SRC_DIR / match.group(1)).resolve()
        try:
            include_path.relative_to(SRC_DIR.resolve())
        except ValueError as error:
            raise ValueError(f"src 外の include は許可されません: {match.group(1)}") from error
        if not include_path.is_file():
            raise FileNotFoundError(f"include ファイルが見つかりません: {match.group(1)}")
        return resolve_includes(include_path, (*include_stack, resolved_path))

    resolved_source = INCLUDE_PATTERN.sub(replace_include, source)
    return resolved_source if not include_stack else VERSION_PRAGMA_PATTERN.sub("", resolved_source)


# `src/main.pine` を入口として結合し、TradingView へ直接貼り付けられる成果物を
# `dist/moment.pine` に UTF-8（BOM なし）で書き出す。出力前に未展開 include と
# version pragma の重複を検査し、Pine Script の単一スクリプト制約を守る。
#
# @returns None。成功時は生成先を標準出力へ表示する。
# @throws OSError 入出力または出力先ディレクトリの作成に失敗した場合。
# @throws ValueError 未展開 include が残る、または `//@version=6` が1つでない場合。
def build() -> None:
    bundled_source = resolve_includes(ENTRY_POINT)
    if "//#include" in bundled_source:
        raise ValueError("未展開の include が残っています")
    if bundled_source.count("//@version=6") != 1:
        raise ValueError("version pragma は1つだけ必要です")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(bundled_source, encoding="utf-8", newline="\n")
    print(f"[SUCCESS] ビルド完了: {OUTPUT_FILE.relative_to(ROOT_DIR)}")


if __name__ == "__main__":
    try:
        build()
    except (OSError, ValueError) as error:
        print(f"[ERROR] ビルド失敗: {error}", file=sys.stderr)
        raise SystemExit(1)
