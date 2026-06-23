# `stdout`

> Um jornal semanal do mundo tech — coletado, curado e redigido automaticamente.

`stdout` é um pipeline de dados que toda semana varre as principais fontes do
mundo da tecnologia e da ciência (notícias, papers, projetos em alta), filtra o
que mais importa, e publica uma edição em formato de jornal — em português e
inglês. Sem intervenção manual: um robô faz tudo, do começo ao fim.

## Como funciona

```
┌────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌──────────┐
│ COLETA │→ │ RANKING │→ │ REDAÇÃO │→ │ REVISÃO │→ │PUBLICAÇÃO│
└────────┘  └─────────┘  └─────────┘  └─────────┘  └──────────┘
 arXiv,HN,   dedup +      IA redige    IA edita     Markdown +
 RSS,GitHub  relevância   PT + EN      p/ a voz     site (Pages)
             anti-spam                 editorial
```

A redação usa o padrão **redator → editor** (LLM-as-editor): a IA escreve o
rascunho e uma segunda passada revisa o texto contra um guia editorial — sempre
técnico, porém didático e conversando com todos. A voz fica em
[`pipeline/style.py`](pipeline/style.py), num lugar só.

## Estágio atual

- [x] **Fase 1 — Coleta.** Hacker News, arXiv, RSS (Ars Technica, The Verge, MIT Tech Review, Quanta) e GitHub — tudo sem chave.
- [x] **Fase 2 — Redação + revisão.** Ranking heurístico (sem IA) + redação e revisão por IA via Gemini (PT + EN), com fallback extrativo.
- [x] **Fase 3 — Site.** Edições viram um jornal estático em `docs/` (capa + páginas PT/EN).
- [x] **Fase 4 — Automação.** Cron semanal via GitHub Actions + publicação no GitHub Pages.

## Automação

O workflow [`.github/workflows/publish.yml`](.github/workflows/publish.yml) roda
toda segunda-feira (e pode ser disparado na mão), gera a edição da semana e dá
push da pasta `docs/` de volta ao repositório. O GitHub Pages serve esse `docs/`.

Para ativar no seu repositório:

1. **Secret:** _Settings → Secrets and variables → Actions → New repository secret_,
   nome `GEMINI_API_KEY`, valor = sua chave do Gemini.
2. **Pages:** _Settings → Pages → Build and deployment → Source: Deploy from a
   branch_, branch `main`, pasta `/docs`.
3. (Opcional) _Actions → stdout · edição semanal → Run workflow_ para gerar a
   primeira edição automática agora.

## Rodando localmente

```bash
pip install -r requirements.txt
python run.py                 # gera a edição (coleta→ranking→redação→revisão) e o site
python run.py --collect-only  # só coleta e imprime no terminal
python run.py --site-only     # reconstrói o site a partir das edições existentes
```

Para a IA redigir, copie `.env.example` para `.env` e preencha sua
`GEMINI_API_KEY` (chave grátis, sem cartão: https://aistudio.google.com/app/apikey).
Sem chave, o pipeline ainda roda em modo extrativo — nunca quebra.

### Pré-visualizar o site localmente

```bash
python -m http.server 8000 --directory docs
# abra http://localhost:8000
```

## Stack

Python · APIs públicas (arXiv, Hacker News, RSS, GitHub) · Gemini (redação) · GitHub Actions · GitHub Pages
