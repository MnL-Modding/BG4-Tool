import struct

from bg4_tool.script import decompress_lz1x, decompress_blz

# TODO: add blz compression
def compress_blz(data):
    return data

# TODO: add lz10/lz11 compression
def compress_lz1x(data):
    return data

class BinGluError(Exception):
    """
    Raised when an issue occurs inside the BinGluArchive class.

    Code 100: Fallback import error.
    Code 101: The header was found to be corrupted during import.
    Code 102: The header uses two-file mode, but only one file was provided.
    Code 103: The header uses file indexing, but the table is corrupted.

    Code 200: Fallback export error.
    Code 201: Buckets were found to be too small when trying to export.
    Code 202: Exported BinGlu version does not support dealing with hash collisions.
    Code 203: A file was given an offset value too large for the format. This usually means the archive is too large.
    Code 204: A file was given an length value too large for the format. This usually means the file is too large for the archive.
    Code 205: A file was found to not have an associated name, which is required in this BinGlu version.
    Code 206: A file was found to not have an associated name hash, which is required in this BinGlu version.

    Code 300: Fallback access error.
    Code 301: Requested header property does not exist.
    Code 302: Requested file name does not exist.
    Code 303: Requested file index does not exist in file list.
    Code 304: Requested version is not supported.
    Code 305: This archive does not support being accessed via index.
    """
    def __init__(self, error_code, file_indices = []):
        message = {
            100: "Import Error: Unknown",
            101: "Import Error: Bad Header",
            102: "Import Error: Data File Not Provided",
            103: "Import Error: Bad Index Table",

            200: "Export Error: Unknown",
            201: "Export Error: Buckets Too Small",
            202: "Export Error: Unhandled Hash Collision",
            203: "Export Error: File Offset Too Large",
            204: "Export Error: File Length Too Large",
            205: "Export Error: File Name Required",
            206: "Export Error: File Name Hash Required",

            300: "Access Error: Unknown",
            301: "Access Error: Bad Property",
            302: "Access Error: Bad File Name",
            303: "Access Error: File Does Not Exist",
            304: "Access Error: Unsupported Version",
            305: "Access Error: Indexed Access Not Supported"
        }.get(error_code, f"Error Code {error_code} Not Implemented")
        super().__init__(message)
        self.error_code = error_code
        self.file_indices = file_indices

