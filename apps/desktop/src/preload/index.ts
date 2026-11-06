import { contextBridge, ipcRenderer } from 'electron'

const api = {
  escolherVideo: (): Promise<string | null> => ipcRenderer.invoke('video:escolher'),
  criarProjeto: (video: string): Promise<string> => ipcRenderer.invoke('projeto:criar', video),
  motor: (cmd: string, args: string[]): Promise<{ codigo: number; erro: string }> =>
    ipcRenderer.invoke('motor:executar', cmd, args),
  aoLinha: (fn: (linha: string) => void): (() => void) => {
    const h = (_e: unknown, l: string) => fn(l)
    ipcRenderer.on('motor:linha', h)
    return () => ipcRenderer.removeListener('motor:linha', h)
  },
  lerJson: <T = unknown>(pasta: string, nome: string): Promise<T> => ipcRenderer.invoke('arquivo:json', pasta, nome),
  lerBytes: (pasta: string, sub: string, nome: string): Promise<Uint8Array> =>
    ipcRenderer.invoke('arquivo:bytes', pasta, sub, nome),
  versao: (): Promise<string> => ipcRenderer.invoke('app:versao'),
  logoAtual: (): Promise<string | null> => ipcRenderer.invoke('logo:atual'),
  logoBytes: (): Promise<Uint8Array | null> => ipcRenderer.invoke('logo:bytes'),
  escolherLogo: (): Promise<string | null> => ipcRenderer.invoke('logo:escolher'),
  removerLogo: (): Promise<void> => ipcRenderer.invoke('logo:remover'),
  mostrarNaPasta: (caminho: string): Promise<void> => ipcRenderer.invoke('pasta:mostrar', caminho)
}

contextBridge.exposeInMainWorld('atto', api)
export type AttoApi = typeof api
