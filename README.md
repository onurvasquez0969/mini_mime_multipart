# mini_mime_multipart

Parses RFC 2046 multipart MIME bodies into part dictionaries with headers and decoded content, using only the Python standard library.

## Usage

```python
from mini_mime_multipart import parse_multipart

content_type = 'multipart/mixed; boundary="--boundary"'
body = (
    b'----boundary\r\n'
    b'Content-Type: text/plain\r\n'
    b'\r\n'
    b'Hello\r\n'
    b'----boundary\r\n'
    b'Content-Type: application/octet-stream\r\n'
    b'\r\n'
    b'\x00\x01\x02\r\n'
    b'----boundary--\r\n'
)

parts = parse_multipart(content_type, body)
for part in parts:
    headers = dict(part['headers'])
    print(headers.get('content-type'))
    print(part['content'])
```

Each returned part is a `dict` with two keys:

- `headers`: a `list[tuple[str, str]]`, header names lower-cased, folded continuations unfolded.
- `content`: the raw `bytes` between the boundary lines.

`parse_multipart(content_type: str, body: bytes) -> list[dict]` is the only public function. `ParseError` is raised on malformed input and is a subclass of `ValueError`.

## Why this exists

The standard library's `email` package can parse multipart messages, but it is built around the full MIME object model: message trees, transfer-encoding application, and policy objects. That is more machinery than most callers need when they just want to split a body on its boundary and read each part's headers and bytes.

The deliberate trade-off: this library does **not** apply `Content-Transfer-Encoding`. The `content` bytes are the raw bytes from the body. If a part is base64-encoded, you receive the base64 bytes and decode them yourself. This keeps the library small and avoids guessing charsets or encodings it cannot reliably infer.

## Edge cases

- Header names are lower-cased. Repeated headers are preserved in order as separate tuples.
- Folded header lines (continuation lines starting with whitespace) are unfolded into the preceding header value.
- Both `\r\n` and `\n` line endings are accepted.
- The boundary value may be quoted or unquoted in the `Content-Type` string.
- A body missing the final `--boundary--` close marker is still parsed; the last part runs to the end of the body.
- Binary content (arbitrary bytes) is preserved unchanged.

## Design notes

The window stores values eagerly rather than keeping running aggregates. Running
sums drift with floating point over long streams, and recomputing from a small
buffer is cheap enough that the drift is not worth the speed.

