import struct
from abc import ABC, abstractmethod
from enum import Enum

# TODO: add blz compression
def compress_blz(method, data):
    print(f"attempted to backward compress data with method {method}")
    return data

# TODO: add lz10/lz11 compression
def compress_lz1x(method, data):
    print(f"attempted to forward compress data with method {method}")
    return data

# TODO: implement rlz compression/decompression when mnllib is hooked into this class
def compress_rlz(data):
    print(f"attempted to rle-lzss compress data")
    return data

def decompress_rlz(data):
    print(f"attempted to rle-lzss decompress data")
    return data

class BinGluModes(Enum):
    SIMPLE_INDEX       = 0
    PREFIXED_INDEX     = 1
    COMPLEX_INDEX      = 2
    BINARY_SEARCH      = 3
    SAFE_BUCKET_SEARCH = 4
    SAFE_BINARY_SEARCH = 5

class BinGluError(Exception):
    """
    Raised when an issue occurs inside the BinGluArchive class.

    Code 100: Fallback import error.
    Code 101: The header was found to be corrupted during import.
    Code 102: The header uses two-file mode, but only one file was provided.
    Code 103: The header uses file indexing, but the table is corrupted.

    Code 200: Fallback export error.
    Code 201: Buckets were found to be too small when trying to export.
    Code 202: Exported BinGlu mode does not support dealing with hash collisions.
    Code 203: A file was given an offset value too large for the format. This usually means the archive is too large.
    Code 204: A file was given an length value too large for the format. This usually means the file is too large for the archive.
    Code 205: A file was found to not have an associated name, which is required in this BinGlu mode.
    Code 206: A file was found to not have an associated name hash, which is required in this BinGlu mode.

    Code 300: Fallback access error.
    Code 301: Requested header property does not exist.
    Code 302: Requested file name does not exist.
    Code 303: Requested file index does not exist in file list.
    Code 304: Requested mode is not supported.
    Code 305: This archive does not support being accessed via index.
    Code 306: Requested compression method is not supported.
    Code 307: Requested file data is outside of the data section.
    Code 308: This archive does not support being accessed via name hashing.
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
            304: "Access Error: Unsupported Mode",
            305: "Access Error: Indexed Access Not Supported",
            306: "Access Error: Unsupported Compression Method",
            307: "Access Error: Out of Bounds Read",
            308: "Access Error: Hashed Access Not Supported",
        }.get(error_code, f"Error Code {error_code} Not Implemented")
        super().__init__(message)
        self.error_code = error_code
        self.file_indices = file_indices



class BinGluArchive(ABC):
    pad_archive_amount = None

    supported_compression_methods = []
    implemented_compression_methods = [None, 'm', 'f0', 'f1', 'b0', 'b1', 'b2', 'r']
    usable_compression_methods = ['f0', 'f1', 'b0', 'b1', 'b2', 'r']

    supported_modes = []
    implemented_modes = [
        BinGluModes.SIMPLE_INDEX,
        # BinGluModes.PREFIXED_INDEX,
        # BinGluModes.COMPLEX_INDEX,
        BinGluModes.BINARY_SEARCH,
        BinGluModes.SAFE_BUCKET_SEARCH,
        BinGluModes.SAFE_BINARY_SEARCH,
    ]

    mode_keyword = "mode"
    single_file_keyword = "single_file"
    use_index_keyword = "use_index"
    base_index_keyword = "base_index"

    compression_method_keyword = "compression_method"
    pad_archive_keyword = "pad_archive"

    @classmethod
    @abstractmethod
    def get_archive_mode(cls, input_data):
        raise BinGluError(300)

    @classmethod
    @abstractmethod
    def archive_uses_single_file(cls, input_data):
        raise BinGluError(300)

    @classmethod
    @abstractmethod
    def archive_uses_index_table(cls, input_data):
        raise BinGluError(300)

    @classmethod
    @abstractmethod
    def get_archive_base_index(cls, input_data):
        raise BinGluError(300)

    @classmethod
    @abstractmethod
    def get_file_entry_by_name(cls, file_name, input_data):
        raise BinGluError(300)

    @classmethod
    @abstractmethod
    def get_file_entry_by_index(cls, file_index, input_data, unsafe_access = False):
        raise BinGluError(300)

    @classmethod
    @abstractmethod
    def get_file_index_by_entry(cls, file_entry, input_data, unsafe_access = False):
        raise BinGluError(300)

    @classmethod
    @abstractmethod
    def extract_file_data_by_name(cls, file_name, input_data, input_data_sub = None):
        raise BinGluError(300)

    @classmethod
    @abstractmethod
    def extract_file_data_by_index(cls, file_index, input_data, input_data_sub = None):
        raise BinGluError(300)

    @classmethod
    @abstractmethod
    def extract_file_data_by_entry(cls, entry_index, input_data, input_data_sub = None):
        raise BinGluError(300)

    @staticmethod
    def get_name_hash(name):
        if name is None or not isinstance(name, str):
            return None

        name = name.encode("ascii")

        hsh = 0
        for c in reversed(name):
            hsh = (hsh * 31 + c) & 0xFFFFFFFF
        return hsh

    @classmethod
    def compress_data(cls, compression_type, data):
        if compression_type is None:
            return data

        if compression_type not in cls.usable_compression_methods:
            raise BinGluError(306)

        method = None
        if len(compression_type) > 1:
            method = int(compression_type[1])

        match compression_type[0]:
            case 'f': data = compress_lz1x(method, data)
            case 'b': data = compress_blz(method, data)
            case 'r': data = compress_rlz(data)
            case _: pass

        return data

    @classmethod
    def decompress_data(cls, compression_type, data):
        if compression_type is None:
            return data

        if compression_type not in cls.usable_compression_methods:
            raise BinGluError(306)

        match compression_type[0]:
            case 'f': data = decompress_lz1x(data)
            case 'b': data = decompress_blz(data)
            case 'r': data = decompress_rlz(data)
            case _: pass

        return data

    @classmethod
    def get_default_properties(cls):
        return {
            cls.mode_keyword:        BinGluModes.SAFE_BUCKET_SEARCH,
            cls.single_file_keyword: True,
            cls.use_index_keyword:   False,
            cls.base_index_keyword:  0, # TODO: let user change this
        }

    @classmethod
    def get_default_advanced_properties(cls):
        return {
            cls.compression_method_keyword: 'b0',
            cls.pad_archive_keyword:        False,
        }

    @classmethod
    def new_archive(cls, mode = BinGluModes.SAFE_BUCKET_SEARCH):
        test_class = cls.get_mode_class(mode)
        out_obj = test_class()

        out_obj.properties = cls.get_default_properties()
        out_obj.properties[cls.mode_keyword] = mode

        out_obj.advanced_properties = cls.get_default_advanced_properties()

        out_obj.files = []

        return out_obj

    @classmethod
    @abstractmethod
    def import_archive(cls, input_data, input_data_sub = None):
        raise BinGluError(100)

    @abstractmethod
    def export_archive(self):
        raise BinGluError(200)

    @classmethod
    def import_archive_general(cls, input_data, input_data_sub = None):
        for test_class in [BG4Archive, BG3Archive, BG2Archive, BGArchive]:
            try:
                return test_class.import_archive(input_data, input_data_sub)
            except BinGluError as e:
                if e.error_code != 101 and e.error_code != 100:
                    raise e
        
        raise BinGluError(101)

    @classmethod
    def get_mode_class(cls, mode):
        if mode not in cls.implemented_modes:
            raise BinGluError(304)

        for test_class in [BG4Archive, BG3Archive, BG2Archive, BGArchive]:
            if mode in test_class.supported_modes:
                return test_class

        raise BinGluError(304)

    def try_change_mode(self, mode):
        test_class = self.get_mode_class(mode)
        self.__class__ = test_class

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
        if set_property not in self.properties and set_property not in self.advanced_properties:
            raise BinGluError(301)
        if set_property == self.mode_keyword and value not in self.supported_modes:
            self.try_change_mode(value)
        if set_property == self.compression_method_keyword and value not in self.supported_compression_methods:
            raise BinGluError(306)

        if set_property in self.properties:
            self.properties[set_property] = value
        elif set_property in self.advanced_properties:
            self.advanced_properties[set_property] = value

    def get_property(self, get_property):
        if get_property not in self.properties and get_property not in self.advanced_properties:
            raise BinGluError(301)

        if get_property in self.properties:
            return self.properties[get_property]
        elif get_property in self.advanced_properties:
            return self.advanced_properties[get_property]

    def new_file(self, file_name, file_data):
        file_index = len(self.files)
        self.files.append({"file_name": file_name, "name_hash": None})
        self.set_file_data(file_index, file_data, is_by_index = True)

    def set_file_name(self, file_name, new_name, is_by_index = False):
        file_index = self.get_file_id_by_name_or_hash(file_name) if not is_by_index else file_name
        self._check_file_index(file_index)

        self.files[file_index]["file_name"] = new_name
        self.files[file_index]["name_hash"] = None

    def set_file_data(self, file_name, file_data, is_by_index = False):
        file_index = self.get_file_id_by_name_or_hash(file_name) if not is_by_index else file_name
        self._check_file_index(file_index)

        if self.files[file_index].get("compression_type") is None:
            self.files[file_index]["compression_type"] = self.advanced_properties[self.compression_method_keyword]

        self.files[file_index]["data_compression_type"] = None
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
        recommended_type = self.advanced_properties[self.compression_method_keyword]
        if recommended_type != 'm':
            return recommended_type
        else:
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



class BG4Archive(BinGluArchive):
    header_magic = b"BG4\0"
    invalid_name = "(invalid)"

    pad_archive_amount = 0x80
    supported_compression_methods = [None, 'm', 'f0', 'f1', 'b0', 'b1', 'b2']
    supported_modes = [
        BinGluModes.BINARY_SEARCH,
        BinGluModes.SAFE_BUCKET_SEARCH,
        BinGluModes.SAFE_BINARY_SEARCH,
    ]

    @classmethod
    def _get_archive_header(cls, input_data, get_advanced = False):
        magic = input_data[:4]
        if magic != cls.header_magic:
            raise BinGluError(101)
        
        properties_raw, entry_count, header_length, bucket_count, bucket_size = struct.unpack("<HHIHH", input_data[4:16])

        # hi   ------>   lo
        # xxxxxxPS MMMMMMMM
        properties = cls.get_default_properties()
        properties[cls.mode_keyword] = BinGluModes(properties_raw & 0x00FF)

        properties[cls.single_file_keyword] = (properties_raw & 0x0100) != 0
        properties[cls.use_index_keyword]   = (properties_raw & 0x0200) != 0

        if entry_count != (bucket_count * bucket_size) and properties[cls.mode_keyword] == BinGluModes.SAFE_BUCKET_SEARCH:
            raise BinGluError(101)

        if get_advanced:
            blz_algorithm = (properties_raw & 0xC000) >> 14
            return properties, header_length, bucket_count, bucket_size, entry_count, blz_algorithm
        else:
            return properties, header_length, bucket_count, bucket_size, entry_count

    @classmethod
    def get_archive_mode(cls, input_data):
        properties, _, _, _, _ = cls._get_archive_header(input_data)
        return properties[cls.mode_keyword]

    @classmethod
    def archive_uses_single_file(cls, input_data):
        properties, _, _, _, _ = cls._get_archive_header(input_data)
        return properties[cls.single_file_keyword]

    @classmethod
    def archive_uses_index_table(cls, input_data):
        properties, _, _, _, _ = cls._get_archive_header(input_data)
        return properties[cls.use_index_keyword]

    @classmethod
    def get_archive_base_index(cls, input_data):
        return 0

    @classmethod
    def _get_archive_mode_properties(cls, mode):
        master_dict = {
            BinGluModes.BINARY_SEARCH:      {"entry_struct": "<III",  "entry_size": 12},
            BinGluModes.SAFE_BUCKET_SEARCH: {"entry_struct": "<IIIH", "entry_size": 14},
            BinGluModes.SAFE_BINARY_SEARCH: {"entry_struct": "<IIIH", "entry_size": 14},
        }

        return master_dict.get(mode)

    @classmethod
    def _check_index_table(cls, input_data):
        if not cls.archive_uses_index_table(input_data):
            return None

        properties, _, _, _, entry_count = cls._get_archive_header(input_data)
        mode = properties[cls.mode_keyword]
        entry_count = int.from_bytes(input_data[6:8], 'little')
        entry_size = cls._get_archive_mode_properties(mode)["entry_size"]

        index_table_offset = 16 + (entry_count * entry_size)
        invalid_files = 0
        for i in range(entry_count):
            entry_index_offset = index_table_offset + (i * 4)
            file_index = int.from_bytes(input_data[entry_index_offset + 0 : entry_index_offset + 2], 'little')
            if file_index == 0xFFFF:
                invalid_files += 1
                file_entry_offset = 16 + (entry_size * i)
                if (int.from_bytes(input_data[file_entry_offset + 4 : file_entry_offset + 8], 'little') & 0x80000000) == 0:
                    return False
                continue

            file_index_offset = index_table_offset + (file_index * 4)
            if i != int.from_bytes(input_data[file_index_offset + 2 : file_index_offset + 4], 'little'):
                return False

        for i in range(invalid_files):
            file_index_offset = index_table_offset + ((entry_count - (i + 1)) * 4)
            if 0xFFFF != int.from_bytes(input_data[file_index_offset + 2 : file_index_offset + 4], 'little'):
                return False

        return True

    # TODO: binary search
    @classmethod
    def get_file_entry_by_name(cls, file_name, input_data):
        properties, _, bucket_count, bucket_size, entry_count = cls._get_archive_header(input_data)
        mode = properties[cls.mode_keyword]
        entry_size = cls._get_archive_mode_properties(mode)["entry_size"]

        name_hash = cls.get_name_hash(file_name)
        first_entry = 0
        if mode == BinGluModes.SAFE_BUCKET_SEARCH:
            first_entry = (name_hash % bucket_count) * bucket_size
            entry_count = bucket_size
        
        print(first_entry)

    @classmethod
    def get_file_entry_by_index(cls, file_index, input_data, unsafe_access = False):
        return cls._file_index_table_access(input_data, file_index, unsafe_access, 1)

    @classmethod
    def get_file_index_by_entry(cls, file_entry, input_data, unsafe_access = False):
        return cls._file_index_table_access(input_data, file_entry, unsafe_access, 0)

    @classmethod
    def _file_index_table_access(cls, input_data, table_index, unsafe_access, table_value):
        properties, _, _, _, entry_count = cls._get_archive_header(input_data)

        if not unsafe_access:
            index_table = cls._check_index_table(input_data)
            if index_table is None:
                raise BinGluError(305)
            elif not index_table:
                raise BinGluError(103)

        mode = properties[cls.mode_keyword]
        entry_size = cls._get_archive_mode_properties(mode)["entry_size"]

        index_table_offset = 16 + (entry_count * entry_size)
        file_index_offset = index_table_offset + [0, 2][table_value] + (table_index * 4)

        return int.from_bytes(input_data[file_index_offset : file_index_offset + 2], 'little')

    @classmethod
    def _get_file_entry_data(cls, file_entry, input_data):
        properties, _, _, _, entry_count = cls._get_archive_header(input_data)
        mode = properties[cls.mode_keyword]
        mode_properties = cls._get_archive_mode_properties(mode)
        entry_struct, entry_size = mode_properties["entry_struct"], mode_properties["entry_size"]

        if file_entry >= entry_count or file_entry < 0:
            raise BinGluError(303)

        entry_offset = 16 + (file_entry * entry_size)
        raw_data = struct.unpack(entry_struct, input_data[entry_offset : entry_offset + entry_size])
        data_offset, data_length, name_hash, name_offset = raw_data + ((None,) * (4 - len(raw_data)))

        compression_value = (data_offset & 0xC0000000) >> 30
        compression_type = {1: 'f', 2: 'b'}.get(compression_value)
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

    @classmethod
    def extract_file_data_by_name(cls, file_name, input_data, input_data_sub = None):
        entry_index = cls.get_file_entry_by_name(file_name, input_data)
        return cls.extract_file_data_by_entry(entry_index, input_data, input_data_sub)

    @classmethod
    def extract_file_data_by_index(cls, file_index, input_data, input_data_sub = None):
        entry_index = cls.get_file_entry_by_index(file_index, input_data)
        return cls.extract_file_data_by_entry(entry_index, input_data, input_data_sub)
    
    @classmethod
    def extract_file_data_by_entry(cls, entry_index, input_data, input_data_sub = None):
        _, _, compression_type, data_offset, data_length = cls._get_file_entry_data(entry_index, input_data)
        _, header_length, _, _, _ = self._get_archive_header(input_data)

        header_length_adjusted = 0
        if cls.archive_uses_single_file(input_data):
            header_length_adjusted = header_length
            input_data_sub = input_data
        elif input_data_sub is None:
            raise BinGluError(102)

        if (data_offset < header_length_adjusted) or ((data_offset + data_length) > len(input_data_sub)):
            raise BinGluError(307)

        file_data = input_data_sub[data_offset : data_offset + data_length]
        return cls.decompress_data(compression_type, file_data)

    @classmethod
    def import_archive(cls, input_data, input_data_sub = None):
        properties, header_length, bucket_count, bucket_size, entry_count, blz_algorithm = cls._get_archive_header(input_data, get_advanced = True)

        header_length_adjusted = 0
        if not properties[cls.single_file_keyword]:
            if input_data_sub is None:
                raise BinGluError(102)
        else:
            header_length_adjusted = header_length
            input_data_sub = input_data

        file_sorting = {}
        sort_by_index = cls._check_index_table(input_data)
        compression_method = None
        compression_confirmation = 0

        for i in range(entry_count):
            entry_data = cls._get_file_entry_data(i, input_data)
            if entry_data is None:
                continue

            file_name, name_hash, compression_type, data_offset, data_length = entry_data

            if (data_offset < header_length_adjusted) or ((data_offset + data_length) > len(input_data_sub)):
                raise BinGluError(307)

            file_data = input_data_sub[data_offset : data_offset + data_length]

            if compression_type == 'f':
                lz_type = file_data[0]
                comp_type = {
                    0x10: 0,
                    0x11: 1,
                }[lz_type]
                compression_type += str(comp_type)
            elif compression_type == 'b':
                compression_type += str(blz_algorithm)

            file = {"file_name": file_name, "name_hash": name_hash if file_name is None else None, "compression_type": compression_type, "data": file_data, "data_compression_type": compression_type}

            if sort_by_index:
                file_index = cls.get_file_index_by_entry(i, input_data, unsafe_access = True) # bypass slow table check since it was already checked once
                file_sorting[file_index] = file
            else:
                file_sorting[(data_offset, data_length)] = file

            if compression_type is not None:
                if compression_method != compression_type and compression_method != 'm':
                    if compression_confirmation == 0:
                        compression_method = compression_type
                    else:
                        compression_method = 'm'

                compression_confirmation += 1

        files = []
        for file in sorted(file_sorting.keys()):
            files.append(file_sorting[file])

        advanced_properties = cls.get_default_advanced_properties()
        advanced_properties[cls.compression_method_keyword] = compression_method
        advanced_properties[cls.pad_archive_keyword] = (header_length & 0x7F) == 0

        out_obj = cls()
        out_obj.properties = properties
        out_obj.advanced_properties = advanced_properties
        out_obj.files = files

        return out_obj

    def _calculate_buckets(self, prioritize_speed = True):
        bucket_size = 1
        last_bucket_amount = None
        last_bucket_size = None

        while True:
            bucket_amount = len(self.files) // bucket_size

            found = False
            while not found:
                test_buckets = [0] * bucket_amount

                found = True
                for file in self.files:
                    hsh = self.get_name_hash(file["file_name"])
                    bucket = hsh % bucket_amount

                    test_buckets[bucket] += 1
                    if test_buckets[bucket] > bucket_size:
                        bucket_amount += 1
                        if bucket_amount > 1024: # give up and try again
                            bucket_size += 1
                            bucket_amount = len(self.files) // bucket_size
                        found = False
                        break

            if prioritize_speed:
                return bucket_amount, bucket_size

            # # TODO: this isn't the whole picture
            # if not (last_bucket_amount is None or last_bucket_size is None):
            #     if (bucket_amount * bucket_size) > (last_bucket_amount * last_bucket_size):
            #         return last_bucket_amount, last_bucket_size

            last_bucket_amount, last_bucket_size = bucket_amount, bucket_size
            bucket_size += 1

    def export_archive(self):
        mode = self.properties[self.mode_keyword]
        if mode != BinGluModes.SAFE_BUCKET_SEARCH:
            bucket_count = 1
            bucket_size = len(self.files)
        else:
            bucket_count, bucket_size = self._calculate_buckets()

        entry_count = bucket_count * bucket_size

        files = {}

        # name section
        name_section = bytearray()

        if mode == BinGluModes.SAFE_BUCKET_SEARCH:
            name_section.extend(self.invalid_name.encode("ascii") + b'\0')

        hash_dict = {}
        hash_collisions = set()

        for file_index, file in enumerate(self.files):
            name = file["file_name"]
            hsh = self.get_name_hash(name) if file["name_hash"] is None else file["name_hash"]
            if hsh is None:
                raise BinGluError(206, [file_index])

            if hsh in hash_dict.keys():
                if mode != BinGluModes.SAFE_BUCKET_SEARCH and mode != BinGluModes.SAFE_BINARY_SEARCH:
                    raise BinGluError(202, [hash_dict[hsh], file_index])
                hash_collisions.add(hsh)
            hash_dict[hsh] = file_index

            files[file_index] = {"name_offset": len(name_section), "name_hash": hsh}
            if mode == BinGluModes.SAFE_BUCKET_SEARCH or mode == BinGluModes.SAFE_BINARY_SEARCH:
                if name is None:
                    raise BinGluError(205, [file_index])
                name_section.extend(name.encode('ascii') + b'\0')

        entry_size = self._get_archive_mode_properties(mode)["entry_size"]

        header_length = 16 + (entry_size * entry_count) + len(name_section)
        if self.properties[self.use_index_keyword]: header_length += entry_count * 4

        pad_amount = 4
        if self.advanced_properties[self.pad_archive_keyword]:
            pad_amount = self.pad_archive_amount
        extra_padding = (pad_amount - (header_length % pad_amount)) % pad_amount
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

            if compression_type is not None:
                compression_type = compression_type[0]
            if self.get_file_is_compressed(file_index, is_by_index = True):
                compression_type = [None, 'f', 'b'].index(compression_type)
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

        # calculate automatically how many elements are in the struct
        entry_struct = self._get_archive_mode_properties(mode)["entry_struct"]
        dummy_bytes = bytes(struct.calcsize(entry_struct))
        entry_elements = len(struct.unpack(entry_struct, dummy_bytes))

        global_index = 0
        for bucket in buckets:
            while len(bucket) < bucket_size:
                bucket.append(invalid_file)

            for file in sorted(bucket, key = lambda bucket_file: bucket_file["name_hash"]):
                name_offset = file["name_offset"]
                is_null = (mode != BinGluModes.SAFE_BUCKET_SEARCH) and name_offset == 0
                if self.properties[self.use_index_keyword] and not is_null: name_offset += entry_count * 4

                entry_data = [file["data_offset"], file["data_length"], file["name_hash"], name_offset]
                hash_table.extend(struct.pack(entry_struct, *entry_data[:entry_elements]))

                file_index = file["file_index"]
                if file_index is not None:
                    order_table[global_index][0] = file_index
                    order_table[file_index][1] = global_index

                global_index += 1

        # index table
        index_table = bytearray()
        if self.properties[self.use_index_keyword]:
            for index_set in order_table:
                index_table.extend(struct.pack("<HH", *index_set))

        # full file
        output_file = bytearray()

        output_file.extend(self.header_magic)

        properties = mode.value

        compression_method = self.advanced_properties[self.compression_method_keyword]
        blz_algorithm = 0
        if compression_method is not None and compression_method[0] == 'b':
            blz_algorithm = int(compression_method[1])
        properties |= blz_algorithm << 14

        if self.properties[self.single_file_keyword]: properties |= 0x0100
        if self.properties[self.use_index_keyword]:   properties |= 0x0200

        if mode != BinGluModes.SAFE_BUCKET_SEARCH:
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



class BG3Archive(BinGluArchive): # TODO: everything
    pad_archive_amount = 0x80
    supported_compression_methods = [None, 'm', 'f0', 'f1', 'b0', 'b1', 'b2']
    supported_modes = [
        BinGluModes.COMPLEX_INDEX
    ]

    @classmethod
    def get_archive_mode(cls, input_data):
        return BinGluModes.COMPLEX_INDEX

    # @classmethod
    # def archive_uses_single_file(cls, input_data):
    #     raise BinGluError(300)

    @classmethod
    def archive_uses_index_table(cls, input_data):
        return True

    # @classmethod
    # def get_archive_base_index(cls, input_data):
    #     raise BinGluError(300)

    @classmethod
    def get_file_entry_by_name(cls, file_name, input_data):
        raise BinGluError(308)

    @classmethod
    def get_file_entry_by_index(cls, file_index, input_data, unsafe_access = False):
        base_index = cls.get_archive_base_index(input_data)
        return file_index - base_index

    @classmethod
    def get_file_index_by_entry(cls, file_entry, input_data, unsafe_access = False):
        base_index = cls.get_archive_base_index(input_data)
        return file_entry + base_index

    @classmethod
    def extract_file_data_by_name(cls, file_name, input_data, input_data_sub = None):
        raise BinGluError(308)

    # @classmethod
    # def extract_file_data_by_index(cls, file_index, input_data, input_data_sub = None):
    #     raise BinGluError(300)

    # @classmethod
    # def extract_file_data_by_entry(cls, entry_index, input_data, input_data_sub = None):
    #     raise BinGluError(300)

    # @classmethod
    # def import_archive(cls, input_data, input_data_sub = None):
    #     raise BinGluError(100)

    # def export_archive(self, input_data, input_data_sub = None):
    #     raise BinGluError(200)



class BG2Archive(BinGluArchive): # TODO: everything
    pad_archive_amount = 0x200
    supported_compression_methods = [None, 'm', 'r']
    supported_modes = [
        BinGluModes.PREFIXED_INDEX
    ]

    @classmethod
    def get_archive_mode(cls, input_data):
        return BinGluModes.PREFIXED_INDEX

    # @classmethod
    # def archive_uses_single_file(cls, input_data):
    #     raise BinGluError(300)

    @classmethod
    def archive_uses_index_table(cls, input_data):
        return True

    @classmethod
    def get_archive_base_index(cls, input_data):
        return 0

    @classmethod
    def get_file_entry_by_name(cls, file_name, input_data):
        raise BinGluError(308)

    @classmethod
    def get_file_entry_by_index(cls, file_index, input_data, unsafe_access = False):
        return file_index

    @classmethod
    def get_file_index_by_entry(cls, file_entry, input_data, unsafe_access = False):
        return file_entry

    @classmethod
    def extract_file_data_by_name(cls, file_name, input_data, input_data_sub = None):
        raise BinGluError(308)

    # @classmethod
    # def extract_file_data_by_index(cls, file_index, input_data, input_data_sub = None):
    #     raise BinGluError(300)

    # @classmethod
    # def extract_file_data_by_entry(cls, entry_index, input_data, input_data_sub = None):
    #     raise BinGluError(300)

    # @classmethod
    # def import_archive(cls, input_data, input_data_sub = None):
    #     raise BinGluError(100)

    # def export_archive(self, input_data, input_data_sub = None):
    #     raise BinGluError(200)



class BGArchive(BinGluArchive): # TODO: everything
    pad_archive_amount = 0x200
    supported_compression_methods = [None, 'm', 'r']
    supported_modes = [
        BinGluModes.SIMPLE_INDEX
    ]

    @classmethod
    def _verify_header(cls, input_data):
        header_end = int.from_bytes(input_data[:4], 'little')

        last_offset = header_end
        for i in range(1, (header_end + 3) // 4):
            new_offset = int.from_bytes(input_data[(i * 4) : ((i + 1) * 4)], 'little')
            if new_offset < last_offset:
                raise BinGluError(101)
            last_offset = new_offset

    @classmethod
    def get_archive_mode(cls, input_data = None):
        return BinGluModes.SIMPLE_INDEX

    @classmethod
    def archive_uses_single_file(cls, input_data = None):
        return True

    @classmethod
    def archive_uses_index_table(cls, input_data = None):
        return True

    @classmethod
    def get_archive_base_index(cls, input_data = None):
        return 0

    @classmethod
    def get_file_entry_by_name(cls, file_name = None, input_data = None):
        raise BinGluError(308)

    @classmethod
    def get_file_entry_by_index(cls, file_index, input_data = None, unsafe_access = False):
        return file_index

    @classmethod
    def get_file_index_by_entry(cls, file_entry, input_data = None, unsafe_access = False):
        return file_entry

    @classmethod
    def extract_file_data_by_name(cls, file_name = None, input_data = None, input_data_sub = None):
        raise BinGluError(308)

    @classmethod
    def extract_file_data_by_index(cls, file_index, input_data, input_data_sub = None):
        ... # TODO

    @classmethod
    def extract_file_data_by_entry(cls, entry_index, input_data, input_data_sub = None):
        ... # TODO

    @classmethod
    def import_archive(cls, input_data, input_data_sub = None):
        cls._verify_header(input_data)
        header_end = int.from_bytes(input_data[:4], 'little')

        uses_padding = header_end % cls.pad_archive_amount == 0

        last_offset = header_end
        files = []
        for i in range(1, (header_end + 3) // 4):
            new_offset = int.from_bytes(input_data[(i * 4) : ((i + 1) * 4)], 'little')
            if new_offset != 0xFFFFFFFF:
                if new_offset % cls.pad_archive_amount != 0:
                    uses_padding = False

                file_data = input_data[last_offset : new_offset]
                file = {"file_name": None, "name_hash": None, "compression_type": None, "data": file_data, "data_compression_type": None} # TODO: compression type
                files.append(file)

            last_offset = new_offset

        properties = cls.get_default_properties()
        properties[cls.mode_keyword] = cls.get_archive_mode(None)
        properties[cls.single_file_keyword] = cls.archive_uses_single_file(None)
        properties[cls.use_index_keyword] = cls.archive_uses_index_table(None)
        properties[cls.base_index_keyword] = cls.get_archive_base_index(None)

        advanced_properties = cls.get_default_advanced_properties()
        # advanced_properties[cls.compression_method_keyword] = compression_method
        advanced_properties[cls.pad_archive_keyword] = uses_padding

        out_obj = cls()
        out_obj.properties = properties
        out_obj.advanced_properties = advanced_properties
        out_obj.files = files

        return out_obj

    def export_archive(self, input_data, input_data_sub = None):
        ... # TODO
