#!/usr/bin/env python3
import base64
import http.server
import secrets
import sys
import urllib.parse
import urllib.request
from urllib.parse import urljoin
import threading

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
REFERER = "https://megaplay.buzz/"


class RelayHandler(http.server.BaseHTTPRequestHandler):
    token = ""
    initial_url = ""
    timestamp_offset = None
    timestamp_lock = threading.Lock()
    initial_subtitle_url = ""

    def log_message(self, *_args):
        return

    def send_error_text(self, status, text):
        body = text.encode()
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    @classmethod
    def make_local_url(cls, upstream_url):
        encoded = base64.urlsafe_b64encode(upstream_url.encode()).decode().rstrip("=")
        return "/stream/" + cls.token + "?u=" + urllib.parse.quote(encoded, safe="")

    def local_url(self, upstream_url):
        return self.make_local_url(upstream_url)

    def upstream_url(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/stream/" + self.token:
            return None
        value = urllib.parse.parse_qs(parsed.query).get("u", [""])[0]
        if not value:
            return self.initial_url
        try:
            padded = value + "=" * (-len(value) % 4)
            return base64.urlsafe_b64decode(padded).decode()
        except (ValueError, UnicodeDecodeError):
            return None

    def fetch(self, url):
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("unsupported upstream URL")
        request = urllib.request.Request(
            url,
            headers={"User-Agent": USER_AGENT, "Referer": REFERER},
        )
        return urllib.request.urlopen(request, timeout=20).read()

    def rewrite_playlist(self, url, body):
        text = body.decode("utf-8", errors="replace")
        output = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                output.append(line)
                continue
            output.append(self.local_url(urljoin(url, stripped)))
        return ("\n".join(output) + "\n").encode()

    # Some releases put a blank line inside a cue (for example a multi-line
    # text-message sign). WebVTT ends a cue at a blank line, so parsers treat
    # the rest as garbage and stop reading the file. Fold such orphan blocks
    # back into the preceding cue.
    @staticmethod
    def sanitize_webvtt(body):
        text = body.decode("utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n")
        blocks = text.strip("\n").split("\n\n")
        output = []
        in_cue = False
        for block in blocks:
            if not block.strip():
                continue
            lines = block.strip("\n").split("\n")
            first = lines[0].strip()
            is_cue = "-->" in lines[0] or (len(lines) > 1 and "-->" in lines[1])
            is_meta = first.startswith(("WEBVTT", "NOTE", "STYLE", "REGION"))
            if is_cue:
                output.append(lines)
                in_cue = True
            elif is_meta or not in_cue:
                output.append(lines)
                in_cue = False
            else:
                output[-1].extend(lines)
        return ("\n\n".join("\n".join(lines) for lines in output) + "\n\n").encode()

    @staticmethod
    def strip_wrapper(body):
        for offset in range(0, min(512, len(body) - 564)):
            if body[offset] == 0x47 and body[offset + 188] == 0x47 and body[offset + 376] == 0x47:
                return body[offset:]
        return body

    @staticmethod
    def decode_timestamp(data):
        if len(data) < 5:
            return None
        return (
            ((data[0] >> 1) & 0x07) << 30
            | data[1] << 22
            | ((data[2] >> 1) & 0x7F) << 15
            | data[3] << 7
            | ((data[4] >> 1) & 0x7F)
        )

    @staticmethod
    def encode_timestamp(data, value):
        value = max(0, value)
        data[0] = (data[0] & 0xF0) | (((value >> 30) & 0x07) << 1) | 1
        data[1] = (value >> 22) & 0xFF
        data[2] = ((value >> 15) & 0x7F) << 1 | 1
        data[3] = (value >> 7) & 0xFF
        data[4] = (value & 0x7F) << 1 | 1

    @classmethod
    def first_pts(cls, body):
        for offset in range(0, len(body) - 187, 188):
            packet = body[offset : offset + 188]
            if packet[0] != 0x47 or not packet[1] & 0x40:
                continue
            adaptation_control = (packet[3] >> 4) & 0x03
            payload_offset = 4
            if adaptation_control in (2, 3):
                adaptation_length = packet[4]
                payload_offset += 1 + adaptation_length
            if adaptation_control not in (1, 3) or payload_offset + 14 > 188:
                continue
            payload = packet[payload_offset:]
            if payload[:3] != b"\x00\x00\x01":
                continue
            if ((payload[7] >> 6) & 0x03) in (2, 3):
                return cls.decode_timestamp(payload[9:14])
        return None

    @classmethod
    # The CDN's MPEG-TS segments can start with a non-zero PTS even though
    # the HLS playlist starts at zero. Normalize PTS/DTS/PCR for players such
    # as VLC so external WebVTT tracks share the playlist timeline.
    def normalize_transport_stream(cls, body):
        if len(body) < 188 or body[0] != 0x47:
            return body
        first_pts = cls.first_pts(body)
        if first_pts is not None:
            with cls.timestamp_lock:
                if cls.timestamp_offset is None:
                    cls.timestamp_offset = first_pts
        offset = cls.timestamp_offset
        if offset in (None, 0):
            return body

        output = bytearray(body)
        for packet_offset in range(0, len(output) - 187, 188):
            packet = output[packet_offset : packet_offset + 188]
            adaptation_control = (packet[3] >> 4) & 0x03
            payload_offset = 4
            if adaptation_control in (2, 3):
                adaptation_length = packet[4]
                if adaptation_length >= 7 and packet[5] & 0x10:
                    pcr = packet[6:12]
                    pcr_base = (
                        pcr[0] << 25
                        | pcr[1] << 17
                        | pcr[2] << 9
                        | pcr[3] << 1
                        | (pcr[4] >> 7)
                    )
                    pcr_extension = ((pcr[4] & 0x01) << 8) | pcr[5]
                    pcr_base = max(0, pcr_base - offset)
                    packet[6] = (pcr_base >> 25) & 0xFF
                    packet[7] = (pcr_base >> 17) & 0xFF
                    packet[8] = (pcr_base >> 9) & 0xFF
                    packet[9] = (pcr_base >> 1) & 0xFF
                    packet[10] = ((pcr_base & 0x01) << 7) | ((pcr_extension >> 8) & 0x01)
                    packet[11] = pcr_extension & 0xFF
                payload_offset += 1 + adaptation_length
            if adaptation_control not in (1, 3) or payload_offset + 14 > 188:
                output[packet_offset : packet_offset + 188] = packet
                continue
            payload = memoryview(packet)[payload_offset:]
            if payload[:3].tobytes() != b"\x00\x00\x01":
                output[packet_offset : packet_offset + 188] = packet
                continue
            pts_dts_flags = (payload[7] >> 6) & 0x03
            if pts_dts_flags in (2, 3):
                pts = cls.decode_timestamp(payload[9:14])
                if pts is not None:
                    cls.encode_timestamp(payload[9:14], pts - offset)
            if pts_dts_flags == 3 and len(payload) >= 19:
                dts = cls.decode_timestamp(payload[14:19])
                if dts is not None:
                    cls.encode_timestamp(payload[14:19], dts - offset)
            output[packet_offset : packet_offset + 188] = packet

        return bytes(output)

    def do_GET(self):
        url = self.upstream_url()
        if not url:
            self.send_error_text(404, "not found\n")
            return
        try:
            body = self.fetch(url)
        except Exception as error:
            self.send_error_text(502, "upstream unavailable: " + str(error) + "\n")
            return

        is_playlist = ".m3u8" in url.lower() or body.startswith(b"#EXTM3U")
        is_subtitle = ".vtt" in url.lower() or body.startswith(b"WEBVTT")
        content_type = "text/vtt; charset=utf-8" if is_subtitle else "application/vnd.apple.mpegurl" if is_playlist else "video/mp2t"
        if is_playlist:
            body = self.rewrite_playlist(url, body)
        elif is_subtitle:
            body = self.sanitize_webvtt(body)
        else:
            body = self.strip_wrapper(body)
            body = self.normalize_transport_stream(body)

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    if len(sys.argv) not in (2, 3):
        raise SystemExit("usage: yomi-relay.py VIDEO_URL [SUBTITLE_URL]")
    RelayHandler.token = secrets.token_urlsafe(18)
    RelayHandler.initial_url = sys.argv[1]
    RelayHandler.initial_subtitle_url = sys.argv[2] if len(sys.argv) == 3 else ""
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), RelayHandler)
    base_url = "http://127.0.0.1:%d" % server.server_port
    # SIGTERM uses Python's default immediate process termination. Calling
    # server.shutdown() from this signal handler would deadlock serve_forever.
    print(base_url + RelayHandler.make_local_url(RelayHandler.initial_url), flush=True)
    if RelayHandler.initial_subtitle_url:
        print(base_url + RelayHandler.make_local_url(RelayHandler.initial_subtitle_url), flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
