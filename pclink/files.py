"""파일·폴더 관리 API."""

import os
import shutil
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from urllib.parse import quote

import psutil
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from .platform_utils import open_with_default_app
from .config import data_dir
from .security import audit, resolve_path

TEXT_LIMIT = 2 * 1024 * 1024  # 텍스트 편집은 2MB 이하만


def build_router(cfg) -> APIRouter:
    r = APIRouter(prefix="/api/fs")

    def P(raw: str, follow_last: bool = True) -> Path:
        return resolve_path(cfg, raw, follow_last)

    def entry(p: Path) -> dict:
        try:
            st = p.stat()
            is_dir = p.is_dir()
            size, mtime = (0 if is_dir else st.st_size), st.st_mtime
        except OSError:
            is_dir, size, mtime = False, 0, 0
        return {
            "name": p.name or str(p),
            "path": str(p),
            "is_dir": is_dir,
            "size": size,
            "mtime": mtime,
            "ext": p.suffix.lower().lstrip("."),
            "hidden": p.name.startswith(".") or _win_hidden(p),
        }

    @r.get("/roots")
    def roots():
        if cfg.allowed_roots:
            items = [str(Path(x).expanduser().resolve()) for x in cfg.allowed_roots]
        else:
            items = [str(Path.home())]
            for part in psutil.disk_partitions(all=False):
                if part.mountpoint not in items and "snap" not in part.mountpoint:
                    items.append(part.mountpoint)
        home = str(Path.home())
        quick = []
        if not cfg.allowed_roots or any(Path(home).is_relative_to(Path(x).expanduser().resolve()) for x in cfg.allowed_roots):
            for name, label in [("Desktop", "바탕화면"), ("Documents", "문서"), ("Downloads", "다운로드"), ("Pictures", "사진")]:
                q = Path(home) / name
                if q.is_dir():
                    quick.append({"label": label, "path": str(q)})
        return {"roots": items, "quick": quick, "sep": os.sep}

    @r.get("/list")
    def list_dir(path: str, hidden: bool = False):
        d = P(path)
        if not d.is_dir():
            raise HTTPException(404, "폴더가 없습니다.")
        try:
            children = list(d.iterdir())
        except PermissionError:
            raise HTTPException(403, "이 폴더에 접근 권한이 없습니다.")
        items = [entry(c) for c in children]
        if not hidden:
            items = [i for i in items if not i["hidden"]]
        items.sort(key=lambda i: (not i["is_dir"], i["name"].lower()))
        parent = str(d.parent) if d.parent != d else None
        if parent and cfg.allowed_roots:
            try:
                P(parent)
            except HTTPException:
                parent = None
        return {"path": str(d), "parent": parent, "items": items}

    @r.get("/download")
    def download(request: Request, path: str, inline: bool = False):
        p = P(path)
        if p.is_dir():
            audit(request, "download_zip", path=str(p))
            return _zip_response(p)
        if not p.is_file():
            raise HTTPException(404, "파일이 없습니다.")
        if not inline:
            audit(request, "download", path=str(p))
        return FileResponse(p, filename=p.name, content_disposition_type="inline" if inline else "attachment")

    @r.get("/read")
    def read_text(path: str):
        p = P(path)
        if not p.is_file():
            raise HTTPException(404, "파일이 없습니다.")
        if p.stat().st_size > TEXT_LIMIT:
            raise HTTPException(413, "2MB가 넘는 파일은 편집할 수 없습니다.")
        data = p.read_bytes()
        for enc in ("utf-8", "cp949"):
            try:
                return {"path": str(p), "encoding": enc, "content": data.decode(enc)}
            except UnicodeDecodeError:
                continue
        raise HTTPException(415, "텍스트 파일이 아닙니다.")

    class WriteBody(BaseModel):
        path: str
        content: str
        encoding: str = "utf-8"

    @r.post("/write")
    def write_text(request: Request, body: WriteBody):
        p = P(body.path)
        if p.is_dir():
            raise HTTPException(400, "폴더에는 쓸 수 없습니다.")
        if body.encoding not in ("utf-8", "cp949"):
            raise HTTPException(400, "지원하지 않는 인코딩입니다.")
        p.write_bytes(body.content.encode(body.encoding))
        audit(request, "write", path=str(p))
        return entry(p)

    @r.post("/upload")
    async def upload(request: Request, dir: str = Form(...), files: list[UploadFile] = File(...)):
        d = P(dir)
        if not d.is_dir():
            raise HTTPException(404, "업로드할 폴더가 없습니다.")
        saved = []
        for f in files:
            name = Path(f.filename or "upload").name  # 경로 조작 방지
            target = _unique(d / name)
            P(str(target))
            with open(target, "wb") as out:
                while chunk := await f.read(1024 * 1024):
                    out.write(chunk)
            saved.append(str(target))
        audit(request, "upload", files=saved)
        return {"saved": saved}

    class PathBody(BaseModel):
        path: str

    @r.post("/mkdir")
    def mkdir(request: Request, body: PathBody):
        p = P(body.path)
        if p.exists():
            raise HTTPException(409, "같은 이름이 이미 있습니다.")
        p.mkdir(parents=True)
        audit(request, "mkdir", path=str(p))
        return entry(p)

    class RenameBody(BaseModel):
        path: str
        new_name: str

    @r.post("/rename")
    def rename(request: Request, body: RenameBody):
        src = P(body.path, follow_last=False)
        name = body.new_name.strip()
        if not name or name in (".", "..") or "/" in name or "\\" in name:
            raise HTTPException(400, "사용할 수 없는 이름입니다.")
        dst = P(str(src.parent / name), follow_last=False)
        if not src.exists() and not src.is_symlink():
            raise HTTPException(404, "대상이 없습니다.")
        if dst.exists() and dst != src:
            raise HTTPException(409, "같은 이름이 이미 있습니다.")
        src.rename(dst)
        audit(request, "rename", src=str(src), dst=str(dst))
        return entry(dst)

    class MultiBody(BaseModel):
        paths: list[str]
        dest: str = ""
        permanent: bool = False

    @r.post("/copy")
    def copy(request: Request, body: MultiBody):
        return _transfer(request, body, move=False)

    @r.post("/move")
    def move(request: Request, body: MultiBody):
        return _transfer(request, body, move=True)

    def _transfer(request: Request, body: MultiBody, move: bool):
        dest = P(body.dest)
        if not dest.is_dir():
            raise HTTPException(404, "대상 폴더가 없습니다.")
        done = []
        for raw in body.paths:
            src = P(raw, follow_last=move)
            if not src.exists() and not src.is_symlink():
                raise HTTPException(404, f"없는 항목: {src.name}")
            if src.is_dir() and (dest == src or dest.is_relative_to(src)):
                raise HTTPException(400, "폴더를 자기 자신 안으로 옮길 수 없습니다.")
            target = _unique(dest / src.name)
            if move:
                shutil.move(str(src), str(target))
            elif src.is_dir():
                shutil.copytree(src, target)
            else:
                shutil.copy2(src, target)
            done.append(str(target))
        audit(request, "move" if move else "copy", paths=body.paths, dest=str(dest))
        return {"done": done}

    @r.post("/delete")
    def delete(request: Request, body: MultiBody):
        removed = []
        for raw in body.paths:
            p = P(raw, follow_last=False)
            if not p.exists() and not p.is_symlink():
                continue
            if p.parent == p or p == Path.home():
                raise HTTPException(400, "드라이브 최상위·홈 폴더는 삭제할 수 없습니다.")
            if body.permanent:
                shutil.rmtree(p) if p.is_dir() and not p.is_symlink() else p.unlink()
            else:
                _to_trash(p)
            removed.append(str(p))
        audit(request, "delete", paths=removed, permanent=body.permanent)
        return {"removed": removed}

    @r.post("/open")
    def open_on_pc(request: Request, body: PathBody):
        p = P(body.path)
        if not p.exists():
            raise HTTPException(404, "대상이 없습니다.")
        open_with_default_app(p)
        audit(request, "open_on_pc", path=str(p))
        return {"ok": True}

    @r.get("/search")
    def search(path: str, q: str, limit: int = 200):
        base = P(path)
        needle = q.strip().lower()
        if not needle:
            raise HTTPException(400, "검색어를 입력하세요.")
        results, deadline = [], time.time() + 10
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for name in dirs + files:
                if needle in name.lower():
                    results.append(entry(Path(root) / name))
                    if len(results) >= min(limit, 1000):
                        return {"items": results, "truncated": True}
            if time.time() > deadline:
                return {"items": results, "truncated": True}
        return {"items": results, "truncated": False}

    return r


