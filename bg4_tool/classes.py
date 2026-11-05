import struct
from io import BytesIO

from bg4_tool.script import decompress_blz

# TODO: add blz compression
def compress_blz(data):
    return data

class BG4ArchiveError(Exception):
    """
    Raised when an issue occurs inside the BG4Archive class.

    Code 100: Fallback import error.
    Code 101: The header was found to be corrupted during import.
    Code 102: The header uses two-file mode, but only one file was provided.
    Code 103: The header uses file indexing, but the table is corrupted.

    Code 200: Fallback export error.
    Code 201: Buckets were found to be too small when trying to export.
    Code 202: Exported BG4 version does not support dealing with hash collisions.
    Code 203: A file was given an offset value too large for the format. This usually means the archive is too large.
    Code 204: A file was given an length value too large for the format. This usually means the file is too large for the archive.
    Code 205: A file was found to not have an associated name, which is required in this BG4 version.
    Code 206: A file was found to not have an associated name hash, which is required in this BG4 version.

    Code 300: Fallback access error.
    Code 301: Requested header property does not exist.
    Code 302: Requested file name does not exist.
    Code 303: Requested file index does not exist in file list.
    Code 304: Requested version is not supported.
    """
    def __init__(self, error_code, file_indeces = []):
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
        }.get(error_code, f"Error Code {error_code} Not Implemented")
        super().__init__(message)
        self.error_code = error_code
        self.file_indeces = file_indeces

