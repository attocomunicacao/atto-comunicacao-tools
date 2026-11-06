# 015 · Instalador do Launcher (2026-11-06)

```bash
npm run instalador
```
Gera `dist/launcher/ATTO-Tools-Setup-0.1.0.exe` (122 MB) com electron-builder (NSIS). Configuração: `apps/launcher/electron-builder.yml`; ícone: `apps/launcher/build/icon.png` (gerado por `scripts/gerar-icone.cjs`).

## Como o instalador se comporta
- **Por usuário, sem pedir administrador**: instala em `%LOCALAPPDATA%\Programs\atto-launcher`.
- Cria atalho **ATTO Tools** na área de trabalho e no menu Iniciar e abre o launcher ao terminar.
- Registra a desinstalação em "Aplicativos instalados". Desinstalar **mantém** `%LOCALAPPDATA%\ATTO Tools` (versões instaladas e projetos).

## Testado
Instalação silenciosa (`/S`), atalhos, entrada no registro, launcher abrindo e mostrando a release real, desinstalação silenciosa sem deixar atalhos, pasta ou registro. O teste de ponta a ponta do launcher continua passando.

## Achados importantes
1. **O Windows bloqueia o instalador sem assinatura.** Ao fim dos testes, a política de controle de aplicativos ("Smart App Control") passou a recusar a execução do `.exe` ("An Application Control policy has blocked this file"). Não foi contornado. **Assinatura de código é necessária** para distribuir o instalador (e o `ATTO Tools.exe` do pacote) a outros usuários.
2. **Download sem clique (não explicado).** Em algumas execuções do launcher instalado, a interface pediu a instalação sozinha ~1 s após abrir (o registro mostrou "atualizar/instalar solicitado pela interface" sem clique) e começou a baixar o zip de 886 MB. Não reproduziu depois, nem com diagnóstico ligado. Medidas: o launcher agora **ignora cliques que não vêm de uma ação real do usuário** (`event.isTrusted`) e grava um registro em `%APPDATA%\atto-launcher\launcher.log` com o motivo de cada ação. Os testes e2e passaram a usar cliques reais do mouse (CDP). **Se acontecer de novo, o log mostra a causa.**
3. O instalador final (com essas duas medidas) **não pôde ser executado** por causa do item 1; as medidas foram verificadas no build de desenvolvimento.
