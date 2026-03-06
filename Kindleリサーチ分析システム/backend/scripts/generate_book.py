#!/usr/bin/env python3
"""
Kindle本生成スクリプト

Usage:
    python3 generate_book.py --topic "Dual Investment投資" --author "著者名"
    python3 generate_book.py --topic "自己啓発" --author "山田太郎"
"""
import argparse
import asyncio
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.generators.script_generator import ScriptGenerator


async def main(topic: str, author: str) -> None:
    slug = topic.replace(" ", "_").replace("　", "_")[:30]
    output_dir = project_root.parent / "output" / slug

    generator = ScriptGenerator(output_dir=output_dir)
    book = await generator.generate(topic=topic, author=author)

    print(f"タイトル:    {book.blueprint.title}")
    print(f"章数:        {len(book.chapters)}章")
    print(f"文字数:      {len(book.full_text):,}文字")
    print(f"品質スコア:  {book.quality_score}/100")
    print(f"出力先:      {output_dir}/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Kindle本台本を生成する")
    parser.add_argument(
        "--topic",
        type=str,
        default="Dual Investment投資",
        help="本のテーマ（例: 'Dual Investment投資'）",
    )
    parser.add_argument(
        "--author",
        type=str,
        default="田中投資研究所",
        help="著者名",
    )
    args = parser.parse_args()
    asyncio.run(main(args.topic, args.author))
