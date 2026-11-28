// Bộ chạy đo giao diện bằng trình duyệt ẩn qua CDP (0.10.1 P7, QĐ683) – 0 thư viện: WebSocket, fetch của Node; trình duyệt có sẵn
// của máy chạy (máy GitHub: google-chrome). Không ghi đường dẫn máy cá nhân: trình duyệt, hồ sơ đọc từ biến môi trường hoặc
// thư mục tạm của hệ điều hành. Cách gọi: CONG=<cổng> PHIEN=<cookie> node chay_do.mjs <tệp ca .mjs> <thư mục kết quả>
// Tệp ca xuất CA = [{ten, duong, kho: [rộng, cao, dienthoai], chedo: 'sang'|'toi', truoc, chuot: [[loại, x, y, lần]], phim, do, anh, tai_lai}]
import { spawn } from 'node:child_process';
import { writeFileSync, mkdirSync, mkdtempSync, rmSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { pathToFileURL } from 'node:url';

const CONG = process.env.CONG || '8365', CONG_DB = Number(process.env.CONG_DB || 9361), PHIEN = process.env.PHIEN || '';
const TRINHDUYET = process.env.TRINHDUYET || 'google-chrome';
const HOSO = process.env.HOSO || mkdtempSync(join(tmpdir(), 'hoso-do-'));
const KHONG_ANH = process.env.KHONG_ANH === '1';
const [tepCa, raRa] = process.argv.slice(2);
const { CA } = await import(pathToFileURL(tepCa).href);
mkdirSync(raRa, { recursive: true });
const ngu = ms => new Promise(r => setTimeout(r, ms));
const co = ['--headless=new', `--remote-debugging-port=${CONG_DB}`, `--user-data-dir=${HOSO}`, '--disable-component-update', '--no-first-run',
  '--disable-background-networking', '--disable-gpu'];
if (process.env.CI === 'true') co.push('--no-sandbox');   // máy GitHub (biến CI) – hộp chạy dùng 01 lần, chỉ dữ liệu thử
const p = spawn(TRINHDUYET, [...co, 'about:blank'], { stdio: 'ignore', detached: process.platform !== 'win32' });
let ws, id = 0; const cho = new Map(), ketqua = [];
const goi = (m, pr = {}) => new Promise((ok, loi) => { const i = ++id; cho.set(i, { ok, loi }); ws.send(JSON.stringify({ id: i, method: m, params: pr })); });
const chuot = async (loai, x, y, lan) => goi('Input.dispatchMouseEvent', { type: loai, x, y, button: 'left', buttons: loai === 'mouseReleased' ? 0 : 1, clickCount: lan || 1 });
try {
  for (let i = 0; i < 120 && !ws; i++) {
    try { const t = (await (await fetch(`http://127.0.0.1:${CONG_DB}/json/list`)).json()).find(x => x.type === 'page'); if (t) ws = new WebSocket(t.webSocketDebuggerUrl); } catch {}
    if (!ws) await ngu(250);
  }
  if (!ws) throw new Error('trình duyệt không mở được cổng điều khiển');
  await new Promise(r => ws.addEventListener('open', r));
  ws.addEventListener('message', e => { const m = JSON.parse(e.data); if (m.id && cho.has(m.id)) { const c = cho.get(m.id); cho.delete(m.id); m.error ? c.loi(new Error(m.error.message)) : c.ok(m.result); } });
  await goi('Page.enable'); await goi('Network.enable');
  if (PHIEN) await goi('Network.setCookie', { name: 'igm360_phien', value: PHIEN, domain: '127.0.0.1', path: '/' });
  for (const c of CA) {
    const [w, h, dt] = c.kho || [1440, 900, false];
    await goi('Emulation.setDeviceMetricsOverride', { width: w, height: h, deviceScaleFactor: dt ? 3 : 1, mobile: !!dt });
    await goi('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-color-scheme', value: c.chedo === 'toi' ? 'dark' : 'light' }] });
    await goi('Page.navigate', { url: `http://127.0.0.1:${CONG}${c.duong || '/'}` }); await ngu(c.cho || 2500);
    if (c.truoc) { await goi('Runtime.evaluate', { expression: c.truoc, awaitPromise: true }); await ngu(c.cho_sau || 800); }
    for (const [loai, x, y, lan] of c.chuot || []) { await chuot(loai, x, y, lan); await ngu(60); }
    for (const k of c.phim || []) { await goi('Input.dispatchKeyEvent', { type: 'keyDown', key: k, code: k }); await goi('Input.dispatchKeyEvent', { type: 'keyUp', key: k, code: k }); await ngu(60); }
    if (c.tai_lai) { await goi('Page.reload', {}); await ngu(c.cho || 2500); if (c.truoc_sau_tai) { await goi('Runtime.evaluate', { expression: c.truoc_sau_tai, awaitPromise: true }); await ngu(600); } }
    const r = await goi('Runtime.evaluate', { returnByValue: true, awaitPromise: true, expression: c.do || '0' });
    const dong = { ten: c.ten, kho: `${w}x${h}`, chedo: c.chedo || 'sang', gt: r.result ? r.result.value : null, loi: r.exceptionDetails ? (r.exceptionDetails.exception || {}).description || r.exceptionDetails.text : null };
    if (c.anh && !KHONG_ANH) {
      const a = await goi('Page.captureScreenshot', { format: 'png' });
      const tep = join(raRa, `${c.ten.replace(/[^A-Za-z0-9_-]+/g, '_')}_${w}_${c.chedo || 'sang'}.png`);
      writeFileSync(tep, Buffer.from(a.data, 'base64')); dong.anh = tep;
    }
    ketqua.push(dong);
  }
  writeFileSync(join(raRa, 'ketqua.json'), JSON.stringify(ketqua, null, 1));
} finally {
  try { ws && ws.close(); } catch {}
  try { if (process.platform === 'win32') p.kill(); else process.kill(-p.pid, 'SIGKILL'); } catch {}   // tắt đúng nhóm tiến trình trình duyệt do bộ chạy này mở
  if (!process.env.HOSO) { try { rmSync(HOSO, { recursive: true, force: true }); } catch {} }
}