# ------------------------------------------------------------------ helpers
def _unique(path: Path) -> Path:
    if not path.exists():
        return path
    stem, suffix, i = path.stem, path.suffix, 1
    while True:
        cand = path.with_name(f"{stem} ({i}){suffix}")
        if not cand.exists():
            return cand
        i += 1


def _to_trash(p: Path) -> None:
    """운영체제 휴지통으로 이동(send2trash). 없으면 ~/.pclink/trash 로 이동."""
    try:
        from send2trash import send2trash  # type: ignore

        send2trash(str(p))
        return
    except ImportError:
        pass
    trash = data_dir() / "trash" / time.strftime("%Y%m%d-%H%M%S")
    trash.mkdir(parents=True, exist_ok=True)
    shutil.move(str(p), str(_unique(trash / p.name)))


def _win_hidden(p: Path) -> bool:
    if sys.platform != "win32":
        return False
    try:
        import stat

        return bool(p.stat().st_file_attributes & stat.FILE_ATTRIBUTE_HIDDEN)  # type: ignore[attr-defined]
    except (OSError, AttributeError):
        return False


def _zip_response(folder: Path) -> StreamingResponse:
    # 임시파일에 압축한 뒤 전송하고 삭제(폴더 다운로드용)
    tmp = tempfile.TemporaryFile()
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(folder):
            for name in files:
                full = Path(root) / name
                try:
                    z.write(full, full.relative_to(folder.parent))
                except (OSError, ValueError):
                    continue
    tmp.seek(0)

    def stream():
        try:
            while chunk := tmp.read(1024 * 1024):
                yield chunk
        finally:
            tmp.close()

    fname = quote(f"{folder.name or 'drive'}.zip")
    return StreamingResponse(
        stream(), media_type="application/zip", headers={"Content-Disposition": f"attachment; filename*=UTF-8''{fname}"}
    )
