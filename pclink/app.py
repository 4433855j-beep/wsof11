"""FastAPI 앱 조립: 인증 미들웨어 + 각 기능 라우터 + 휴대폰용 웹앱(PWA) 정적 파일."""
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import files, screen, system
from .config import Config
from .security import SESSION_COOKIE, SESSION_TTL, Auth, audit, client_ip

WEB_DIR = Path(__file__).parent / "web"
PUBLIC_API = {"/api/login", "/api/ping"}


class LoginBody(BaseModel):
    token: str


def create_app(cfg: Config) -> FastAPI:
    app = FastAPI(title="PC Link", docs_url=None, redoc_url=None, openapi_url=None)
    auth = Auth(cfg)
    app.state.auth = auth

    @app.middleware("http")
    async def guard(request: Request, call_next):
        path = request.url.path
        if path.startswith("/api/") and path not in PUBLIC_API and not auth.valid(request):
            return JSONResponse({"detail": "로그인이 필요합니다."}, status_code=401)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        return response

    @app.get("/api/ping")
    def ping(request: Request):
        return {"ok": True, "authed": auth.valid(request)}

    @app.post("/api/login")
    def login(request: Request, body: LoginBody):
        if not auth.check_token(body.token.strip(), client_ip(request)):
            audit(request, "login_fail")
            raise HTTPException(401, "접속 코드가 올바르지 않습니다.")
        sid = auth.new_session()
        audit(request, "login")
        resp = JSONResponse({"ok": True})
        resp.set_cookie(
            SESSION_COOKIE, sid, max_age=SESSION_TTL, httponly=True, samesite="strict",
            secure=request.url.scheme == "https",
        )
        return resp

    @app.post("/api/logout")
    def logout(request: Request):
        auth.drop_session(request.cookies.get(SESSION_COOKIE, ""))
        resp = JSONResponse({"ok": True})
        resp.delete_cookie(SESSION_COOKIE)
        return resp

    app.include_router(files.build_router(cfg))
    app.include_router(system.build_router(cfg))
    app.include_router(screen.build_router(cfg))

    @app.get("/")
    def index():
        return FileResponse(WEB_DIR / "index.html", headers={"Cache-Control": "no-cache"})

    app.mount("/", StaticFiles(directory=WEB_DIR), name="web")
    return app