class BinGluArchive:
    header_magic = b"BG4\0"
    invalid_name = "(invalid)"
    supported_versions = [3, 4, 5]

    version_keyword = "version"
    single_file_keyword = "single_file"
    preserve_order_keyword = "preserve_order"

    @staticmethod
    def get_archive_header(input_data):
        magic = input_data[:4]
        if magic != BinGluArchive.header_magic:
            raise BinGluError(101)
        
        properties_raw, entry_count, _header_length, bucket_count, bucket_size = struct.unpack("<HHIHH", input_data[4:16])

        properties = {}
        properties[BinGluArchive.version_keyword] = properties_raw & 0x00FF

        properties[BinGluArchive.single_file_keyword]    = (properties_raw & 0x0100) != 0
        properties[BinGluArchive.preserve_order_keyword] = (properties_raw & 0x0200) != 0

        if entry_count != (bucket_count * bucket_size) and properties[BinGluArchive.version_keyword] == 4:
            raise BinGluError(101)

        return properties, bucket_count, bucket_size, entry_count

    @staticmethod
    def get_archive_version(input_data):
        properties, _, _, _ = BinGluArchive.get_archive_header(input_data)
        return properties[BinGluArchive.version_keyword]

    @staticmethod
    def archive_uses_single_file(input_data):
        properties, _, _, _ = BinGluArchive.get_archive_header(input_data)
        return properties[BinGluArchive.single_file_keyword]

    @staticmethod
    def archive_uses_index_table(input_data):
        properties, _, _, _ = BinGluArchive.get_archive_header(input_data)
        return properties[BinGluArchive.preserve_order_keyword]

    @staticmethod
    def get_name_hash(name):
        if name is None or not isinstance(name, str):
            return None

        name = name.encode("ascii")

        hsh = 0
        for c in reversed(name):
            hsh = (hsh * 31 + c) & 0xFFFFFFFF
        return hsh

    # TODO: add subtype
    @staticmethod
    def compress_data(compression_type, data):
        match compression_type:
            case "f": data = compress_lz1x(data)
            case "b": data = compress_blz(data)
            case _: pass

        return data

    @staticmethod
    def decompress_data(compression_type, data):
        match compression_type:
            case "f": data = decompress_lz1x(data)
            case "b": data = decompress_blz(data)
            case _: pass

        return data

    # TODO: binary search
    @staticmethod
    def get_file_entry_by_name(input_data, file_name):
        version = input_data[4]
        _, bucket_count, bucket_size, entry_count = BinGluArchive.get_archive_header(input_data)
        entry_size = 14 if version > 3 else 12

    @staticmethod
    def get_file_entry_by_index(input_data, file_index):
        return _file_index_table_access(input_data, file_index, 1)

    @staticmethod
    def get_file_index_by_entry(input_data, file_entry):
        return _file_index_table_access(input_data, file_entry, 0)

    @staticmethod
    def _file_index_table_access(input_data, table_index, table_value):
        if not BinGluArchive.archive_uses_index_table(input_data):
            raise BinGluError(305)

        version = input_data[4]
        entry_count = int.from_bytes(input_data[6:8], 'little')
        entry_size = 14 if version > 3 else 12

        index_table_offset = 16 + (entry_count * entry_size)
        file_index_offset = index_table_offset + [0, 2][table_value] + (file_entry * 4)

        return int.from_bytes(input_data[file_index_offset : file_index_offset + 2], 'little')

    @staticmethod
    def get_file_entry_data(input_data, file_entry):
        version = input_data[4]
        entry_count = int.from_bytes(input_data[6:8], 'little')
        entry_struct, entry_size = ("<IIIH", 14) if version > 3 else ("<III", 12)

        if file_entry >= entry_count or file_entry < 0:
            raise BinGluError(303)

        entry_offset = 16 + (file_entry * entry_size)
        raw_data = struct.unpack(entry_struct, input_data[entry_offset : entry_offset + entry_size])
        data_offset, data_length, name_hash, name_offset = raw_data + (None,) if len(raw_data) == 3 else raw_data

        compression_value = (data_offset & 0xC0000000) >> 30
        compression_type = {1: "f", 2: "b"}.get(compression_value)
        data_offset &= 0x3FFFFFFF

        is_invalid = ((data_length & 0x80000000) != 0) or ((data_offset & 0xC0000000) == 0xC0000000)
        data_length &= 0x3FFFFFFF

        if is_invalid:
            return None

        if name_offset is not None:
            name_section_offset = 16 + (entry_count * entry_size)
            read_pointer = name_section_offset + name_offset
            file_name = ""
            while(True):
                next_char = input_data[read_pointer : read_pointer + 1]
                if next_char == b'\0':
                    break
                file_name += next_char.decode("ascii")
                read_pointer += 1
        else:
            file_name = None

        return file_name, name_hash, compression_type, data_offset, data_length

    def __init__(self):
        # hi   ------>   lo
        # xxxxxxPS VVVVVVVV
        self.properties = {
            self.version_keyword:        5,
            self.single_file_keyword:    True,
            self.preserve_order_keyword: False,
        }

        # TODO: deprecate
        self.bucket_count = 0
        self.bucket_size = 0

        self.files = []

    def import_archive(self, input_data, input_data_sub = None):
        properties, bucket_count, bucket_size, entry_count = self.get_archive_header(input_data)

        self.properties = properties
        # TODO: deprecate
        self.bucket_count = bucket_count
        self.bucket_size = bucket_size

        if not self.properties[self.single_file_keyword]:
            if input_data_sub is None:
                raise BinGluError(102)
        else:
            input_data_sub = input_data

        file_sorting = {}
        for i in range(entry_count):
            entry_data = self.get_file_entry_data(input_data, i)
            if entry_data is None:
                continue

            file_name, name_hash, compression_type, data_offset, data_length = entry_data
            file_data = input_data_sub[data_offset : data_offset + data_length]

            file = {"file_name": file_name, "name_hash": name_hash if file_name is None else None, "compression_type": compression_type, "data": file_data, "data_compression_type": compression_type}
            # TODO: have this pull from the archive's index table if it has one, catch any exceptions that may raise with error code 103
            file_sorting[data_offset] = file

        for offset in sorted(file_sorting.keys()):
            self.files.append(file_sorting[offset])

    def _check_file_index(self, file_index):
        try:
            self.files[file_index]
        except IndexError:
            raise BinGluError(303)

    def get_file_id_by_name_or_hash(self, file_name):
        if isinstance(file_name, str):
            list_to_check = [item["file_name"] for item in self.files]
        elif isinstance(file_name, int):
            list_to_check = [item["name_hash"] for item in self.files]
        else:
            return None

        if file_name not in list_to_check:
            raise BinGluError(302)
        return list_to_check.index(file_name)

    def set_property(self, set_property, value):
        if set_property not in self.properties:
            raise BinGluError(301)
        if set_property == self.version_keyword and value not in self.supported_versions:
            raise BinGluError(304)
        self.properties[set_property] = value

    def get_property(self, get_property):
        if get_property not in self.properties:
            raise BinGluError(301)
        return self.properties[get_property]

    def new_file(self, file_name, file_data):
        file_index = len(self.files)
        self.files.append({"file_name": file_name, "name_hash": None})
        self.set_file_data(file_index, file_data, is_by_index = True)

    def set_file_data(self, file_name, file_data, is_by_index = False):
        file_index = self.get_file_id_by_name_or_hash(file_name) if not is_by_index else file_name
        self._check_file_index(file_index)

        compression_type = None
        # TODO: check whether to compress
        self.files[file_index]["compression_type"] = compression_type
        self.files[file_index]["data_compression_type"] = compression_type
        self.files[file_index]["data"] = file_data

    def get_uncompressed_file_contents(self, file_name, is_by_index = False):
        file_index = self.get_file_id_by_name_or_hash(file_name) if not is_by_index else file_name
        self._check_file_index(file_index)

        compression_type = self.get_file_data_compression_type(file_name, is_by_index)
        return self.decompress_data(compression_type, self.files[file_index]["data"])

    def get_file_contents(self, file_name, is_by_index = False):
        file_index = self.get_file_id_by_name_or_hash(file_name) if not is_by_index else file_name
        self._check_file_index(file_index)

        return self.files[file_index]["data"]

    def get_file_is_compressed(self, file_name, is_by_index = False):
        file_index = self.get_file_id_by_name_or_hash(file_name) if not is_by_index else file_name
        self._check_file_index(file_index)

        return self.files[file_index]["compression_type"] != None

    def get_file_compression_type(self, file_name, is_by_index = False):
        file_index = self.get_file_id_by_name_or_hash(file_name) if not is_by_index else file_name
        self._check_file_index(file_index)

        return self.files[file_index]["compression_type"]

    def get_file_data_is_compressed(self, file_name, is_by_index = False):
        file_index = self.get_file_id_by_name_or_hash(file_name) if not is_by_index else file_name
        self._check_file_index(file_index)

        return self.files[file_index]["data_compression_type"] != None

    def get_file_data_compression_type(self, file_name, is_by_index = False):
        file_index = self.get_file_id_by_name_or_hash(file_name) if not is_by_index else file_name
        self._check_file_index(file_index)

        return self.files[file_index]["data_compression_type"]

    # TODO: let the user restore names to files that only have a hash or index

    def export_archive(self):
        if self.properties[self.version_keyword] != 4:
            bucket_count = 1
            bucket_size = len(self.files)
        else:
            # TODO: get these automatically
            bucket_count = self.bucket_count
            bucket_size = self.bucket_size

        entry_count = bucket_count * bucket_size

        files = {}

        # name section
        name_section = bytearray()

        if self.properties[self.version_keyword] == 4:
            name_section.extend(self.invalid_name.encode("ascii") + b'\0')

        hash_dict = {}
        hash_collisions = set()

        for file_index, file in enumerate(self.files):
            name = file["file_name"]
            hsh = self.get_name_hash(name) if file["name_hash"] is None else file["name_hash"]
            if hsh is None:
                raise BinGluError(206, [file_index])

            if hsh in hash_dict.keys():
                if not self.properties[self.version_keyword] > 3:
                    raise BinGluError(202, [hash_dict[hsh], file_index])
                hash_collisions.add(hsh)
            hash_dict[hsh] = file_index

            files[file_index] = {"name_offset": len(name_section), "name_hash": hsh}
            if self.properties[self.version_keyword] > 3:
                if name is None:
                    raise BinGluError(205, [file_index])
                name_section.extend(encoded_name + b'\0')

        entry_size = 14 if self.properties[self.version_keyword] > 3 else 12

        header_length = 16 + (entry_size * entry_count) + len(name_section)
        if self.properties[self.preserve_order_keyword]: header_length += entry_count * 4
        extra_padding = (4 - (header_length % 4)) % 4
        header_length += extra_padding
        name_section.extend(b"\xFF" * extra_padding)

        # data section
        data_section = bytearray()

        for file_index, file in enumerate(self.files):
            files[file_index]["file_index"] = file_index
            data = self.get_file_contents(file_index, is_by_index = True)

            offset = len(data_section)
            if self.properties[self.single_file_keyword]:
                offset += header_length

            data_offset = offset
            if data_offset != (data_offset & 0x3FFFFFFF):
                raise BinGluError(203)
            files[file_index]["data_offset"] = data_offset

            data_compression_type = self.get_file_data_compression_type(file_index, is_by_index = True)
            compression_type = self.get_file_compression_type(file_index, is_by_index = True)
            if compression_type != data_compression_type:
                data = self.decompress_data(data_compression_type, data)
                data = self.compress_data(compression_type, data)

            if self.get_file_is_compressed(file_index, is_by_index = True):
                compression_type = [None, "f", "b"].index(compression_type)
                files[file_index]["data_offset"] |= (compression_type << 30)

            data_length = len(data)
            if data_length != (data_length & 0x3FFFFFFF):
                raise BinGluError(204, [file_index])
            files[file_index]["data_length"] = data_length
            data_section.extend(data)
            if files[file_index]["name_hash"] in hash_collisions:
                files[file_index]["data_length"] |= 0x40000000

            extra_padding = (4 - (len(data_section) % 4)) % 4
            data_section.extend(b"\xFF" * extra_padding)

        # hash table
        hash_table = bytearray()
        buckets = []
        for _ in range(bucket_count):
            buckets.append([])

        for file in files.values():

            bucket_id = file["name_hash"] % bucket_count
            buckets[bucket_id].append(file)

            if len(buckets[bucket_id]) > bucket_size:
                raise BinGluError(201)

        invalid_file = {"name_offset": 0, "name_hash": 0xFFFFFFFF, "data_offset": 0, "data_length": 0x80000000, "file_index": None}
        order_table = []
        for _ in range(entry_count):
            order_table.append([0xFFFF, 0xFFFF])

        global_index = 0
        for bucket in buckets:
            while len(bucket) < bucket_size:
                bucket.append(invalid_file)

            for file in sorted(bucket, key = lambda bucket_file: bucket_file["name_hash"]):
                name_offset = file["name_offset"]
                is_null = (self.properties[self.version_keyword] != 4) and name_offset == 0
                if self.properties[self.preserve_order_keyword] and not is_null: name_offset += entry_count * 4

                if self.properties[self.version_keyword] > 3:
                    hash_table.extend(struct.pack("<IIIH", file["data_offset"], file["data_length"], file["name_hash"], name_offset))
                else:
                    hash_table.extend(struct.pack("<III", file["data_offset"], file["data_length"], file["name_hash"]))

                file_index = file["file_index"]
                if file_index is not None:
                    order_table[global_index][0] = file_index
                    order_table[file_index][1] = global_index

                global_index += 1

        # index table
        index_table = bytearray()
        if self.properties[self.preserve_order_keyword]:
            for index_set in order_table:
                index_table.extend(struct.pack("<HH", *index_set))

        # full file
        output_file = bytearray()

        output_file.extend(self.header_magic)

        properties = self.properties[self.version_keyword]

        if self.properties[self.single_file_keyword]:    properties |= 0x0100
        if self.properties[self.preserve_order_keyword]: properties |= 0x0200

        if self.properties[self.version_keyword] != 4:
            bucket_count, bucket_size = 0, 0

        output_file.extend(struct.pack("<HHIHH", properties, entry_count, header_length, bucket_count, bucket_size))
        output_file.extend(hash_table)
        output_file.extend(index_table)
        output_file.extend(name_section)
        if self.properties[self.single_file_keyword]:
            output_file.extend(data_section)
            return output_file, None
        else:
            return output_file, data_section