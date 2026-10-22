# PDF Dark

Transforme PDFs de fundo branco em documentos com **fundo escuro e texto claro**,
muito mais confortáveis para quem passa horas lendo.

O programa aceita qualquer PDF (inclusive digitalizações), aplica um tema escuro
página por página e gera um novo arquivo pronto para ler no computador, no tablet
ou no celular — sem precisar de extensões, contas ou internet.

```
livro.pdf  ──►  livro-dark.pdf
```

---

## Sumário

- [Recursos](#recursos)
- [Requisitos](#requisitos)
- [Instalação](#instalação)
- [Como usar](#como-usar)
- [Opções da linha de comando](#opções-da-linha-de-comando)
- [Gerar o executável (sem Python)](#gerar-o-executável-sem-python)
- [Como funciona](#como-funciona)
- [Limitações](#limitações)
- [Solução de problemas](#solução-de-problemas)
- [Desenvolvimento](#desenvolvimento)
- [Licença e contribuição](#licença-e-contribuição)

---

## Recursos

- **Interface gráfica simples** em Tkinter (já vem com o Python, sem dependências extras).
- **Linha de comando** para converter um arquivo, uma pasta inteira ou usar em scripts.
- **Três temas**: cinza escuro, preto puro (ideal para telas OLED) e sépia.
- **Fotos e ilustrações preservadas** nas cores originais, em vez de virarem negativos.
- **Tons de cinza por padrão**, com opção de preservar as cores de código,
  gráficos e links (`--color`).
- **Gravação incremental**: o PDF é escrito página por página, então o uso de memória
  não cresce com o tamanho do documento.
- **Ajuste de resolução e qualidade** para equilibrar nitidez e tamanho do arquivo.
- Funciona em **Windows, macOS e Linux**.

## Requisitos

- Python **3.10 ou superior** (apenas para rodar a partir do código-fonte).
- [uv](https://docs.astral.sh/uv/) para o fluxo de desenvolvimento recomendado.

> Quer usar sem instalar Python? Veja [Gerar o executável](#gerar-o-executável-sem-python).

## Instalação

### 1. Clone o repositório

```bash
git clone https://github.com/SEU-USUARIO/pdf-dark.git
cd pdf-dark
```

### 2. Crie o ambiente e instale as dependências

```bash
uv sync
```

O `uv` cria automaticamente a pasta `.venv` com o Python fixado em
[`.python-version`](.python-version) e instala o projeto em modo editável.

Se preferir ativar o ambiente manualmente:

| Sistema | Comando |
| --- | --- |
| Windows (PowerShell) | `.venv\Scripts\Activate.ps1` |
| Linux / macOS | `source .venv/bin/activate` |

### 3. Instale o comando no sistema (opcional)

Para usar `pdf-dark` de qualquer pasta, sem ativar a venv:

```bash
uv tool install .
```

Para desinstalar depois: `uv tool uninstall pdf-dark`.

## Como usar

### Interface gráfica

A forma mais simples — com duplo clique no executável ou com:

```bash
uv run pdf-dark
```

1. Clique em **Escolher…** e selecione o PDF.
2. Confira o nome do arquivo de saída (sugerido automaticamente como `nome-dark.pdf`).
3. Ajuste o tema e, se quiser, o DPI/qualidade.
4. Clique em **Converter** e aguarde a barra de progresso.
5. Ao final, o programa pergunta se deseja abrir o PDF gerado.

### Linha de comando

```bash
# Conversão simples: gera livro-dark.pdf ao lado do original
uv run pdf-dark livro.pdf

# Escolhendo o arquivo de saída e a resolução
uv run pdf-dark livro.pdf -o livro-escuro.pdf --dpi 200

# Tema sépia
uv run pdf-dark artigo.pdf --theme sepia

# Mantendo as cores de código e gráficos
uv run pdf-dark aula.pdf --color

# Convertendo todos os PDFs de uma pasta para outra pasta
uv run pdf-dark meus-pdfs/ -o convertidos/

# Arquivo menor e mais leve
uv run pdf-dark livro.pdf --dpi 120

# PDF protegido por senha
uv run pdf-dark protegido.pdf --password "minha-senha"
```

## Opções da linha de comando

| Opção | Padrão | Descrição |
| --- | --- | --- |
| `PDF...` | — | Um ou mais arquivos PDF, ou pastas contendo PDFs. |
| `-o`, `--output` | `<nome>-dark.pdf` | Arquivo de saída (um PDF) ou pasta de saída (vários PDFs). |
| `-t`, `--theme` | `dark` | `dark` (cinza), `amoled` (preto puro) ou `sepia`. |
| `-d`, `--dpi` | `150` | Resolução da página, de 72 a 600. Maior = mais nítido e mais pesado. |
| `-q`, `--quality` | `85` | Qualidade JPEG, de 40 a 100. |
| `-c`, `--contrast` | `1.0` | Realce do contraste do texto (ex.: `1.2`). |
| `--color` / `--no-color` | desligado | Mantém o matiz de código/gráficos (`--color`) ou usa tons de cinza. |
| `--keep-images` / `--no-keep-images` | ligado | Preserva fotos nas cores originais ou escurece tudo. |
| `--password` | — | Senha, se o PDF estiver protegido. |
| `-f`, `--overwrite` | desligado | Sobrescreve a saída existente. |
| `--open` | desligado | Abre o PDF gerado ao terminar. |
| `--gui` | desligado | Abre a interface gráfica. |
| `--version` | — | Mostra a versão. |

### Escolhendo a resolução

| Uso | `--dpi` sugerido | Comentário |
| --- | --- | --- |
| Leitura casual em tela | `120` | Arquivos bem menores. |
| Equilíbrio (padrão) | `150` | Bom para a maioria dos documentos. |
| Texto pequeno ou zoom | `200`–`300` | Mais nítido, arquivo maior. |

## Gerar o executável (sem Python)

O executável é gerado com [PyInstaller](https://pyinstaller.org/) e roda em
computadores que **não têm Python instalado**.

```bash
uv run python scripts/build.py
```

O arquivo final fica em `dist/` (`pdf-dark.exe` no Windows, `pdf-dark` no
Linux/macOS). Basta copiar esse único arquivo para a outra máquina.

- Ao abrir com duplo clique (sem argumentos), a interface gráfica inicia e o
  console do Windows é escondido automaticamente.
- Chamado pelo terminal com argumentos, funciona como a CLI normal.
- O executável precisa ser gerado **no sistema operacional de destino**:
  Windows gera `.exe`, Linux gera binário Linux, e assim por diante.
  Se você publicar releases no GitHub, o workflow
  [`.github/workflows/build.yml`](.github/workflows/build.yml) compila os três
  sistemas automaticamente.

Para regerar o ícone do aplicativo (opcional):

```bash
uv run python scripts/make_icon.py
```

## Como funciona

1. Cada página é rasterizada com o **PDFium** (o mesmo motor do Chrome) na
   resolução escolhida.
2. A página é tratada como um mapa de tinta: papel branco vira o fundo do tema e
   texto preto vira a cor de frente clara, preservando o antisserrilhado das letras.
3. Por padrão o resultado fica em tons de cinza; com `--color`, a luminosidade
   é invertida no espaço de cor Lab e o matiz original é mantido (útil para
   código e gráficos).
4. Regiões de imagem são recortadas do original e coladas por cima, evitando fotos
   com aspecto de negativo. Páginas digitalizadas (uma imagem ocupando a página
   inteira) são escurecidas normalmente.
5. O PDF de saída é escrito **incrementalmente** como JPEG por página, usando um
   escritor próprio — sem depender de bibliotecas pesadas de PDF e com memória
   constante.

```
src/pdf_dark/
├── converter.py   # orquestra leitura, renderização e gravação
├── theme.py       # temas e curva de tons (papel/tinta)
├── pdfwriter.py   # escritor de PDF incremental
├── cli.py         # interface de linha de comando
├── gui.py         # interface gráfica em Tkinter
└── assets/        # ícone do aplicativo
```

## Limitações

- **O PDF gerado é composto por imagens.** O texto continua nítido e legível, mas
  não é mais selecionável, pesquisável ou copiável, e leitores de tela não
  conseguem extraí-lo. Guarde sempre o arquivo original.
- O tamanho do arquivo cresce com a resolução: um livro de 300 páginas em 150 DPI
  costuma ficar entre 30 MB e 120 MB. Para reduzir, use `--dpi 120`.
- PDFs que já têm fundo escuro podem ficar estranhos (o programa assume fundo
  branco). Nesse caso, use o original.

## Solução de problemas

| Problema | Solução |
| --- | --- |
| `não foi possível abrir ...` | O arquivo pode estar corrompido ou protegido. Tente `--password`. |
| Conversão muito lenta | Reduza `--dpi` (cada página é rasterizada). |
| Arquivo muito grande | Use `--dpi 120` e reduza `--quality`. |
| Texto serrilhado | Aumente `--dpi` para 200 ou mais. |
| Fotos ficaram escuras | Elas são vetoriais ou parte de uma página digitalizada; não há como preservar só a foto. |
| Acentos estranhos no terminal | Use o Windows Terminal ou `chcp 65001`. |
| `UnicodeDecodeError` ao rodar `uv run` no Windows | A pasta do projeto tem acentos e o Python é anterior ao 3.13. Mova o projeto para um caminho sem acentos ou use o Python 3.13+. |

## Desenvolvimento

```bash
uv sync                 # instala tudo, inclusive as ferramentas de dev
uv run pytest           # roda os testes
uv run python -m pdf_dark --help
```

Os testes geram PDFs temporários com o Pillow, então não é necessário nenhum
arquivo externo.

## Licença e contribuição

Este projeto é distribuído sob a **GNU General Public License v3.0 ou posterior**
(GPL-3.0-or-later). Veja o arquivo [`LICENSE`](LICENSE).

Em resumo: você pode usar, estudar, modificar e redistribuir o programa, desde que
mantenha a mesma licença e disponibilize o código-fonte. Não há garantias.

Contribuições são muito bem-vindas! Leia o
[`CONTRIBUTING.md`](CONTRIBUTING.md) para saber como propor melhorias, relatar
problemas e enviar *pull requests*.
