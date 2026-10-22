"""Escritor de PDF incremental, sem dependências externas.

Cada página é inserida no arquivo assim que fica pronta, então o uso de
memória não cresce com o tamanho do documento. As páginas são gravadas como
imagens JPEG (filtro ``DCTDecode``), que é o formato suportado nativamente
por qualquer leitor de PDF.
"""

from __future__ import annotations

from typing import BinaryIO


class PdfWriter:
    """Monta um PDF válido (versão 1.4) com uma imagem por página."""

    def __init__(self, stream: BinaryIO) -> None:
        self._stream = stream
        self._offsets: dict[int, int] = {}
        self._kids: list[int] = []
        self._next_id = 4  # 1 = catálogo, 2 = páginas, 3 = informações
        stream.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        self._write_object(1, b"<< /Type /Catalog /Pages 2 0 R >>")
        self._write_object(
            3,
            b"<< /Producer (pdf-dark) /Creator (pdf-dark) >>",
        )

    # ------------------------------------------------------------------ #
    # API pública
    # ------------------------------------------------------------------ #
    def add_page(
        self,
        jpeg: bytes,
        pixel_width: int,
        pixel_height: int,
        width_pt: float,
        height_pt: float,
        *,
        grayscale: bool = False,
    ) -> None:
        """Adiciona uma página com a imagem JPEG ocupando toda a área."""
        if not jpeg:
            raise ValueError("imagem JPEG vazia")
        if pixel_width <= 0 or pixel_height <= 0:
            raise ValueError("dimensões da imagem inválidas")

        page_id = self._next_id
        content_id = page_id + 1
        image_id = page_id + 2
        self._next_id += 3

        color_space = b"/DeviceGray" if grayscale else b"/DeviceRGB"
        image_dict = (
            b"<< /Type /XObject /Subtype /Image"
            b" /Width " + str(pixel_width).encode() +
            b" /Height " + str(pixel_height).encode() +
            b" /ColorSpace " + color_space +
            b" /BitsPerComponent 8 /Filter /DCTDecode"
            b" /Length " + str(len(jpeg)).encode() +
            b" >>\nstream\n" + jpeg + b"\nendstream"
        )
        self._write_object(image_id, image_dict)

        content = (
            f"q {width_pt:.4f} 0 0 {height_pt:.4f} 0 0 cm /Im0 Do Q"
        ).encode()
        self._write_object(
            content_id,
            b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n"
            + content
            + b"\nendstream",
        )

        page_dict = (
            b"<< /Type /Page /Parent 2 0 R"
            b" /MediaBox [0 0 " + f"{width_pt:.4f} {height_pt:.4f}".encode() + b"]"
            b" /Resources << /XObject << /Im0 " + str(image_id).encode() + b" 0 R >> >>"
            b" /Contents " + str(content_id).encode() + b" 0 R >>"
        )
        self._write_object(page_id, page_dict)
        self._kids.append(page_id)

    def close(self) -> None:
        """Grava a árvore de páginas, a tabela xref e o trailer."""
        if not self._kids:
            raise ValueError("nenhuma página foi adicionada")

        kids = b" ".join(f"{kid} 0 R".encode() for kid in self._kids)
        pages = (
            b"<< /Type /Pages /Count " + str(len(self._kids)).encode()
            + b" /Kids [" + kids + b"] >>"
        )
        self._write_object(2, pages)

        xref_offset = self._stream.tell()
        size = self._next_id
        entries = [b"xref\n", f"0 {size}\n".encode(), b"0000000000 65535 f \n"]
        for object_id in range(1, size):
            try:
                offset = self._offsets[object_id]
            except KeyError:  # pragma: no cover - indica bug interno
                raise RuntimeError(f"objeto {object_id} não foi gravado") from None
            entries.append(f"{offset:010d} 00000 n \n".encode())
        self._stream.write(b"".join(entries))
        self._stream.write(
            f"trailer\n<< /Size {size} /Root 1 0 R /Info 3 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n".encode()
        )
        self._stream.flush()

    # ------------------------------------------------------------------ #
    # Interno
    # ------------------------------------------------------------------ #
    def _write_object(self, object_id: int, body: bytes) -> None:
        if object_id in self._offsets:  # pragma: no cover - bug interno
            raise RuntimeError(f"objeto {object_id} gravado duas vezes")
        self._offsets[object_id] = self._stream.tell()
        self._stream.write(f"{object_id} 0 obj\n".encode())
        self._stream.write(body)
        self._stream.write(b"\nendobj\n")
