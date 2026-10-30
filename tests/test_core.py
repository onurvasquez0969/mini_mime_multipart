import unittest

from mini_mime_multipart import parse_multipart, ParseError


class TestParseMultipart(unittest.TestCase):
    def _wrap(self, boundary, parts):
        out = bytearray()
        for headers, content in parts:
            out += b"--" + boundary + b"\r\n"
            for name, value in headers:
                out += name.encode() + b": " + value.encode() + b"\r\n"
            out += b"\r\n"
            out += content
            out += b"\r\n"
        out += b"--" + boundary + b"--\r\n"
        return bytes(out)

    def test_basic_two_parts(self):
        body = self._wrap(b"BOUND", [
            ([("Content-Type", "text/plain")], b"hello"),
            ([("Content-Type", "text/html")], b"<p>hi</p>"),
        ])
        ct = 'multipart/mixed; boundary=BOUND'
        parts = parse_multipart(ct, body)
        self.assertEqual(len(parts), 2)
        self.assertEqual(parts[0]["headers"], [("content-type", "text/plain")])
        self.assertEqual(parts[0]["content"], b"hello")
        self.assertEqual(parts[1]["headers"], [("content-type", "text/html")])
        self.assertEqual(parts[1]["content"], b"<p>hi</p>")

    def test_quoted_boundary(self):
        body = self._wrap(b'a-bound', [([], b'data')])
        ct = 'multipart/mixed; boundary="a-bound"'
        parts = parse_multipart(ct, body)
        self.assertEqual(len(parts), 1)
        self.assertEqual(parts[0]["content"], b'data')
        self.assertEqual(parts[0]["headers"], [])

    def test_missing_boundary_param_raises(self):
        with self.assertRaises(ParseError):
            parse_multipart('multipart/mixed', b'--x\r\n\r\n--x--')

    def test_no_delimiter_raises(self):
        with self.assertRaises(ParseError):
            parse_multipart('multipart/mixed; boundary=x', b'just text')

    def test_content_not_bytes_raises(self):
        with self.assertRaises(TypeError):
            parse_multipart('multipart/mixed; boundary=x', 'not bytes')

    def test_content_type_not_str_raises(self):
        with self.assertRaises(TypeError):
            parse_multipart(b'boundary=x', b'--x\r\n\r\n--x--')

    def test_no_headers_part(self):
        body = b'--b\r\n\r\nbody-only\r\n--b--\r\n'
        parts = parse_multipart('multipart/mixed; boundary=b', body)
        self.assertEqual(len(parts), 1)
        self.assertEqual(parts[0]["headers"], [])
        self.assertEqual(parts[0]["content"], b'body-only')

    def test_no_body_part(self):
        body = b'--b\r\nContent-ID: 1\r\n\r\n\r\n--b--\r\n'
        parts = parse_multipart('multipart/mixed; boundary=b', body)
        self.assertEqual(len(parts), 1)
        self.assertEqual(parts[0]["headers"], [("content-id", "1")])
        self.assertEqual(parts[0]["content"], b'')

    def test_lf_only_line_endings(self):
        body = b'--b\nContent-Type: text/plain\n\nhello\n--b--\n'
        parts = parse_multipart('multipart/mixed; boundary=b', body)
        self.assertEqual(parts[0]["headers"], [("content-type", "text/plain")])
        self.assertEqual(parts[0]["content"], b'hello')

    def test_folded_header(self):
        body = (
            b'--b\r\n'
            b'X-Long: part1\r\n part2\r\n'
            b'\r\n'
            b'content\r\n'
            b'--b--\r\n'
        )
        parts = parse_multipart('multipart/mixed; boundary=b', body)
        self.assertEqual(parts[0]["headers"], [("x-long", "part1 part2")])

    def test_repeated_headers_preserved(self):
        body = (
            b'--b\r\n'
            b'Received: a\r\n'
            b'Received: b\r\n'
            b'\r\n'
            b'x\r\n'
            b'--b--\r\n'
        )
        parts = parse_multipart('multipart/mixed; boundary=b', body)
        self.assertEqual(
            parts[0]["headers"],
            [("received", "a"), ("received", "b")],
        )

    def test_header_names_lowercased(self):
        body = b'--b\r\nContent-Type: text/plain\r\n\r\nx\r\n--b--\r\n'
        parts = parse_multipart('multipart/mixed; boundary=b', body)
        self.assertEqual(parts[0]["headers"][0][0], "content-type")

    def test_empty_boundary_raises(self):
        with self.assertRaises(ParseError):
            parse_multipart('multipart/mixed; boundary=""', b'--\r\n\r\n----')

    def test_boundary_with_special_chars(self):
        b = b'==some/weird-boundary=='
        body = self._wrap(b, [([("X-A", "1")], b'payload')])
        ct = 'multipart/mixed; boundary="==some/weird-boundary=="'
        parts = parse_multipart(ct, body)
        self.assertEqual(parts[0]["content"], b'payload')

    def test_binary_content_preserved(self):
        payload = bytes(range(256))
        body = self._wrap(b'bb', [([], payload)])
        parts = parse_multipart('multipart/mixed; boundary=bb', body)
        self.assertEqual(parts[0]["content"], payload)

    def test_three_parts(self):
        body = self._wrap(b'm', [
            ([], b'one'),
            ([], b'two'),
            ([], b'three'),
        ])
        parts = parse_multipart('multipart/mixed; boundary=m', body)
        self.assertEqual([p["content"] for p in parts], [b'one', b'two', b'three'])

    def test_parse_error_is_value_error(self):
        try:
            parse_multipart('multipart/mixed', b'')
        except ValueError:
            pass
        else:
            self.fail("ParseError should be a ValueError subclass")


if __name__ == "__main__":
    unittest.main()
