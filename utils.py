import os
import re
import shutil
import hashlib
from pathlib import Path


def get_md_image_folder(md_path: Path) -> str:
    stem = md_path.stem
    return f".{stem}"


def resolve_unique_filename(folder: Path, filename: str) -> str:
    folder.mkdir(parents=True, exist_ok=True)
    name, ext = os.path.splitext(filename)
    candidate = filename
    counter = 1
    while (folder / candidate).exists():
        candidate = f"{name}_{counter}{ext}"
        counter += 1
    return candidate


def resolve_unique_md_name(output_folder: Path, md_name: str) -> str:
    output_folder.mkdir(parents=True, exist_ok=True)
    name, ext = os.path.splitext(md_name)
    candidate = md_name
    counter = 1
    while (output_folder / candidate).exists():
        candidate = f"{name}_{counter}{ext}"
        counter += 1
    return candidate


def flatten_name(rel_path: Path) -> str:
    parts = list(rel_path.parts)
    return "_".join(parts)


def is_url(path: str) -> bool:
    return bool(re.match(r'^https?://', path, re.IGNORECASE))


def is_data_uri(path: str) -> bool:
    return path.startswith('data:')


def is_absolute_path(path: str) -> bool:
    return os.path.isabs(path)


def extract_image_refs(md_content: str) -> list[tuple[int, int, str]]:
    results = []
    pattern_md = r'!\[[^\]]*\]\(<?([^)>]+?)>?(?:\s+"[^"]*")?\s*\)'
    for m in re.finditer(pattern_md, md_content):
        url = m.group(1)
        if not is_url(url) and not is_data_uri(url):
            results.append((m.start(), m.end(), url))

    pattern_html = r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>'
    for m in re.finditer(pattern_html, md_content, re.IGNORECASE):
        url = m.group(1)
        if not is_url(url) and not is_data_uri(url):
            results.append((m.start(), m.end(), url))

    results.sort(key=lambda x: x[0])
    return results


def replace_image_ref(md_content: str, start: int, end: int,
                      old_path: str, new_path: str) -> str:
    before = md_content[:start]
    after = md_content[end:]
    middle = md_content[start:end]
    updated = middle.replace(old_path, new_path)
    return before + updated + after


def get_display_path(path: Path, base: Path) -> str:
    try:
        return str(path.relative_to(base))
    except ValueError:
        return str(path)
