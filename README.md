# PDF Dark

Um aplicativo de leitura em **modo escuro** para PDFs, com canvas próprio,
alternância ao vivo entre claro e escuro e uma ferramenta integrada para exportar
o documento com o tema aplicado.

O programa aceita qualquer PDF (inclusive digitalizações), aplica um tema escuro
página por página e gera um novo arquivo pronto para ler no computador, no tablet
ou no celular — sem extensões, contas ou internet.

```
livro.pdf  ──►  leitor escuro  ──►  livro-dark.pdf
```

---

## Sumário

- [Recursos](#recursos)
- [Requisitos](#requisitos)
- [Instalação](#instalação)
- [Como usar](#como-usar)
- [Atalhos do leitor](#atalhos-do-leitor)
- [Opções da linha de comando](#opções-da-linha-de-comando)
- [Gerar o executável (sem Python)](#gerar-o-executável-sem-python)
- [Como funciona](#como-funciona)
- [Limitações](#limitações)
- [Solução de problemas](#solução-de-problemas)
- [Desenvolvimento](#desenvolvimento)
- [Licença e contribuição](#licença-e-contribuição)

---

## Recursos

- **Leitor embutido** com canvas próprio: rolagem contínua, zoom, ajuste à largura
  e modo imersivo em tela cheia (F11), com barra flutuante que se esconde sozinha.
- **Barra de ferramentas ocultável (F10)**: esconda a barra do aplicativo para ler
  sem distrações; as bordas normais da janela continuam disponíveis.
- **Alternância ao vivo** entre o PDF original e o modo escuro, sem reabrir o arquivo.
- **Interface escura e minimalista**, com barras discretas e sem distrações.
- **Conversão integrada**: um painel lateral exporta o PDF com o tema escolhido,
  reaproveitando exatamente a mesma renderização do leitor.
- **Três temas**: cinza escuro, preto puro (ideal para telas OLED) e sépia.
- **Fotos e ilustrações preservadas** nas cores originais, em vez de virarem negativos.
- **Tons de cinza por padrão**, com opção de preservar as cores de código,
  gráficos e links (`--color`).
- **Linha de comando** para converter um arquivo, uma pasta inteira ou usar em scripts.
- **Gravação incremental**: o PDF é escrito página por página, então o uso de memória
  não cresce com o tamanho do documento.
- Funciona em **Windows, macOS e Linux**.

## Requisitos

- Python **3.10 ou superior** (apenas para rodar a partir do código-fonte).
- [uv](https://docs.astral.sh/uv/) para o fluxo de desenvolvimento recomendado.

> Quer usar sem instalar Python? Veja [Gerar o executável](#gerar-o-executável-sem-python).

## Instalação

### 1. Clone o repositório

```bash
git clone https://github.com/irlansouza93/pdf-dark.git
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

### Abrir o aplicativo de leitura

```bash
uv run pdf-dark                    # tela inicial
uv run pdf-dark --view livro.pdf   # já abre o livro
```

Na tela inicial, clique em **Abrir um PDF** (ou use `Ctrl+O`). O documento já
aparece em modo escuro; a barra superior concentra o essencial:

- **● Escuro / ○ Claro** alterna o documento ao vivo (`D`).
- **− 100% +** controla o zoom e **Ajustar** volta a página à largura da janela.
- **Converter** abre o painel de exportação.
- **⌃** esconde a barra de ferramentas do aplicativo (`F10`); use `F10` novamente
  para mostrá-la.
- **⛶** entra no modo imersivo (`F11`), com a barra flutuante que aparece ao mover
  o mouse e se esconde após alguns segundos.
- Arraste a página com o mouse para navegar quando estiver com zoom; a roda rola e
  `Ctrl` + roda amplia.

A janela pode ser reduzida até **560 × 380**. Em janelas estreitas, o cabeçalho
esconde automaticamente o nome do arquivo, o botão **Ajustar** e o indicador de
página para manter os controles essenciais visíveis.

### Ocultar a barra de ferramentas

Pressione `F10` (ou clique em **⌃** no canto direito da barra) para esconder a barra
do aplicativo e deixar só o documento. A janela continua com as bordas e os botões
normais do sistema, então pode ser movida, minimizada e fechada como qualquer outra.

Para trazer a barra de volta, pressione `F10` novamente. A escolha se mantém ao
trocar de página, de tema ou de arquivo.

### Converter para um arquivo escuro

1. Abra o PDF no leitor.
2. Clique em **Converter**.
3. Escolha o tema, a resolução e a qualidade. As mudanças de tema são aplicadas
   na hora no leitor, como prévia.
4. Clique em **Converter agora**. O arquivo `nome-dark.pdf` é criado ao lado do
   original.
5. Ao terminar, use **Abrir arquivo** ou **Mostrar na pasta**.

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

## Atalhos do leitor

| Atalho | Ação |
| --- | --- |
| `Ctrl+O` | Abrir um PDF |
| `D` | Alternar entre claro e escuro |
| `F10` | Ocultar ou mostrar a barra de ferramentas do aplicativo |
| `F11` | Entrar ou sair do modo imersivo |
| `Esc` | Fechar o painel de conversão ou sair da tela cheia |
| `Ctrl` `+` / `Ctrl` `-` | Aumentar ou diminuir o zoom |
| `Ctrl+0` | Ajustar à largura |
| `PgUp` / `PgDn`, `←` / `→`, `Espaço` | Página anterior / próxima |
| `Home` / `End` | Primeira / última página |
| Roda do mouse | Rolar |
| `Ctrl` + roda | Ampliar na posição |
| Arrastar com o mouse | Navegar com zoom aplicado |

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
| `--password` | — | Senha, se o PDF estiver protegido (apenas na CLI). |
| `-f`, `--overwrite` | desligado | Sobrescreve a saída existente. |
| `--open` | desligado | Abre o PDF gerado ao terminar. |
| `--view` | desligado | Abre o aplicativo de leitura com o PDF informado. |
| `--gui` | desligado | Abre o aplicativo de leitura (equivalente a rodar sem argumentos). |
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

- Ao abrir com duplo clique (sem argumentos), o aplicativo inicia e o console do
  Windows é escondido automaticamente.
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

### Conversão

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

### Leitor

O leitor usa a mesma função de renderização da conversão. As páginas visíveis
são rasterizadas em uma **thread separada** (a interface nunca trava), com cache
das últimas 10 páginas e limite de 300 DPI — acima disso, a imagem é ampliada.
Ao alternar o tema, só as páginas na tela são processadas novamente.

```
src/pdf_dark/
├── app.py         # janela principal, tela inicial e painel de conversão
├── viewer.py      # canvas do leitor: rolagem, zoom e renderização assíncrona
├── widgets.py     # paleta e componentes da interface escura
├── converter.py   # orquestra leitura, renderização e gravação
├── theme.py       # temas e curva de tons (papel/tinta)
├── pdfwriter.py   # escritor de PDF incremental
├── cli.py         # interface de linha de comando
└── assets/        # ícone do aplicativo
```

## Limitações

- **O PDF gerado é composto por imagens.** O texto continua nítido e legível, mas
  não é mais selecionável, pesquisável ou copiável, e leitores de tela não
  conseguem extraí-lo. Guarde sempre o arquivo original.
- **O leitor exibe as páginas como imagens.** Assim como no arquivo gerado, não é
  possível selecionar texto nem buscar palavras dentro do aplicativo.
- **PDFs protegidos por senha** não abrem no leitor; use a CLI com `--password`
  para gerar a versão escura.
- O tamanho do arquivo gerado cresce com a resolução: um livro de 300 páginas em
  150 DPI costuma ficar entre 30 MB e 120 MB. Para reduzir, use `--dpi 120`.
- PDFs que já têm fundo escuro podem ficar estranhos (o programa assume fundo
  branco). Nesse caso, use o original.

## Solução de problemas

| Problema | Solução |
| --- | --- |
| `não foi possível abrir ...` | O arquivo pode estar corrompido ou protegido. Na CLI, tente `--password`. |
| A página demora a aparecer | O zoom está alto ou o PDF tem páginas pesadas; aguarde ou use `Ctrl+0`. |
| Conversão muito lenta | Reduza `--dpi` (cada página é rasterizada). |
| Arquivo muito grande | Use `--dpi 120` e reduza `--quality`. |
| Texto serrilhado | Aumente `--dpi` para 200 ou mais. |
| Fotos ficaram escuras | Elas são vetoriais ou parte de uma página digitalizada; não há como preservar só a foto. |
| O cabeçalho perdeu botões | A janela está estreita: aumente-a para mostrar todos os controles. |
| Acentos estranhos no terminal | Use o Windows Terminal ou `chcp 65001`. |
| `UnicodeDecodeError` ao rodar `uv run` no Windows | A pasta do projeto tem acentos e o Python é anterior ao 3.13. Mova o projeto para um caminho sem acentos ou use o Python 3.13+. |

## Desenvolvimento

```bash
uv sync                 # instala tudo, inclusive as ferramentas de dev
uv run pytest           # roda os testes
uv run pdf-dark          # abre o aplicativo
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
