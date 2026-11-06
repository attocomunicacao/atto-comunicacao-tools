# Decisões de projeto

| Tema | Decisão |
|---|---|
| Plataforma | Somente Windows 10/11 x64 |
| Stack | Electron + React 19 + TypeScript (launcher e app), motor Python 3.12 (uv), referência: soul-cars-app |
| Cortes | FFmpeg direto, sem Premiere (exportação XML fica para versão futura) |
| IA | 100% local: Whisper + LLM local |
| Hardware alvo | Intel i7 com Iris Xe, sem NVIDIA: inferência em CPU (int8), processamento em segundo plano com progresso e retomada |
| Repositório | github.com/attocomunicacao/atto-comunicacao-tools (público) |
| Dicionário | Local por usuário, nunca compartilhado, gerado pelo uso |
| Licença | Todos os direitos reservados |
| Commits | Conventional Commits em português |
| Transcrição | faster-whisper `small` (int8, CPU) como padrão, com correção por dicionário do usuário e LLM local. `medium` fica como opção de alta qualidade. Ver [diário 003](diario/003-teste-whisper.md) |
