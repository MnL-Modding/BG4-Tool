from math import ceil

def decompress_lz1x(data):
    lz_type = data[0]
    decompressed_len = int.from_bytes(data[1:4], 'little')
    out_data = bytearray(decompressed_len)

    read_pointer = 4
    write_pointer = 0

    while write_pointer < decompressed_len:
        instruction_set = data[read_pointer]
        next_instructions = [2 if instruction_set & (0x80 >> i) != 0 else 1 for i in range(8)]
        read_pointer += 1

        for instruction_key in next_instructions:
            value = data[read_pointer : read_pointer + instruction_key]
            length = 1

            if instruction_key == 2:
                instruction_test = None
                len_mask = 0xF
                len_add = 3
                if lz_type == 0x11:
                    instruction_test = value[0] >> 4
                    len_add = 1
                
                match instruction_test:
                    case 0:
                        instruction_key = 3
                        len_mask = 0xFFF
                        len_add = 0x11
                    case 1:
                        instruction_key = 4
                        len_mask = 0xFFFF
                        len_add = 0x111
                    case _:
                        pass

                if instruction_key > 2:
                    value = data[read_pointer : read_pointer + instruction_key]

                instruction = int.from_bytes(value, 'big')
                length = ((instruction >> 12) & len_mask) + len_add
                displacement = (instruction & 0xFFF) + 1

                offset = write_pointer - displacement
                value = out_data[offset : write_pointer]
                value *= ceil(length / len(value))
                value = value[:length]

            out_data[write_pointer : write_pointer + length] = value
            read_pointer += instruction_key
            write_pointer += length

    return out_data[:decompressed_len]

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