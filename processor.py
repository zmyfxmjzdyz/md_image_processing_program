import os
import shutil
from pathlib import Path
from typing import Callable

from utils import (
    get_md_image_folder,
    resolve_unique_filename,
    resolve_unique_md_name,
    flatten_name,
    extract_image_refs,
    replace_image_ref,
    get_display_path,
)


class MdImageProcessor:
    def __init__(self, input_folder: str, output_folder: str,
                 keep_structure: bool = True):
        self.input_folder = Path(input_folder).resolve()
        self.output_folder = Path(output_folder).resolve()
        self.keep_structure = keep_structure
        self._cancel_flag = False

    def cancel(self):
        self._cancel_flag = True

    def _collect_md_files(self) -> list[Path]:
        md_files = []
        for root, dirs, files in os.walk(self.input_folder):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for f in files:
                if f.lower().endswith('.md'):
                    md_files.append(Path(root) / f)
        return md_files

    def _resolve_image_source(self, md_file: Path, img_path: str) -> Path | None:
        if img_path.startswith('/') or (len(img_path) > 2 and img_path[1] == ':'):
            candidate = Path(img_path)
        else:
            candidate = (md_file.parent / img_path).resolve()

        try:
            candidate = candidate.resolve()
        except (OSError, ValueError):
            return None

        if candidate.exists() and candidate.is_file():
            return candidate

        decoded = img_path
        try:
            from urllib.parse import unquote
            decoded = unquote(img_path)
        except Exception:
            pass

        if decoded != img_path:
            if img_path.startswith('/') or (len(img_path) > 2 and img_path[1] == ':'):
                candidate2 = Path(decoded)
            else:
                candidate2 = (md_file.parent / decoded).resolve()
            try:
                candidate2 = candidate2.resolve()
            except (OSError, ValueError):
                return None
            if candidate2.exists() and candidate2.is_file():
                return candidate2

        return None

    def _process_single_md(self, md_file: Path,
                           callback: Callable | None = None) -> bool:
        if self._cancel_flag:
            return False

        rel_path = md_file.relative_to(self.input_folder)
        display = str(rel_path)

        if callback:
            callback("info", f"处理: {display}")

        try:
            md_content = md_file.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            try:
                md_content = md_file.read_text(encoding='gbk')
            except Exception as e:
                if callback:
                    callback("error", f"读取失败 {display}: {e}")
                return False
        except PermissionError as e:
            if callback:
                callback("error", f"权限不足 {display}: {e}")
            return False

        image_refs = extract_image_refs(md_content)
        if not image_refs:
            if self.keep_structure:
                out_md_dir = self.output_folder / rel_path.parent
            else:
                out_md_dir = self.output_folder
            out_md_dir.mkdir(parents=True, exist_ok=True)

            if self.keep_structure:
                out_md_name = md_file.name
            else:
                flat = flatten_name(rel_path)
                out_md_name = resolve_unique_md_name(out_md_dir, flat)
                if out_md_name != flat:
                    md_name_display = out_md_name
                else:
                    md_name_display = flat
                display = md_name_display

            out_md_path = out_md_dir / out_md_name
            try:
                out_md_path.write_text(md_content, encoding='utf-8')
            except PermissionError as e:
                if callback:
                    callback("error", f"写入失败 {display}: {e}")
                return False

            if callback:
                callback("info", f"完成(无图片): {display}")
            return True

        if self.keep_structure:
            out_md_dir = self.output_folder / rel_path.parent
            out_md_name = md_file.name
            img_folder_name = get_md_image_folder(md_file)
            img_folder = out_md_dir / img_folder_name
        else:
            out_md_dir = self.output_folder
            flat = flatten_name(rel_path)
            out_md_name = resolve_unique_md_name(out_md_dir, flat)
            if out_md_name != flat:
                md_name_display = out_md_name
            else:
                md_name_display = flat
            display = md_name_display
            img_folder_name = get_md_image_folder(Path(out_md_name))
            img_folder = out_md_dir / img_folder_name

        out_md_dir.mkdir(parents=True, exist_ok=True)

        img_folder_rel = img_folder_name.replace('\\', '/')
        updated_content = md_content
        copied_count = 0

        for start, end, img_path in reversed(image_refs):
            if self._cancel_flag:
                return False

            source_file = self._resolve_image_source(md_file, img_path)
            if source_file is None:
                if callback:
                    callback("warn",
                             f"  图片未找到: {img_path} (来自 {display})")
                continue

            img_filename = source_file.name
            unique_img_name = resolve_unique_filename(img_folder, img_filename)

            try:
                shutil.copy2(source_file, img_folder / unique_img_name)
            except PermissionError as e:
                if callback:
                    callback("error",
                             f"  复制失败 {source_file.name}: {e}")
                continue
            except OSError as e:
                if callback:
                    callback("error",
                             f"  复制失败 {source_file.name}: {e}")
                continue

            new_img_rel = f"{img_folder_rel}/{unique_img_name}"
            new_img_rel = new_img_rel.replace('\\', '/')
            updated_content = replace_image_ref(
                updated_content, start, end, img_path, new_img_rel
            )
            copied_count += 1

        out_md_path = out_md_dir / out_md_name
        try:
            out_md_path.write_text(updated_content, encoding='utf-8')
        except PermissionError as e:
            if callback:
                callback("error", f"写入失败 {display}: {e}")
            return False

        if callback:
            callback("info",
                     f"完成: {display} (复制 {copied_count} 张图片)")
        return True

    def run(self, callback: Callable | None = None) -> dict:
        self._cancel_flag = False
        md_files = self._collect_md_files()

        if callback:
            callback("info", f"找到 {len(md_files)} 个 Markdown 文件")

        stats = {"total": len(md_files), "success": 0, "failed": 0}
        for i, md_file in enumerate(md_files):
            if self._cancel_flag:
                if callback:
                    callback("info", "处理已取消")
                break

            ok = self._process_single_md(md_file, callback)
            if ok:
                stats["success"] += 1
            else:
                stats["failed"] += 1

            if callback:
                progress_pct = int((i + 1) / len(md_files) * 100)
                callback("progress", progress_pct)

        if callback and not self._cancel_flag:
            callback("info",
                     f"处理完成: 成功 {stats['success']}, 失败 {stats['failed']}")

        return stats
