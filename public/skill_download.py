"""NiceTool Skill 公共下载接口。"""

from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

router = APIRouter(tags=["nicetool-skill"])

SKILL_SOURCE = (
    Path(__file__).resolve().parents[1] / "plugins" / "nicetool" / "skills" / "nicetool"
)
ARCHIVE_NAME = "nicetool-skill.zip"
ARCHIVE_ROOT = "nicetool"


def _build_skill_archive(
    source: Path | None = None, archive_root: str = ARCHIVE_ROOT
) -> bytes:
    """将固定的 NiceTool Skill 目录打包为内存 ZIP。"""
    source = source or SKILL_SOURCE
    if not source.is_dir() or not (source / "SKILL.md").is_file():
        raise ValueError("NiceTool Skill 文件不完整")

    output = BytesIO()
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        for path in sorted(source.rglob("*")):
            if (
                not path.is_file()
                or path.is_symlink()
                or "__pycache__" in path.parts
                or path.suffix in {".pyc", ".pyo"}
                or path.name == ".DS_Store"
            ):
                continue
            relative_path = path.relative_to(source).as_posix()
            archive.write(path, f"{archive_root}/{relative_path}")
    return output.getvalue()


@router.get("/api/downloads/nicetool-skill.zip", response_class=Response)
def download_nicetool_skill() -> Response:
    """下载当前 Server 随附的 NiceTool Skill。"""
    try:
        content = _build_skill_archive()
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return Response(
        content=content,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{ARCHIVE_NAME}"',
            "Cache-Control": "no-store",
        },
    )
