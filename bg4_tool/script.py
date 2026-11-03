def decompress_blz(data):
    if not isinstance(data, bytearray):
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


def compress_blz(data):
    decompressed_len = len(data)

    read_pointer = decompressed_len
    preserve_pointer = 0

    packet_set = []
    while True:
        preserve_pointer = read_pointer
        read_pointer, packet_header, packet = get_packet_recursive(data, read_pointer)
        if read_pointer < 0:
            break
        packet.append(packet_header)
        packet_set.append(packet)

    print(preserve_pointer)
    return_array = bytearray(data[:preserve_pointer])
    for packet in reversed(packet_set):
        return_array.extend(packet)

    extra_padding = (4 - (len(return_array) % 4)) % 4
    return_array.extend(b"\xFF" * extra_padding)

    compressed_len = len(return_array) + 8 - preserve_pointer
    footer_len = extra_padding + 8
    decompressed_extend = decompressed_len - len(return_array) + 8

    return_array.extend(compressed_len.to_bytes(3, 'little'))
    return_array.extend(footer_len.to_bytes(1, 'little'))
    return_array.extend(decompressed_extend.to_bytes(4, 'little'))
    return return_array

def get_packet_recursive(data, pointer, packet_header = 0, recursion_level = 7):
    if recursion_level < 0:
        return pointer, packet_header, bytearray()

    test_byte = data[pointer - 1]
    window = data[pointer : pointer + 0x1002]

    indeces = [index + 1 for index, value in enumerate(window) if value == test_byte and index >= 2]
    displacement = 0
    length = 2
    bad_window_test = True
    for test_displacement in indeces:
        test_window = window[test_displacement - 18 : test_displacement]
        decompressed_window = data[pointer - 18 : pointer]
        new_length = next((i for i, (x, y) in enumerate(zip(reversed(decompressed_window), reversed(test_window))) if x != y), min(len(decompressed_window), len(test_window)))
        if new_length > length:
            length = new_length
            displacement = test_displacement
            bad_window_test = False

    if not indeces or bad_window_test:
        pointer, packet_header, packet = get_packet_recursive(data, pointer - 1, packet_header, recursion_level - 1)
        packet.extend(bytes([test_byte]))
        return pointer, packet_header, packet

    else:
        pointer_lz, packet_header_lz, packet_lz = get_packet_recursive(data, pointer - length, packet_header, recursion_level - 1)
        pointer_rb, packet_header_rb, packet_rb = get_packet_recursive(data, pointer - 1, packet_header, recursion_level - 1)

        if pointer_rb < pointer_lz: # raw byte beats lz window
            packet_rb.extend(bytes([test_byte]))
            return pointer_rb, packet_header_rb, packet_rb

        else:
            packed_value = (displacement - 3) | ((length - 3) << 12)
            packet_lz.extend(packed_value.to_bytes(2, 'little'))
            return pointer_lz, packet_header_lz | (1 << recursion_level), packet_lz



def decompress_analyze_blz(data):
    if not isinstance(data, bytearray):
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
        analyze_packet_header = []
        analyze_chunk_out = bytearray()

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

                analyze_packet_header.append(f"pointer: {{length: {length}, displacement: {displacement}}}")
            else:
                analyze_packet_header.append(f"literal: 0x{value[0]:02X}")

            data[write_pointer - length : write_pointer] = value
            write_pointer -= length

            analyze_chunk_out.extend(reversed(value))

        print("packet header: " + ", ".join(reversed(analyze_packet_header)))
        print("packet output: " + " ".join([f"{byte:02X}" for byte in reversed(analyze_chunk_out)]))
        print("")

    print("header: " + " ".join([f"{byte:02X}" for byte in data[:read_pointer]]))
    return data