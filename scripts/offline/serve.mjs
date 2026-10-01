import http from 'node:http'
import { readFile, stat } from 'node:fs/promises'
import { resolve, sep, extname } from 'node:path'
import { fileURLToPath } from 'node:url'
const root = fileURLToPath(new URL('.', import.meta.url))
const port = Number(process.env.PORT || 4178)
const mime = { '.html':'text/html; charset=utf-8', '.js':'text/javascript', '.css':'text/css', '.json':'application/json', '.svg':'image/svg+xml', '.png':'image/png', '.jpg':'image/jpeg', '.webp':'image/webp', '.woff2':'font/woff2', '.woff':'font/woff', '.pdf':'application/pdf', '.md':'text/plain; charset=utf-8' }
const home = `<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PIL travel kit</title><style>body{font:18px/1.7 system-ui;max-width:750px;margin:60px auto;padding:0 24px;color:#213e35;background:#f5f4ee}a{color:#246154}li{margin:18px 0}code{background:#e3e9df;padding:3px 6px}</style><h1>Your offline PIL workspace</h1><p>Everything linked below is served from this laptop.</p><ul><li><a href="/morning-recall/#/learn/openai-pil-offline">Start here: the onsite learning guide</a></li><li><a href="/lab/">Prototype reference and Excalidraw whiteboard</a></li><li><a href="/morning-recall/#/learn">Existing learning library</a></li><li><a href="/morning-recall/#/designs">Worked system designs</a></li></ul><p>To edit code, use <code>source/uie-practice/pil-offline</code>. Run <code>npm run dev</code> after installing dependencies on this laptop.</p><p>The official course source is under <code>source/pil-frontend-course</code>. Start it in another terminal with <code>node run-course.mjs</code>, then open <a href="http://localhost:3000/">the local course</a>.</p><p>Export drawings as .excalidraw files. Browser draft storage does not transfer to another machine.</p></html>`
const roots = { '/morning-recall/': resolve(root, 'reading'), '/lab/': resolve(root, 'lab') }
http.createServer(async (req,res) => {
  try {
    const path = decodeURIComponent(new URL(req.url, 'http://localhost').pathname)
    if (req.method !== 'GET' && req.method !== 'HEAD') { res.writeHead(405); res.end(); return }
    if (path === '/') { res.writeHead(200, { 'Content-Type':mime['.html'] }); res.end(req.method === 'HEAD' ? undefined : home); return }
    if (path === '/lab' || path === '/morning-recall') { res.writeHead(302,{Location:path+'/'});res.end();return }
    const prefix = Object.keys(roots).find(p => path.startsWith(p))
    if (!prefix) { res.writeHead(404); res.end('Not found'); return }
    const base = roots[prefix]
    let file = resolve(base, path.slice(prefix.length) || 'index.html')
    if (!file.startsWith(base + sep)) { res.writeHead(403);res.end();return }
    if ((await stat(file)).isDirectory()) file = resolve(file,'index.html')
    const bytes = await readFile(file)
    res.writeHead(200,{'Content-Type':mime[extname(file)]||'application/octet-stream','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'})
    res.end(req.method === 'HEAD' ? undefined : bytes)
  } catch { res.writeHead(404);res.end('Not found') }
}).listen(port,'127.0.0.1',() => console.log(`PIL travel kit: http://127.0.0.1:${port}/ (Ctrl+C to stop)`)).on('error',err=>{console.error(err.message);process.exitCode=1})
