# Como contribuir

Obrigado pelo interesse em melhorar o PDF Dark! Este projeto é livre (GPL-3.0-or-later)
e toda contribuição — código, documentação, tradução ou relato de problema — é bem-vinda.

## Antes de começar

- Verifique se já existe uma *issue* sobre o assunto.
- Para mudanças grandes, abra uma *issue* descrevendo a proposta antes de escrever código.
- Seja gentil e objetivo nas discussões.

## Preparando o ambiente

```bash
git clone https://github.com/irlansouza93/pdf-dark.git
cd pdf-dark
uv sync
```

O `uv` cria a `.venv`, instala as dependências de execução e as de desenvolvimento
(`pytest` e `pyinstaller`).

## Fluxo de trabalho

1. Crie uma branch a partir de `main`:

   ```bash
   git switch -c feature/minha-melhoria
   ```

2. Faça a alteração em `src/pdf_dark/` (ou na documentação).
3. Rode os testes e confira o estilo do código:

   ```bash
   uv run pytest
   ```

4. Teste manualmente com um PDF real:

   ```bash
   uv run pdf-dark seu-teste.pdf --dpi 100
   uv run pdf-dark --view seu-teste.pdf   # aplicativo de leitura
   ```

5. Faça o commit com uma mensagem clara, no imperativo:

   ```
   adiciona tema de alto contraste
   corrige cálculo de recorte em páginas rotacionadas
   ```

6. Envie a branch e abra um *pull request* explicando o que mudou e por quê.

## Padrões do projeto

- Python 3.10+, com `from __future__ import annotations`.
- Código e comentários em português (o público-alvo é lusófono).
- Nomes de funções e variáveis em inglês, como no restante do código.
- Sem dependências novas sem justificativa — o objetivo é manter o programa leve.
- Toda função pública deve ter *docstring*.
- Prefira mudanças pequenas e focadas.

## Adicionando um tema

1. Adicione uma entrada em `THEMES` em `src/pdf_dark/theme.py`:

   ```python
   "contraste": Theme(
       key="contraste",
       label="Alto contraste",
       background=(0, 0, 0),
       foreground=(255, 255, 255),
   ),
   ```

2. A CLI e o aplicativo passam a listar o tema automaticamente.
3. Adicione um teste em `tests/test_converter.py` verificando as cores geradas.

## Relatando problemas

Inclua no relato:

- sistema operacional e versão do Python (se estiver rodando pelo código);
- o comando utilizado (ou os ajustes escolhidos na interface);
- o que era esperado e o que aconteceu;
- se possível, um PDF de exemplo ou uma página que reproduza o problema.

## Licença das contribuições

Ao enviar um *pull request*, você concorda em licenciar sua contribuição sob a
mesma licença do projeto (GPL-3.0-or-later).
