import { contextBridge, ipcRenderer } from 'electron'

contextBridge.exposeInMainWorld('launcher', {
  registrar: (msg: string) => ipcRenderer.invoke('launcher:log', String(msg).slice(0, 300)),
  estado: () => ipcRenderer.invoke('launcher:estado'),
  atualizar: () => ipcRenderer.invoke('launcher:atualizar'),
  abrir: () => ipcRenderer.invoke('launcher:abrir'),
  reverter: () => ipcRenderer.invoke('launcher:reverter'),
  aoProgresso: (fn: (pct: number, etapa: string) => void) =>
    ipcRenderer.on('launcher:progresso', (_e, pct: number, etapa: string) => fn(pct, etapa))
})