class BG4Archive:
    header_magic = b"BG4\0"
    invalid_name = "(invalid)"
    supported_versions = [3, 4, 5]

    version_keyword = "version"
    single_file_keyword = "single_file"
    preserve_order_keyword = "preserve_order"

    def __init__(self):
        # hi   ------>   lo
        # xxxxxxPS VVVVVVVV
        self.properties = {
            self.version_keyword:        4,
            self.single_file_keyword:    True,
            self.preserve_order_keyword: False,
        }

        # TODO: deprecate
        self.bucket_count = 0
        self.bucket_size = 0

        self.files = []

    def _get_archive_header(self, input_data):
        in_data = BytesIO(input_data)
        magic = in_data.read(4)

        if magic != self.header_magic:
            raise BG4ArchiveError(101)
        
        properties, entry_count, header_length, bucket_count, bucket_size = struct.unpack("<HHIHH", in_data.read(12))

        self.properties[self.version_keyword] = properties & 0x00FF

        self.properties[self.single_file_keyword]    = (properties & 0x0100) != 0
        self.properties[self.preserve_order_keyword] = (properties & 0x0200) != 0

        if entry_count != (bucket_count * bucket_size) and self.properties[self.version_keyword] == 4:
            raise BG4ArchiveError(101)

        # TODO: deprecate
        self.bucket_count = bucket_count
        self.bucket_size = bucket_size

        return entry_count

    def get_name_hash(self, name):
        if name is None:
            return None

        hsh = 0
        for c in reversed(name):
            hsh = (hsh * 31 + c) & 0xFFFFFFFF
        return hsh

    def archive_uses_single_file(self, input_data):
        self._get_archive_header(input_data)
        return self.properties[self.single_file_keyword]

    def import_archive(self, input_data, input_data_sub = None):
        entry_count = self._get_archive_header(input_data)
        in_data = BytesIO(input_data)

        in_data_sub = in_data
        if not self.properties[self.single_file_keyword]:
            if input_data_sub is None:
                raise BG4ArchiveError(102)
            in_data_sub = BytesIO(input_data_sub)

        name_sorting = {}

        entry_size = 12
        if self.properties[self.version_keyword] > 3:
            entry_size = 14

        name_section_offset = 16 + (entry_count * entry_size)
        for i in range(entry_count):
            in_data.seek(16 + (i * entry_size))

            if self.properties[self.version_keyword] > 3:
                data_offset, data_length, name_hash, name_offset = struct.unpack("<IIIH", in_data.read(entry_size))
            else:
                data_offset, data_length, name_hash = struct.unpack("<III", in_data.read(entry_size))
                name_offset = None

            # TODO: implement other compression types
            is_compressed = (data_offset & 0x80000000) != 0
            data_offset &= 0x3FFFFFFF

            is_invalid = ((data_length & 0x80000000) != 0) or ((data_offset & 0xC0000000) == 0xC0000000)
            data_length &= 0x3FFFFFFF

            if is_invalid: continue

            if name_offset is not None:
                in_data.seek(name_section_offset + name_offset)
                file_name = ""
                while(True):
                    next_char = in_data.read(1)
                    if next_char == b'\0':
                        break
                    file_name += next_char.decode("ascii")
            else:
                file_name = None

            in_data_sub.seek(data_offset)
            file_data = in_data_sub.read(data_length)

            file = {"file_name": file_name, "name_hash": name_hash if file_name is None else None, "is_compressed": is_compressed, "data": file_data, "data_is_compressed": is_compressed}
            # TODO: have this pull from the archive's index table if it has one, catch any exceptions that may raise with error code 103
            name_sorting[data_offset] = file

        for offset in sorted(name_sorting.keys()):
            self.files.append(name_sorting[offset])

    def _check_file_index(self, file_index):
        try:
            self.files[file_index]
        except IndexError:
            raise BG4ArchiveError(303)

    def get_file_id_by_name_or_hash(self, file_name):
        if isinstance(file_name, str):
            list_to_check = [item["file_name"] for item in self.files]
        elif isinstance(file_name, int):
            list_to_check = [item["name_hash"] for item in self.files]
        else:
            return None

        if file_name not in list_to_check:
            raise BG4ArchiveError(302)
        return list_to_check.index(file_name)

    def set_property(self, set_property, value):
        if set_property not in self.properties:
            raise BG4ArchiveError(301)
        if set_property == self.version_keyword and value not in self.supported_versions:
            raise BG4ArchiveError(304)
        self.properties[set_property] = value

    def get_property(self, get_property):
        if get_property not in self.properties:
            raise BG4ArchiveError(301)
        return self.properties[get_property]

    def new_file(self, file_name, file_data):
        file_index = len(self.files)
        self.files.append({"file_name": file_name, "name_hash": None})
        self.set_file_data(file_index, file_data, is_by_index = True)

    def set_file_data(self, file_name, file_data, is_by_index = False):
        file_index = self.get_file_id_by_name_or_hash(file_name) if not is_by_index else file_name
        self._check_file_index(file_index)

        is_compressed = False
        # TODO: check whether to compress
        self.files[file_index]["is_compressed"] = is_compressed
        self.files[file_index]["data_is_compressed"] = is_compressed
        self.files[file_index]["data"] = file_data

    def get_uncompressed_file_contents(self, file_name, is_by_index = False):
        file_index = self.get_file_id_by_name_or_hash(file_name) if not is_by_index else file_name
        self._check_file_index(file_index)

        file_data = self.files[file_index]["data"]
        if self.get_file_data_is_compressed(file_name):
            file_data = decompress_blz(file_data)
        return file_data

    def get_file_contents(self, file_name, is_by_index = False):
        file_index = self.get_file_id_by_name_or_hash(file_name) if not is_by_index else file_name
        self._check_file_index(file_index)

        return self.files[file_index]["data"]

    def get_file_is_compressed(self, file_name, is_by_index = False):
        file_index = self.get_file_id_by_name_or_hash(file_name) if not is_by_index else file_name
        self._check_file_index(file_index)

        return self.files[file_index]["is_compressed"]

    def get_file_data_is_compressed(self, file_name, is_by_index = False):
        file_index = self.get_file_id_by_name_or_hash(file_name) if not is_by_index else file_name
        self._check_file_index(file_index)

        return self.files[file_index]["data_is_compressed"]

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
            encoded_name = None
            if name is not None:
                encoded_name = name.encode("ascii")

            hsh = self.get_name_hash(encoded_name) if file["name_hash"] is None else file["name_hash"]
            if hsh is None:
                raise BG4ArchiveError(206, [file_index])

            if hsh in hash_dict.keys():
                if not self.properties[self.version_keyword] > 3:
                    raise BG4ArchiveError(202, [hash_dict[hsh], file_index])
                hash_collisions.add(hsh)
            hash_dict[hsh] = file_index

            files[file_index] = {"name_offset": len(name_section), "name_hash": hsh}
            if self.properties[self.version_keyword] > 3:
                if name is None:
                    raise BG4ArchiveError(205, [file_index])
                name_section.extend(encoded_name + b'\0')

        entry_size = 12
        if self.properties[self.version_keyword] > 3:
            entry_size = 14

        header_length = 16 + (entry_size * entry_count) + len(name_section)
        if self.properties[self.preserve_order_keyword]: header_length += entry_count * 4
        extra_padding = (4 - (header_length % 4)) % 4
        header_length += extra_padding
        name_section.extend(b"\xFF" * extra_padding)

        # data section
        data_section = bytearray()

        for file_index, file in enumerate(self.files):
            name_or_hash = file["name_hash"] if file["file_name"] is None else file["file_name"]
            files[file_index]["file_index"] = file_index
            data = self.get_file_contents(name_or_hash)

            offset = len(data_section)
            if self.properties[self.single_file_keyword]:
                offset += header_length

            data_offset = offset
            if data_offset != (data_offset & 0x3FFFFFFF):
                raise BG4ArchiveError(203)
            files[file_index]["data_offset"] = data_offset
            if self.get_file_is_compressed(name_or_hash):
                files[file_index]["data_offset"] |= 0x80000000

            data_is_compressed = self.get_file_data_is_compressed(name_or_hash)
            is_compressed = self.get_file_is_compressed(name_or_hash)
            if (not data_is_compressed) and (is_compressed):
                data = compress_blz(data)
            elif (data_is_compressed) and (not is_compressed):
                data = decompress_blz(data)

            data_length = len(data)
            if data_length != (data_length & 0x3FFFFFFF):
                raise BG4ArchiveError(204, [file_index])
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
                raise BG4ArchiveError(201)

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