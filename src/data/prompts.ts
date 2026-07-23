// Single source of truth: the repo-root prompts.json (per the build spec's
// "edit prompts.json and redeploy" workflow). Imported at build time.
import raw from '../../prompts.json'
import type { PromptsFile } from '../lib/types'

// prompts.json is imported at build time and typed here.
export const data = raw as unknown as PromptsFile
export const meta = data.meta
export const prompts = data.prompts

export function promptById(id: string) {
  return prompts.find((p) => p.id === id)
}
