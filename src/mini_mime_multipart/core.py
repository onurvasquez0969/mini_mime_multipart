# Minimal RFC 2046 multipart MIME body parser.

import re


class ParseError(ValueError):
    pass


def _find_boundary(content_type: str) -> bytes:
    if content_type is None:
        raise ParseError("Content-Type is None; cannot determine boundary")
    for piece in content_type.split(";"):
        piece = piece.strip()
        if not piece or "=" not in piece:
            continue
        name, _, raw_value = piece.partition("=")
        if name.strip().lower() != "boundary":
            continue
        value = raw_value.strip()
        if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
            value = value[1:-1]
        if value == "":
            raise ParseError("boundary parameter is empty")
        return value.encode("ascii", errors="replace")
    raise ParseError("no boundary parameter found in Content-Type")


def _parse_headers(raw_headers: bytes) -> list:
    if raw_headers == b"":
        return []
    text = raw_headers.decode("latin-1").replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    unfolded = []
    for line in lines:
        if line == "":
            continue
        if line[0] in " \t" and unfolded:
            unfolded[-1] = unfolded[-1] + " " + line.strip()
        else:
            unfolded.append(line)
    headers = []
    for line in unfolded:
        if ":" not in line:
            continue
        name, _, value = line.partition(":")
        headers.append((name.strip().lower(), value.strip()))
    return headers


def _build_boundary_regex(boundary: bytes):
    return re.compile(rb"(?m)^--" + re.escape(boundary))


def parse_multipart(content_type, body):
    if not isinstance(body, (bytes, bytearray)):
        raise TypeError("body must be bytes")
    if not isinstance(content_type, str):
        raise TypeError("content_type must be str")
    body_bytes = bytes(body)
    boundary = _find_boundary(content_type)
    delimiter = b"--" + boundary
    delim_re = _build_boundary_regex(boundary)
    matches = list(delim_re.finditer(body_bytes))
    positions = [m.start() for m in matches]
    if not positions:
        raise ParseError("boundary delimiter not found in body")
    parts = []
    for i, pos in enumerate(positions):
        after_delim = pos + len(delimiter)
        if body_bytes[after_delim:after_delim + 2] == b"--":
            break
        if i + 1 < len(positions):
            part_end = positions[i + 1]
        else:
            part_end = len(body_bytes)
        content_start = after_delim
        if body_bytes[content_start:content_start + 2] == b"\r\n":
            content_start += 2
        elif body_bytes[content_start:content_start + 1] == b"\n":
            content_start += 1
        part_block = body_bytes[content_start:part_end]
        if part_block.endswith(b"\r\n"):
            part_block = part_block[:-2]
        elif part_block.endswith(b"\n"):
            part_block = part_block[:-1]
        if part_block.startswith(b"\r\n"):
            raw_headers = b""
            part_content = part_block[2:]
        elif part_block.startswith(b"\n"):
            raw_headers = b""
            part_content = part_block[1:]
        else:
            header_end = -1
            header_sep_len = 0
            for sep in (b"\r\n\r\n", b"\n\n"):
                idx = part_block.find(sep)
                if idx != -1 and (header_end == -1 or idx < header_end):
                    header_end = idx
                    header_sep_len = len(sep)
            if header_end == -1:
                raw_headers = part_block
                part_content = b""
            else:
                raw_headers = part_block[:header_end]
                part_content = part_block[header_end + header_sep_len:]
        headers = _parse_headers(raw_headers)
        parts.append({"headers": headers, "content": part_content})
    return parts
