import sys
import os
import struct
import errno

HEADER_FORMAT = '<4s4sII4s4sII'
ENTRY_FIXED_FORMAT = '<Q Q Q Q I c'
BLOB_HEADER_FORMAT = '<4sQ'

HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
ENTRY_FIXED_SIZE = struct.calcsize(ENTRY_FIXED_FORMAT)
BLOB_HEADER_SIZE = struct.calcsize(BLOB_HEADER_FORMAT)


def bswap32(x):
    return ((x & 0xFF000000) >> 24) | \
           ((x & 0x00FF0000) >> 8) | \
           ((x & 0x0000FF00) << 8) | \
           ((x & 0x000000FF) << 24)


def bswap64(x):
    return ((x & 0xFF00000000000000) >> 56) | \
           ((x & 0x00FF000000000000) >> 40) | \
           ((x & 0x0000FF0000000000) >> 24) | \
           ((x & 0x000000FF00000000) >> 8) | \
           ((x & 0x00000000FF000000) << 8) | \
           ((x & 0x0000000000FF0000) << 24) | \
           ((x & 0x000000000000FF00) << 40) | \
           ((x & 0x00000000000000FF) << 56)


def ensure_dirs(path):
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)


def detect_file_type(data):
    if data.startswith(b'\x89PNG'):
        return "png"
    if data.startswith(b'\xFF\xD8\xFF'):
        return "jpg"
    if data.startswith(b'RIFF') and b'WEBP' in data[:16]:
        return "webp"
    if data.startswith(b'\x1A\x45\xDF\xA3'):
        return "webm"
    if data.startswith(b'\x00\x00\x00') and b'ftyp' in data[:16]:
        return "mp4"
    return None


def main():
    args = sys.argv[1:]
    source = None
    destination = None

    i = 0
    while i < len(args):
        if args[i] == "-o" and i + 1 < len(args):
            destination = args[i + 1]
            i += 2
        else:
            source = args[i]
            i += 1

    if not source:
        print("Usage: python c3extractor_fixed.py file.dat -o output_folder")
        return

    with open(source, "rb") as f:
        header = f.read(HEADER_SIZE)

        magic1, padding, unknown, unknown2, magic2, padding2, entries_size, entry_count = \
            struct.unpack(HEADER_FORMAT, header)

        if magic1 != b'c3ab' or magic2 != b'fdir':
            print("Not a Construct 3 archive")
            return

        count = bswap32(entry_count)

        print("Files:", count)

        entries = []

        for _ in range(count):
            entry_fixed = f.read(ENTRY_FIXED_SIZE)

            pad, offset, file_size, file_size_dup, pad2, char_count = \
                struct.unpack(ENTRY_FIXED_FORMAT, entry_fixed)

            offset = bswap64(offset)
            file_size = bswap64(file_size)
            file_size_dup = bswap64(file_size_dup)

            char_count = char_count[0]
            name = f.read(char_count).decode("utf-8", errors="replace")

            entries.append((name, offset, file_size))

        blob_header = f.read(BLOB_HEADER_SIZE)
        blob_start = f.tell()

        print("Blob data starts at:", blob_start)

        if destination:
            os.makedirs(destination, exist_ok=True)
            os.chdir(destination)

        extracted = 0
        corrupted = 0

        for name, offset, size in entries:
            f.seek(blob_start + offset)

            data = f.read(size)

            if len(data) != size:
                print("Corrupted:", name)
                corrupted += 1
                continue

            ensure_dirs(name)

            with open(name, "wb") as out:
                out.write(data)

            # диагностика медиа
            filetype = detect_file_type(data[:32])
            if filetype:
                pass

            extracted += 1

        print()
        print("Extraction finished")
        print("Extracted:", extracted)
        print("Corrupted:", corrupted)


if __name__ == "__main__":
    main()