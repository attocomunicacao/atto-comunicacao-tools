import '@fontsource/inter-tight/400.css'
import '@fontsource/inter-tight/500.css'
import '@fontsource/inter-tight/700.css'
import './styles.css'

interface Estado {
  instalada: string | null
  anterior: string | null
  ultima: { versao: string; notas?: string } | null
  semConexao: boolean
}
declare global {
  interface Window {
    launcher: {
      estado(): Promise<Estado>
      atualizar(): Promise<void>
      abrir(): Promise<void>
      registrar(msg: string): Promise<void>
      reverter(): Promise<void>
      aoProgresso(fn: (pct: number, etapa: string) => void): void
    }
  }
}

const $ = <T extends HTMLElement>(id: string) => document.getElementById(id) as T
const principal = $<HTMLButtonElement>('principal')
const voltar = $<HTMLButtonElement>('voltar')
let acao: () => Promise<void> = async () => {}
let baixa = false // a ação atual baixa/instala (mostra a barra)

function mostrarErro(e: unknown) {
  const el = $('erro')
  el.textContent = e instanceof Error ? e.message.replace(/^Error invoking remote method '[^']+': (Error: )?/, '') : String(e)
  el.hidden = false
}

async function atualizarTela() {
  const s = await window.launcher.estado()
  $('erro').hidden = true
  $('barra').hidden = true
  voltar.hidden = !s.anterior
  const nova = s.ultima && (!s.instalada || s.ultima.versao !== s.instalada)
  if (!s.instalada && s.ultima) {
    $('rotulo').textContent = 'Primeira instalação'
    $('titulo').textContent = `ATTO Tools ${s.ultima.versao}`
    $('detalhe').textContent = s.ultima.notas ?? 'Ferramentas para editores de vídeo, fotógrafos, designers e jornalistas.'
    principal.textContent = 'Baixar e instalar'
    acao = window.launcher.atualizar
    baixa = true
  } else if (!s.instalada) {
    $('rotulo').textContent = 'Sem conexão'
    $('titulo').textContent = 'Não foi possível verificar'
    $('detalhe').textContent = 'Conecte-se à internet para baixar o ATTO Tools.'
    principal.textContent = 'Tentar de novo'
    acao = async () => {}
    baixa = false
  } else if (nova) {
    $('rotulo').textContent = 'Atualização disponível'
    $('titulo').textContent = `Versão ${s.ultima!.versao}`
    $('detalhe').textContent = s.ultima!.notas ?? `Você está na ${s.instalada}.`
    principal.textContent = 'Atualizar'
    acao = window.launcher.atualizar
    baixa = true
  } else {
    $('rotulo').textContent = s.semConexao ? 'Sem conexão' : 'Tudo em dia'
    $('titulo').textContent = `ATTO Tools ${s.instalada}`
    $('detalhe').textContent = s.semConexao ? 'Não foi possível buscar atualizações agora.' : 'Você está na versão mais recente.'
    principal.textContent = 'Abrir'
    acao = window.launcher.abrir
    baixa = false
  }
  $('rodape').textContent = s.instalada ? `Instalada: ${s.instalada}` : ''
  principal.disabled = false
}

principal.addEventListener('click', async (ev) => {
  // Só age com uma ação real da pessoa (mouse/teclado); cliques gerados por script são ignorados.
  if (!ev.isTrusted) {
    window.launcher.registrar('clique ignorado: não veio de uma ação real do usuário')
    return
  }
  window.launcher.registrar(`clique em "${principal.textContent}" isTrusted=${ev.isTrusted} detail=${ev.detail} pointer=${(ev as PointerEvent).pointerType ?? '-'} foco=${document.hasFocus()} ativacao=${navigator.userActivation?.isActive}`)
  principal.disabled = true
  voltar.hidden = true
  try {
    if (baixa) $('barra').hidden = false
    await acao()
  } catch (e) {
    await atualizarTela().catch(() => {})
    mostrarErro(e)
    return
  }
  await atualizarTela().catch(mostrarErro)
})
voltar.addEventListener('click', async (ev) => {
  if (!ev.isTrusted) return
  try {
    await window.launcher.reverter()
  } catch (e) {
    mostrarErro(e)
  }
  await atualizarTela()
})
window.launcher.aoProgresso((pct, etapa) => {
  ;($('preenche') as HTMLElement).style.width = `${pct}%`
  $('detalhe').textContent = `${etapa}…`
})
atualizarTela().catch(mostrarErro)
