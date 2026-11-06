"""Testa correção de transcrição com LLM local (Ollama). Uso: bench_llm.py <txt> <modelo>"""
import json, sys, time, urllib.request

txt, model = sys.argv[1], sys.argv[2]
trecho = open(txt, encoding="utf-8").read()[:1800]
prompt = (
    "Você revisa transcrições automáticas em português do Brasil. Dicionário de termos corretos: "
    "SINDEPRESTEM (sindicato). Corrija erros de grafia e nomes, sem reescrever o conteúdo. "
    "Depois liste em 'DÚVIDAS' cada trecho que você alterou ou não tem certeza, no formato 'original -> sugestão'.\n\n"
    f"TEXTO:\n{trecho}"
)
body = json.dumps({"model": model, "prompt": prompt, "stream": False, "options": {"temperature": 0.1}}).encode()
t0 = time.time()
r = json.load(urllib.request.urlopen(urllib.request.Request("http://localhost:11434/api/generate", body, {"Content-Type": "application/json"}), timeout=1800))
print(f"modelo={model} tempo={time.time()-t0:.0f}s tokens_saida={r.get('eval_count')} entrada={len(trecho)} caracteres")
print(r["response"])
