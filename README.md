# `stdout`

> Um jornal diário do mundo tech — coletado, curado e redigido automaticamente.

### 🌐 Leia o jornal ao vivo → **[matpasquali.github.io/stdout](https://matpasquali.github.io/stdout/)**

`stdout` é um pipeline de dados que todo dia varre as principais fontes do
mundo da tecnologia e da ciência (notícias, papers, projetos em alta), filtra o
que mais importa, e publica uma edição em formato de jornal — em português e
inglês. Sem intervenção manual: um robô faz tudo, do começo ao fim.

## Como funciona

```
┌────────┐  ┌─────────┐  ┌─────────┐  ┌──────────┐
│ COLETA │→ │ RANKING │→ │ REDAÇÃO │→ │PUBLICAÇÃO│
└────────┘  └─────────┘  └─────────┘  └──────────┘
 arXiv, HN,  dedup,       IA redige    site (Pages)
 RSS, GH,    relevância,  e revisa     + Markdown
 HuggingFace anti-spam,   PT + EN
             categoriza
```

A redação é um único passo de IA que **redige e se auto-revisa** contra um guia
editorial: sempre técnico, porém didático e conversando com todos. A voz fica em
[`pipeline/style.py`](pipeline/style.py), num lugar só. As matérias são
organizadas em seções temáticas (IA, Indústria, Mercado de Trabalho, Ciência &
Papers, Projetos) e cada edição fecha com uma seção de **Referências**,
creditando a fonte e a origem de tudo.

## Estágio atual

- [x] **Fase 1 — Coleta.** Hacker News, arXiv, GitHub, Hugging Face (modelos) e RSS (tech, ciência, Brasil e carreira) — tudo sem chave.
- [x] **Fase 2 — Redação.** Ranking heurístico (sem IA) + redação por IA que se auto-revisa (Groq, com Gemini de fallback), em PT + EN, com modo extrativo de segurança.
- [x] **Fase 3 — Site.** Edições viram um jornal estático em `docs/` (capa + páginas PT/EN).
- [x] **Fase 4 — Automação.** Cron diário via GitHub Actions + publicação no GitHub Pages.

## Automação

O workflow [`.github/workflows/publish.yml`](.github/workflows/publish.yml) roda
todo dia (e pode ser disparado na mão), gera a edição do dia e dá
push da pasta `docs/` de volta ao repositório. O GitHub Pages serve esse `docs/`.

Para ativar no seu repositório:

1. **Secret:** _Settings → Secrets and variables → Actions → New repository secret_,
   nome `GROQ_API_KEY`, valor = sua chave do Groq (grátis, sem cartão:
   https://console.groq.com/keys). Opcionalmente, `GEMINI_API_KEY` como fallback.
2. **Pages:** _Settings → Pages → Build and deployment → Source: Deploy from a
   branch_, branch `main`, pasta `/docs`.
3. (Opcional) _Actions → stdout · edição diária → Run workflow_ para gerar a
   primeira edição automática agora.

## Rodando localmente

```bash
pip install -r requirements.txt
python run.py                 # gera a edição (coleta→ranking→redação) e o site
python run.py --collect-only  # só coleta e imprime no terminal
python run.py --site-only     # reconstrói o site a partir das edições existentes
```

Para a IA redigir, copie `.env.example` para `.env` e preencha sua
`GROQ_API_KEY` (chave grátis, sem cartão: https://console.groq.com/keys). O Gemini
serve de fallback via `GEMINI_API_KEY`. Sem chave, o pipeline ainda roda em modo
extrativo, nunca quebra.

### Pré-visualizar o site localmente

```bash
python -m http.server 8000 --directory docs
# abra http://localhost:8000
```

## Stack

Python · APIs públicas (arXiv, Hacker News, GitHub, Hugging Face, RSS) · IA grátis (Groq, com Gemini de fallback) · GitHub Actions · GitHub Pages
