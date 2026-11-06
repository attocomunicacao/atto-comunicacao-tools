/// <reference types="vite/client" />
import type { AttoApi } from '../../preload'

declare global {
  interface Window {
    atto: AttoApi
  }
}
