import { cp, mkdir, readFile, readdir, stat, writeFile } from 'node:fs/promises'
import { resolve, dirname, relative, join, basename } from 'node:path'
import { fileURLToPath } from 'node:url'
import { createHash } from 'node:crypto'
import { execFileSync } from 'node:child_process'
const repo = resolve(dirname(fileURLToPath(import.meta.url)), '../..')
const ui = resolve(process.env.UIE_REPO || join(repo,'../uie-practice'))
const lab = join(ui,'pil-offline')
const includeDeps = process.argv.includes('--include-deps')
const stamp = new Date().toISOString().replace(/[:.]/g,'-')
const output = join(repo,'out',`pil-travel-${stamp}`)
const kit = join(output,'pil-travel-kit')
// A fresh timestamped directory avoids deleting any previous travel copy or drawings.
for (const path of [join(repo,'dist/index.html'),join(lab,'dist/index.html')]) await stat(path)
await mkdir(kit,{recursive:true})
await cp(join(repo,'dist'),join(kit,'reading'),{recursive:true})
await cp(join(lab,'dist'),join(kit,'lab'),{recursive:true})
async function optional(src,dest) { try { await stat(src) } catch(e) { if(e.code==='ENOENT') return; throw e } await cp(src,dest,{recursive:true,filter:p=>!p.split('/').some(x=>x==='node_modules'||x==='.git'||x==='dist'||x==='out'||x.startsWith('.env'))}) }
// Allowlist source/config files. No .git, credentials, unrelated notes, or recruiter attachment.
for(const [from,name] of [[repo,'staff-eng-interview-prompter'],[ui,'uie-practice']]) {
  const dest = join(kit,'source',name); await mkdir(dest,{recursive:true})
  for(const entry of ['src','public','scripts','package.json','package-lock.json','index.html','README.md','AGENTS.md','BUILD_SPEC.md','DESIGN_PAGE_AUTHORING.md','AUDIO_SCRIPT_AUTHORING.md','vite.config.ts','vitest.config.ts','vitest.setup.ts','tsconfig.json','tsconfig.app.json','tsconfig.node.json','tailwind.config.js','tailwind.config.ts','postcss.config.js','postcss.config.cjs','pil-offline']) await optional(join(from,entry),join(dest,entry))
  if(name==='staff-eng-interview-prompter') for(const entry of await readdir(from)) if(entry.endsWith('.md') && !entry.includes('handoff') && entry!=='openai-sysdesign-top5.md') await optional(join(from,entry),join(dest,entry))
}
// Lab's npm resolver setting must accompany its lockfile.
await cp(join(lab,'.npmrc'),join(kit,'source/uie-practice/pil-offline/.npmrc'))
if(includeDeps) await cp(join(lab,'node_modules'),join(kit,'source/uie-practice/pil-offline/node_modules'),{recursive:true,verbatimSymlinks:true})
const course = resolve(process.env.PIL_COURSE_REPO || join(repo,'../pil-frontend-course'))
try {
  await stat(join(course,'package.json'))
  await optional(course,join(kit,'source/pil-frontend-course'))
  if(includeDeps) {
    await cp(join(course,'node_modules'),join(kit,'source/pil-frontend-course/node_modules'),{recursive:true,verbatimSymlinks:true})
    await cp(join(course,'offline-tools/node_modules'),join(kit,'source/pil-frontend-course/offline-tools/node_modules'),{recursive:true,verbatimSymlinks:true})
  }
} catch(e) { if(e.code!=='ENOENT') throw e; console.warn('Course or its dependencies missing; course is optional.') }
for(const file of ['serve.mjs','verify.mjs','run-course.mjs']) await cp(join(repo,'scripts/offline',file),join(kit,file))
await mkdir(join(kit,'drawings'),{recursive:true})
await mkdir(join(kit,'references'),{recursive:true})
const referencePaths = process.argv.filter(a=>a.startsWith('--reference=')).map(a=>resolve(a.slice('--reference='.length)))
const referenceNames = new Set()
for(const path of referencePaths) {
  const name=basename(path)
  if(referenceNames.has(name)) throw new Error(`Duplicate reference filename: ${name}`)
  referenceNames.add(name)
  await cp(path,join(kit,'references',name))
}
await writeFile(join(kit,'START-HERE.txt'),`PIL OFFLINE TRAVEL KIT\n\nInstall Node 24 on the destination laptop while online.\nFrom this folder: node verify.mjs, then node serve.mjs\nOpen http://127.0.0.1:4178/\n\nEditable lab: cd source/uie-practice/pil-offline\nRun npm ci ONLINE on the destination, then npm test and npm run dev.\nThe lab dev app is http://127.0.0.1:5178/\nCopied dependencies: ${includeDeps ? 'included; only reuse on matching OS/architecture' : 'not included'}.\nSource snapshot includes existing uncommitted exercise work. The parent UI repo has pre-existing TypeScript errors; use the isolated lab.\nExport every important drawing as .excalidraw into drawings/. Browser storage will not transfer.\nChosen private attachments are in references/. Add other permitted personal resources there.\nOfficial course (if included): node run-course.mjs, then http://localhost:3000/. No videos or Node installer included.\nKeep the original source repositories: this kit is a working snapshot, not Git history.\nAfter edits, verification will report modified source files; that is expected.\n`)
const files = {}
async function walk(dir) { for(const e of await readdir(dir,{withFileTypes:true})) { const p=join(dir,e.name); if(e.name==='node_modules') continue; if(e.isDirectory()) await walk(p); else if(e.isFile()) files[relative(kit,p).split('\\').join('/')] = createHash('sha256').update(await readFile(p)).digest('hex') } }
await walk(kit)
await writeFile(join(kit,'manifest.json'),JSON.stringify({created:new Date().toISOString(),platform:process.platform,arch:process.arch,node:process.version,dependenciesIncluded:includeDeps,dependencyHashesIncluded:false,files},null,2))
const archive = output+'.tar.gz'
execFileSync('tar',['-czf',archive,'-C',output,'pil-travel-kit'],{stdio:'inherit'})
console.log(`Folder: ${kit}\nArchive: ${archive}\nDependencies are excluded from integrity hashes. Private references included only when explicitly passed via --reference=PATH.`)
