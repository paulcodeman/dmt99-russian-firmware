"""Strict IPS encoder/application, bounded to the DMT99 application file region."""
MAX_IMAGE = 0x30000 - 0x6400

def encode(original, modified):
    if len(modified) < len(original) or len(modified) > MAX_IMAGE:
        raise ValueError('Unsupported output length')
    patch = bytearray(b'PATCH')
    cursor = 0
    while cursor < len(modified):
        if cursor < len(original) and original[cursor] == modified[cursor]:
            cursor += 1
            continue
        start = cursor
        cursor += 1
        while cursor < len(modified) and cursor-start < 65535:
            if cursor < len(original) and original[cursor] == modified[cursor]:
                break
            cursor += 1
        data = modified[start:cursor]
        patch.extend(start.to_bytes(3, 'big'))
        patch.extend(len(data).to_bytes(2, 'big'))
        patch.extend(data)
    patch.extend(b'EOF')
    return bytes(patch)

def apply(original, patch):
    if not patch.startswith(b'PATCH'):
        raise ValueError('Bad IPS header')
    output = bytearray(original)
    cursor = 5
    while True:
        if cursor + 3 > len(patch):
            raise ValueError('Missing IPS terminator')
        if patch[cursor:cursor+3] == b'EOF':
            if cursor + 3 != len(patch):
                raise ValueError('Unexpected data after IPS terminator')
            return bytes(output)
        if cursor + 5 > len(patch):
            raise ValueError('Truncated IPS record')
        offset = int.from_bytes(patch[cursor:cursor+3], 'big')
        length = int.from_bytes(patch[cursor+3:cursor+5], 'big')
        cursor += 5
        if length == 0:
            raise ValueError('RLE records are not accepted by this patch format')
        if cursor + length > len(patch) or offset + length > MAX_IMAGE:
            raise ValueError('Truncated or out-of-bounds IPS record')
        if offset + length > len(output):
            output.extend(b'\0' * (offset + length - len(output)))
        output[offset:offset+length] = patch[cursor:cursor+length]
        cursor += length
