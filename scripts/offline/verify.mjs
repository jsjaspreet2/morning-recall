import { readFile } from 'node:fs/promises'
import { createHash } from 'node:crypto'
const manifest = JSON.parse(await readFile(new URL('manifest.json',import.meta.url),'utf8'))
let failures = 0
for (const [path,expected] of Object.entries(manifest.files)) {
  try { const actual = createHash('sha256').update(await readFile(new URL(path,import.meta.url))).digest('hex'); if (actual !== expected) throw new Error('checksum differs') }
  catch(e) { console.error(path+': '+e.message); failures++ }
}
console.log(`${Object.keys(manifest.files).length} files checked; ${failures} failures. Built on ${manifest.platform}/${manifest.arch}, Node ${manifest.node}.`)
console.log('Checksums verify the original transfer. Your later source edits will correctly change their hashes.')
process.exitCode = failures ? 1 : 0
