import { spawn } from 'node:child_process'
import { fileURLToPath } from 'node:url'
const root = fileURLToPath(new URL('./source/pil-frontend-course/',import.meta.url))
const bun = fileURLToPath(new URL('./source/pil-frontend-course/offline-tools/node_modules/bun/bin/bun.exe',import.meta.url))
const child=spawn(bun,['server.ts'],{cwd:root,stdio:'inherit'})
child.on('error',e=>{console.error('Course runtime unavailable. Install its offline-tools and course dependencies on this laptop while online.\n'+e.message);process.exitCode=1})
child.on('exit',code=>{process.exitCode=code??1})
