"use strict";
/* PC Link 휴대폰 웹앱 */

const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const state = {
  cwd: null, sep: "/", items: [], hidden: false,
  selecting: false, selected: new Set(),
  clip: null, // {mode:'copy'|'move', paths:[]}
  features: {},
  apps: [], procs: [], appsView: "apps",
  mouseMode: "click", live: null,
};

// ------------------------------------------------------------------ 공통
async function api(path, opts = {}) {
  const init = { credentials: "same-origin", ...opts };
  if (opts.json !== undefined) {
    init.method = init.method || "POST";
    init.headers = { "Content-Type": "application/json" };
    init.body = JSON.stringify(opts.json);
  }
  const res = await fetch(path, init);
  if (res.status === 401 && path !== "/api/login") { showLogin(); throw new Error("로그인이 필요합니다."); }
  if (!res.ok) {
    let msg = res.statusText;
    try { const j = await res.json(); msg = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail); } catch {}
    throw new Error(msg);
  }
  const ct = res.headers.get("content-type") || "";
  return ct.includes("json") ? res.json() : res;
}
const qs = (o) => new URLSearchParams(o).toString();

let toastTimer;
function toast(msg) {
  const t = $("#toast");
  t.textContent = msg; t.classList.remove("hidden");
  clearTimeout(toastTimer); toastTimer = setTimeout(() => t.classList.add("hidden"), 2600);
}
async function run(fn, okMsg) {
  try { const r = await fn(); if (okMsg) toast(okMsg); return r; } catch (e) { toast("⚠ " + e.message); }
}
function fmtSize(n) {
  if (!n) return "0 B";
  const u = ["B", "KB", "MB", "GB", "TB"]; let i = 0;
  while (n >= 1024 && i < u.length - 1) { n /= 1024; i++; }
  return `${n.toFixed(i ? 1 : 0)} ${u[i]}`;
}
function fmtDate(t) {
  if (!t) return "";
  const d = new Date(t * 1000), p = (x) => String(x).padStart(2, "0");
  return `${d.getFullYear()}.${p(d.getMonth() + 1)}.${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
}
function joinPath(dir, name) {
  return dir.endsWith(state.sep) ? dir + name : dir + state.sep + name;
}

// 하단 시트
function openSheet(title, html) {
  $("#sheetTitle").textContent = title;
  $("#sheetContent").innerHTML = html;
  $("#sheet").classList.remove("hidden");
  return $("#sheetContent");
}
function closeSheet() {
  $("#sheet").classList.add("hidden");
  $("#sheetContent").innerHTML = ""; // 동영상·오디오 재생 중지
}
$("#sheetClose").onclick = closeSheet;
$("#sheet").addEventListener("click", (e) => { if (e.target.id === "sheet") closeSheet(); });

function ask(title, placeholder, value = "") {
  return new Promise((resolve) => {
    const c = openSheet(title, `<form class="row" id="askForm"><input id="askInput" placeholder="${esc(placeholder)}" value="${esc(value)}"><button class="btn primary">확인</button></form>`);
    const inp = $("#askInput", c);
    inp.focus();
    const dot = value.lastIndexOf(".");
    if (dot > 0) inp.setSelectionRange(0, dot);
    $("#askForm", c).onsubmit = (e) => { e.preventDefault(); const v = inp.value.trim(); closeSheet(); resolve(v || null); };
  });
}

// ------------------------------------------------------------------ 로그인
function showLogin() {
  stopLive();
  $("#main").classList.add("hidden");
  $("#login").classList.remove("hidden");
}
async function login(token) {
  $("#loginErr").textContent = "";
  try {
    await api("/api/login", { json: { token } });
    await start();
  } catch (e) {
    $("#loginErr").textContent = e.message;
  }
}
$("#loginForm").onsubmit = (e) => { e.preventDefault(); login($("#tokenInput").value.trim()); };

async function start() {
  $("#login").classList.add("hidden");
  $("#main").classList.remove("hidden");
  const info = await api("/api/system/info");
  state.features = info.features;
  $("#powerBox").classList.toggle("hidden", !info.features.power);
  $("#termBox").classList.toggle("hidden", !info.features.terminal);
  $('[data-tab="screen"]').classList.toggle("hidden", !info.features.screen);
  renderSystem(info);
  const r = await api("/api/fs/roots");
  state.sep = r.sep; state.roots = r.roots; state.quick = r.quick;
  const saved = localGet("cwd");
  await openDir(saved || r.roots[0]).catch(() => openDir(r.roots[0]));
}

function localGet(k) { try { return localStorage.getItem("pclink." + k); } catch { return null; } }
function localSet(k, v) { try { localStorage.setItem("pclink." + k, v); } catch {} }

// ------------------------------------------------------------------ 탭
$$(".tabs button").forEach((b) => b.onclick = () => switchTab(b.dataset.tab));
function switchTab(name) {
  $$(".tabs button").forEach((b) => b.classList.toggle("on", b.dataset.tab === name));
  $$(".tab").forEach((s) => s.classList.toggle("hidden", s.id !== "tab-" + name));
  if (name !== "screen") stopLive();
  if (name === "apps" && !state.apps.length) loadApps();
  if (name === "screen") refreshScreen();
  if (name === "system") run(async () => renderSystem(await api("/api/system/info")));
}

// ------------------------------------------------------------------ 파일
const ICONS = {
  img: ["jpg", "jpeg", "png", "gif", "webp", "bmp", "heic", "svg"],
  video: ["mp4", "mov", "avi", "mkv", "webm", "wmv"],
  audio: ["mp3", "wav", "m4a", "flac", "ogg", "aac"],
  doc: ["doc", "docx", "hwp", "hwpx", "odt", "rtf"],
  sheet: ["xls", "xlsx", "csv", "ods"],
  slide: ["ppt", "pptx", "odp"],
  pdf: ["pdf"],
  zip: ["zip", "7z", "rar", "tar", "gz", "egg", "alz"],
  code: ["txt", "md", "json", "xml", "html", "css", "js", "ts", "py", "java", "c", "cpp", "h", "ini", "cfg", "log", "yml", "yaml", "bat", "ps1", "sh", "sql", "toml"],
  exe: ["exe", "msi", "lnk", "app", "dmg", "url"],
};
const EMOJI = { img: "🖼", video: "🎬", audio: "🎵", doc: "📝", sheet: "📊", slide: "📽", pdf: "📕", zip: "🗜", code: "📄", exe: "⚙" };
function kindOf(ext) { for (const k in ICONS) if (ICONS[k].includes(ext)) return k; return "file"; }

async function openDir(path) {
  const r = await api("/api/fs/list?" + qs({ path, hidden: state.hidden }));
  state.cwd = r.path; state.parent = r.parent; state.items = r.items;
  localSet("cwd", r.path);
  clearSelection();
  renderCrumbs();
  renderFiles(r.items);
  window.scrollTo(0, 0);
}

function renderCrumbs() {
  const p = state.cwd, sep = state.sep;
  const parts = [];
  if (sep === "\\") {
    const segs = p.split("\\").filter(Boolean);
    let acc = "";
    segs.forEach((s, i) => { acc = i === 0 ? s + "\\" : joinPath(acc, s); parts.push([s, acc]); });
  } else {
    parts.push(["/", "/"]);
    let acc = "";
    p.split("/").filter(Boolean).forEach((s) => { acc += "/" + s; parts.push([s, acc]); });
  }
  const el = $("#crumbs");
  el.innerHTML = parts.map(([n, full]) => `<button data-p="${esc(full)}">${esc(n)}</button>`).join("");
  $$("button", el).forEach((b) => b.onclick = () => run(() => openDir(b.dataset.p)));
  el.scrollLeft = el.scrollWidth;
  $("#fsUp").disabled = !state.parent;
}

function renderFiles(items, searchMode = false) {
  const ul = $("#fileList");
  if (!items.length) { ul.innerHTML = `<li class="empty">${searchMode ? "검색 결과가 없습니다" : "빈 폴더입니다"}</li>`; return; }
  ul.innerHTML = items.map((it, i) => {
    const k = it.is_dir ? "dir" : kindOf(it.ext);
    const sub = it.is_dir ? fmtDate(it.mtime) : `${fmtSize(it.size)} · ${fmtDate(it.mtime)}`;
    return `<li data-i="${i}"><span class="ico">${it.is_dir ? "📁" : EMOJI[k] || "📄"}</span>
      <span class="meta"><div class="name">${esc(it.name)}</div><div class="sub">${esc(searchMode ? it.path : sub)}</div></span>
      <button class="icon-btn more" data-more="${i}" aria-label="메뉴">⋯</button></li>`;
  }).join("");
  state.view = items;
  bindListGestures(ul);
}

function bindListGestures(ul) {
  $$("li[data-i]", ul).forEach((li) => {
    const it = state.view[+li.dataset.i];
    let timer, long = false;
    li.addEventListener("touchstart", () => { long = false; timer = setTimeout(() => { long = true; toggleSelect(li, it); navigator.vibrate?.(20); }, 500); }, { passive: true });
    li.addEventListener("touchmove", () => clearTimeout(timer), { passive: true });
    li.addEventListener("touchend", () => clearTimeout(timer));
    li.addEventListener("contextmenu", (e) => { e.preventDefault(); if (!long) toggleSelect(li, it); });
    li.addEventListener("click", (e) => {
      if (long) { long = false; return; }
      if (e.target.closest("[data-more]")) { fileMenu(it); return; }
      if (state.selecting) { toggleSelect(li, it); return; }
      if (it.is_dir) run(() => openDir(it.path)); else fileMenu(it);
    });
  });
}

function toggleSelect(li, it) {
  state.selecting = true;
  if (state.selected.has(it.path)) { state.selected.delete(it.path); li.classList.remove("sel"); }
  else { state.selected.add(it.path); li.classList.add("sel"); }
  if (!state.selected.size) return clearSelection();
  $("#selectBar").classList.remove("hidden");
  $("#selectInfo").textContent = `${state.selected.size}개 선택됨`;
}
function clearSelection() {
  state.selecting = false; state.selected.clear();
  $("#selectBar").classList.add("hidden");
  $$("#fileList li.sel").forEach((l) => l.classList.remove("sel"));
}
$$("#selectBar [data-sel]").forEach((b) => b.onclick = async () => {
  const paths = [...state.selected], a = b.dataset.sel;
  if (a === "cancel") return clearSelection();
  if (a === "delete") return deletePaths(paths);
  setClip(a, paths);
  clearSelection();
});

function setClip(mode, paths) {
  state.clip = { mode, paths };
  $("#pasteBar").classList.remove("hidden");
  $("#pasteInfo").textContent = `${paths.length}개 ${mode === "copy" ? "복사" : "이동"} — 원하는 폴더로 가서 붙여넣기`;
}
$("#pasteCancel").onclick = () => { state.clip = null; $("#pasteBar").classList.add("hidden"); };
$("#pasteHere").onclick = () => run(async () => {
  const { mode, paths } = state.clip;
  await api(`/api/fs/${mode}`, { json: { paths, dest: state.cwd } });
  state.clip = null; $("#pasteBar").classList.add("hidden");
  await openDir(state.cwd);
}, "완료했습니다");

async function deletePaths(paths, permanent = false) {
  const msg = permanent ? `${paths.length}개 항목을 영구 삭제할까요? 되돌릴 수 없습니다.` : `${paths.length}개 항목을 휴지통으로 보낼까요?`;
  if (!confirm(msg)) return;
  await run(async () => { await api("/api/fs/delete", { json: { paths, permanent } }); closeSheet(); await openDir(state.cwd); }, "삭제했습니다");
}

const dl = (p, inline = false) => "/api/fs/download?" + qs({ path: p, inline });

function fileMenu(it) {
  const k = it.is_dir ? "dir" : kindOf(it.ext);
  let preview = "";
  if (k === "img") preview = `<img src="${dl(it.path, true)}" alt="">`;
  else if (k === "video") preview = `<video src="${dl(it.path, true)}" controls playsinline preload="metadata"></video>`;
  else if (k === "audio") preview = `<audio src="${dl(it.path, true)}" controls></audio>`;
  const sub = it.is_dir ? "폴더" : `${fmtSize(it.size)} · ${fmtDate(it.mtime)}`;
  const c = openSheet(it.name, `
    ${preview ? `<div class="preview">${preview}</div>` : ""}
    <p class="muted" style="margin-top:0">${esc(sub)}</p>
    <div class="sheet-actions">
      ${it.is_dir ? `<button class="btn primary" data-a="enter">열기</button>` : ""}
      ${!it.is_dir && (k === "pdf" || k === "img" || k === "video" || k === "audio" || k === "code") ? `<button class="btn primary" data-a="view">휴대폰에서 보기</button>` : ""}
      <button class="btn" data-a="download">${it.is_dir ? "ZIP으로 받기" : "휴대폰에 저장"}</button>
      <button class="btn" data-a="pcopen">PC에서 열기</button>
      ${k === "code" || ["txt", "md", "csv"].includes(it.ext) ? `<button class="btn" data-a="edit">편집</button>` : ""}
      <button class="btn" data-a="rename">이름 바꾸기</button>
      <button class="btn" data-a="copy">복사</button>
      <button class="btn" data-a="move">이동</button>
      <button class="btn danger" data-a="delete">휴지통</button>
      <button class="btn danger" data-a="purge">영구 삭제</button>
    </div>`);
  $$("[data-a]", c).forEach((b) => b.onclick = () => fileAction(b.dataset.a, it));
}

async function fileAction(a, it) {
  if (a === "enter") { closeSheet(); return run(() => openDir(it.path)); }
  if (a === "view") return window.open(dl(it.path, true), "_blank");
  if (a === "download") { const l = document.createElement("a"); l.href = dl(it.path); l.download = it.name; l.click(); return; }
  if (a === "pcopen") return run(() => api("/api/fs/open", { json: { path: it.path } }), "PC에서 열었습니다");
  if (a === "edit") return editFile(it);
  if (a === "rename") {
    const n = await ask("이름 바꾸기", "새 이름", it.name);
    if (n && n !== it.name) run(async () => { await api("/api/fs/rename", { json: { path: it.path, new_name: n } }); await openDir(state.cwd); }, "이름을 바꿨습니다");
    return;
  }
  if (a === "copy" || a === "move") { closeSheet(); return setClip(a, [it.path]); }
  if (a === "delete") return deletePaths([it.path]);
  if (a === "purge") return deletePaths([it.path], true);
}

async function editFile(it) {
  const r = await run(() => api("/api/fs/read?" + qs({ path: it.path })));
  if (!r) return;
  const c = openSheet(`편집: ${it.name} (${r.encoding})`, `<textarea class="editor" id="editor" spellcheck="false"></textarea>
    <div class="row"><button class="btn primary" id="saveEdit" style="flex:1">저장</button></div>`);
  $("#editor", c).value = r.content;
  $("#saveEdit", c).onclick = () => run(async () => {
    await api("/api/fs/write", { json: { path: it.path, content: $("#editor").value, encoding: r.encoding } });
    closeSheet(); await openDir(state.cwd);
  }, "저장했습니다");
}

$("#fsUp").onclick = () => state.parent && run(() => openDir(state.parent));
$("#fsSearchBtn").onclick = () => { $("#fsSearchRow").classList.toggle("hidden"); $("#fsSearchInput").focus(); };
$("#fsSearchGo").onclick = () => doSearch();
$("#fsSearchInput").addEventListener("keydown", (e) => { if (e.key === "Enter") doSearch(); });
async function doSearch() {
  const q = $("#fsSearchInput").value.trim();
  if (!q) return openDir(state.cwd);
  toast("검색 중…");
  const r = await run(() => api("/api/fs/search?" + qs({ path: state.cwd, q })));
  if (r) { renderFiles(r.items, true); if (r.truncated) toast("결과가 많아 일부만 표시합니다"); }
}

$("#fsMenuBtn").onclick = () => {
  const drives = (state.roots || []).map((r) => `<button class="btn" data-go="${esc(r)}">💽 ${esc(r)}</button>`).join("");
  const quick = (state.quick || []).map((q) => `<button class="btn" data-go="${esc(q.path)}">⭐ ${esc(q.label)}</button>`).join("");
  const c = openSheet("파일 메뉴", `
    <div class="sheet-actions">
      <button class="btn primary" data-m="upload">⬆ 휴대폰 → PC 업로드</button>
      <button class="btn" data-m="mkdir">📁 새 폴더</button>
      <button class="btn" data-m="newfile">📄 새 텍스트 파일</button>
      <button class="btn" data-m="hidden">${state.hidden ? "숨김 파일 숨기기" : "숨김 파일 보기"}</button>
      <button class="btn" data-m="select">여러 개 선택</button>
      <button class="btn" data-m="refresh">새로고침</button>
    </div>
    <h3>빠른 이동</h3><div class="sheet-actions">${quick}${drives}</div>`);
  $$("[data-go]", c).forEach((b) => b.onclick = () => { closeSheet(); run(() => openDir(b.dataset.go)); });
  $$("[data-m]", c).forEach((b) => b.onclick = async () => {
    const m = b.dataset.m;
    closeSheet();
    if (m === "upload") $("#uploadInput").click();
    if (m === "refresh") run(() => openDir(state.cwd));
    if (m === "hidden") { state.hidden = !state.hidden; run(() => openDir(state.cwd)); }
    if (m === "select") { state.selecting = true; toast("항목을 눌러 선택하세요"); $("#selectBar").classList.remove("hidden"); $("#selectInfo").textContent = "0개 선택됨"; }
    if (m === "mkdir") {
      const n = await ask("새 폴더", "폴더 이름");
      if (n) run(async () => { await api("/api/fs/mkdir", { json: { path: joinPath(state.cwd, n) } }); await openDir(state.cwd); }, "폴더를 만들었습니다");
    }
    if (m === "newfile") {
      const n = await ask("새 텍스트 파일", "파일 이름", "새 문서.txt");
      if (n) run(async () => {
        await api("/api/fs/write", { json: { path: joinPath(state.cwd, n), content: "" } });
        await openDir(state.cwd);
      }, "파일을 만들었습니다");
    }
  });
};

$("#uploadInput").onchange = () => {
  const files = $("#uploadInput").files;
  if (!files.length) return;
  const fd = new FormData();
  fd.append("dir", state.cwd);
  for (const f of files) fd.append("files", f, f.name);
  const bar = $("#uploadProgress");
  bar.classList.remove("hidden");
  const xhr = new XMLHttpRequest();
  xhr.open("POST", "/api/fs/upload");
  xhr.upload.onprogress = (e) => { if (e.lengthComputable) $("div", bar).style.width = (e.loaded / e.total * 100) + "%"; };
  xhr.onloadend = () => {
    bar.classList.add("hidden"); $("div", bar).style.width = "0";
    $("#uploadInput").value = "";
    if (xhr.status === 200) { toast(`${files.length}개 업로드 완료`); openDir(state.cwd); }
    else if (xhr.status === 401) showLogin();
    else toast("⚠ 업로드 실패 (" + xhr.status + ")");
  };
  xhr.send(fd);
};

// ------------------------------------------------------------------ 프로그램 / 프로세스
$$("#appsSeg button").forEach((b) => b.onclick = () => {
  $$("#appsSeg button").forEach((x) => x.classList.toggle("on", x === b));
  state.appsView = b.dataset.v;
  state.appsView === "apps" ? loadApps() : loadProcs();
});
$("#appsRefresh").onclick = () => state.appsView === "apps" ? loadApps(true) : loadProcs();
$("#appsFilter").addEventListener("input", renderApps);

async function loadApps(refresh = false) {
  const r = await run(() => api("/api/apps?" + qs({ refresh })));
  if (r) { state.apps = r.items; renderApps(); }
}
async function loadProcs() {
  const r = await run(() => api("/api/processes"));
  if (r) { state.procs = r.items; renderApps(); }
}
function renderApps() {
  const q = $("#appsFilter").value.trim().toLowerCase();
  const ul = $("#appsList");
  if (state.appsView === "apps") {
    const list = state.apps.filter((a) => a.name.toLowerCase().includes(q));
    ul.innerHTML = list.length ? list.map((a) => `<li data-id="${esc(a.id)}"><span class="ico">${a.kind === "custom" ? "⭐" : "🧩"}</span>
      <span class="meta"><div class="name">${esc(a.name)}</div></span><span class="muted">실행 ▸</span></li>`).join("")
      : `<li class="empty">프로그램이 없습니다</li>`;
    $$("li[data-id]", ul).forEach((li) => li.onclick = () => {
      const a = state.apps.find((x) => x.id === li.dataset.id);
      if (confirm(`PC에서 '${a.name}' 을(를) 실행할까요?`)) run(() => api("/api/apps/launch", { json: { id: a.id } }), "실행했습니다");
    });
  } else {
    const list = state.procs.filter((p) => p.name.toLowerCase().includes(q));
    ul.innerHTML = list.map((p) => `<li data-pid="${p.pid}"><span class="ico">⚙</span>
      <span class="meta"><div class="name">${esc(p.name)}</div><div class="sub">PID ${p.pid} · 메모리 ${fmtSize(p.memory)}</div></span></li>`).join("")
      || `<li class="empty">없음</li>`;
    $$("li[data-pid]", ul).forEach((li) => li.onclick = () => {
      const p = state.procs.find((x) => x.pid === +li.dataset.pid);
      const c = openSheet(`${p.name} (PID ${p.pid})`, `<p class="muted">저장하지 않은 작업은 사라질 수 있습니다.</p>
        <div class="sheet-actions"><button class="btn" data-f="0">종료</button><button class="btn danger" data-f="1">강제 종료</button></div>`);
      $$("[data-f]", c).forEach((b) => b.onclick = () => run(async () => {
        await api("/api/processes/kill", { json: { pid: p.pid, force: b.dataset.f === "1" } });
        closeSheet(); await loadProcs();
      }, "종료했습니다"));
    });
  }
}

// ------------------------------------------------------------------ 원격 화면
const img = $("#screenImg");
let shotBusy = false;
async function refreshScreen() {
  if (shotBusy) return;
  shotBusy = true;
  try {
    const w = Math.min(1920, Math.round(img.parentElement.clientWidth * (window.devicePixelRatio || 1)));
    const res = await api("/api/screen/shot?" + qs({ width: w, quality: state.live ? 50 : 70, t: Date.now() }));
    const blob = await res.blob();
    const old = img.src;
    img.src = URL.createObjectURL(blob);
    if (old.startsWith("blob:")) URL.revokeObjectURL(old);
  } catch (e) {
    toast("⚠ " + e.message); stopLive();
  } finally { shotBusy = false; }
}
function stopLive() {
  if (state.live) { clearInterval(state.live); state.live = null; }
  $("#screenLive").textContent = "▶"; $("#screenLive").classList.remove("on");
}
$("#screenLive").onclick = () => {
  if (state.live) return stopLive();
  state.live = setInterval(refreshScreen, 800);
  $("#screenLive").textContent = "⏸"; $("#screenLive").classList.add("on");
};
$("#screenRefresh").onclick = refreshScreen;
$("#screenPh").onclick = refreshScreen;
$$("#mouseMode button").forEach((b) => b.onclick = () => {
  $$("#mouseMode button").forEach((x) => x.classList.toggle("on", x === b));
  state.mouseMode = b.dataset.v;
});
img.addEventListener("click", async (e) => {
  if (!img.naturalWidth) return refreshScreen();
  const r = img.getBoundingClientRect();
  const x = (e.clientX - r.left) / r.width, y = (e.clientY - r.top) / r.height;
  await run(() => api("/api/screen/mouse", { json: { action: state.mouseMode, x, y } }));
  setTimeout(refreshScreen, 350);
});
let lastPos = { x: 0.5, y: 0.5 };
img.addEventListener("pointerdown", (e) => { const r = img.getBoundingClientRect(); lastPos = { x: (e.clientX - r.left) / r.width, y: (e.clientY - r.top) / r.height }; });
$$("[data-scroll]").forEach((b) => b.onclick = async () => {
  await run(() => api("/api/screen/mouse", { json: { action: "scroll", amount: +b.dataset.scroll, ...lastPos } }));
  setTimeout(refreshScreen, 300);
});
$("#typeForm").onsubmit = async (e) => {
  e.preventDefault();
  const text = $("#typeInput").value;
  if (!text) return;
  await run(() => api("/api/screen/keyboard", { json: { text } }));
  $("#typeInput").value = "";
  setTimeout(refreshScreen, 300);
};
$$("#keys [data-k]").forEach((b) => b.onclick = async () => {
  await run(() => api("/api/screen/keyboard", { json: { keys: b.dataset.k.split("+") } }));
  setTimeout(refreshScreen, 300);
});

// ------------------------------------------------------------------ 시스템
function renderSystem(i) {
  $("#sysHost").textContent = `💻 ${i.hostname}`;
  const meter = (p) => `<div class="meter"><div style="width:${Math.min(100, p)}%"></div></div>`;
  const cards = [
    `<div class="card"><div class="k">CPU (${i.cpu_count}코어)</div><div class="v">${i.cpu_percent.toFixed(0)}%</div>${meter(i.cpu_percent)}</div>`,
    `<div class="card"><div class="k">메모리</div><div class="v">${i.memory.percent.toFixed(0)}%</div><div class="s">${fmtSize(i.memory.used)} / ${fmtSize(i.memory.total)}</div>${meter(i.memory.percent)}</div>`,
  ];
  if (i.battery) cards.push(`<div class="card"><div class="k">배터리</div><div class="v">${Math.round(i.battery.percent)}%</div><div class="s">${i.battery.plugged ? "충전 중" : "배터리 사용"}</div>${meter(i.battery.percent)}</div>`);
  cards.push(`<div class="card"><div class="k">운영체제</div><div class="s">${esc(i.os)}</div><div class="s">부팅: ${fmtDate(i.boot_time)}</div></div>`);
  i.disks.forEach((d) => cards.push(`<div class="card"><div class="k">디스크 ${esc(d.mount)}</div><div class="v">${d.percent.toFixed(0)}%</div><div class="s">${fmtSize(d.used)} / ${fmtSize(d.total)}</div>${meter(d.percent)}</div>`));
  $("#sysCards").innerHTML = cards.join("");
}
$("#sysRefresh").onclick = () => run(async () => renderSystem(await api("/api/system/info")));

$("#clipSend").onclick = () => run(() => api("/api/clipboard", { json: { text: $("#clipText").value } }), "PC 클립보드에 복사했습니다");
$("#clipGet").onclick = () => run(async () => {
  const r = await api("/api/clipboard");
  $("#clipText").value = r.text;
  try { await navigator.clipboard.writeText(r.text); toast("휴대폰 클립보드에도 복사했습니다"); } catch { toast("가져왔습니다"); }
});

const POWER_LABEL = { lock: "화면 잠금", sleep: "절전", restart: "다시 시작", shutdown: "시스템 종료", cancel: "종료 취소" };
$$("[data-power]").forEach((b) => b.onclick = () => {
  const a = b.dataset.power;
  if (["sleep", "restart", "shutdown"].includes(a) && !confirm(`정말 PC를 '${POWER_LABEL[a]}' 할까요?`)) return;
  run(() => api("/api/system/power", { json: { action: a, confirm: true } }),
    a === "restart" || a === "shutdown" ? `${POWER_LABEL[a]} 예약됨 (약 1분 뒤, 취소 가능)` : `${POWER_LABEL[a]} 실행`);
});

$("#termForm").onsubmit = async (e) => {
  e.preventDefault();
  const command = $("#termInput").value.trim();
  if (!command) return;
  const out = $("#termOut");
  out.textContent = "실행 중…";
  try {
    const r = await api("/api/terminal/run", { json: { command, cwd: state.cwd || "" } });
    out.textContent = `$ ${command}\n${r.stdout}${r.stderr ? "\n[오류]\n" + r.stderr : ""}\n(종료 코드 ${r.code})`;
  } catch (err) { out.textContent = "⚠ " + err.message; }
};

$("#logoutBtn").onclick = async () => { await api("/api/logout", { method: "POST" }).catch(() => {}); showLogin(); };

// ------------------------------------------------------------------ 시작
(async () => {
  if ("serviceWorker" in navigator && window.isSecureContext) navigator.serviceWorker.register("sw.js").catch(() => {});
  const m = location.hash.match(/token=([^&]+)/);
  if (m) {
    history.replaceState(null, "", location.pathname); // 주소창에서 토큰 제거
    return login(decodeURIComponent(m[1]));
  }
  const p = await fetch("/api/ping", { credentials: "same-origin" }).then((r) => r.json()).catch(() => ({}));
  if (p.authed) start().catch((e) => toast("⚠ " + e.message)); else showLogin();
})();
