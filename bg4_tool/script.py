def decompress_blz(data):
    data = bytearray(data)

    compressed_len = int.from_bytes(data[-8:-5], 'little')
    footer_len = data[-5]
    full_len = len(data)

    decompressed_extend = int.from_bytes(data[-4:], 'little')
    data.extend(bytes(decompressed_extend))

    read_pointer = full_len - footer_len
    write_pointer = full_len + decompressed_extend

    header_end = full_len - compressed_len
    while write_pointer > header_end:
        read_pointer -= 1
        instruction_set = data[read_pointer]
        next_instructions = [2 if instruction_set & (0x80 >> i) != 0 else 1 for i in range(8)]

        for instruction_key in next_instructions:
            value = data[read_pointer - instruction_key : read_pointer]
            length = 1
            read_pointer -= instruction_key

            if instruction_key == 2:
                instruction = int.from_bytes(value, 'little')
                length = (instruction >> 12) + 3
                displacement = (instruction & 0xFFF) + 3

                offset = write_pointer + displacement
                value = data[offset - length : offset]

            data[write_pointer - length : write_pointer] = value
            write_pointer -= length

    return data