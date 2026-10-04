"""Private Windows handle-based filesystem boundary for LocalFileRepository."""

from __future__ import annotations

import ctypes
import os
from pathlib import Path
from typing import Any, Final

from manga_director.domain.exceptions import ValidationError

_GENERIC_READ: Final = 0x80000000
_DELETE: Final = 0x00010000
_SYNCHRONIZE: Final = 0x00100000
_FILE_READ_ATTRIBUTES: Final = 0x00000080
_FILE_LIST_DIRECTORY: Final = 0x00000001
_FILE_TRAVERSE: Final = 0x00000020
_FILE_SHARE_READ: Final = 0x00000001
_FILE_SHARE_WRITE: Final = 0x00000002
_OPEN_EXISTING: Final = 3
_FILE_OPEN: Final = 1
_FILE_ATTRIBUTE_DIRECTORY: Final = 0x00000010
_FILE_ATTRIBUTE_REPARSE_POINT: Final = 0x00000400
_FILE_FLAG_OPEN_REPARSE_POINT: Final = 0x00200000
_FILE_FLAG_BACKUP_SEMANTICS: Final = 0x02000000
_FILE_DIRECTORY_FILE: Final = 0x00000001
_FILE_SYNCHRONOUS_IO_NONALERT: Final = 0x00000020
_FILE_NON_DIRECTORY_FILE: Final = 0x00000040
_FILE_OPEN_REPARSE_POINT: Final = 0x00200000
_FILE_TYPE_DISK: Final = 0x0001
_FILE_NAME_NORMALIZED: Final = 0x0
_FILE_DISPOSITION_INFO_CLASS: Final = 4
_FILE_FULL_DIRECTORY_INFO_CLASS: Final = 14
_FILE_FULL_DIRECTORY_RESTART_INFO_CLASS: Final = 15
_OBJ_CASE_INSENSITIVE: Final = 0x00000040
_DRIVE_REMOTE: Final = 4
_ERROR_FILE_NOT_FOUND: Final = 2
_ERROR_PATH_NOT_FOUND: Final = 3
_ERROR_NO_MORE_FILES: Final = 18
_ERROR_HANDLE_EOF: Final = 38


def _unsafe() -> ValidationError:
    return ValidationError("Project path safety cannot be established.")


class _FileTime(ctypes.Structure):
    _fields_ = [("low", ctypes.c_uint32), ("high", ctypes.c_uint32)]


class _ByHandleFileInformation(ctypes.Structure):
    _fields_ = [
        ("attributes", ctypes.c_uint32),
        ("creation", _FileTime),
        ("access", _FileTime),
        ("write", _FileTime),
        ("volume_serial", ctypes.c_uint32),
        ("size_high", ctypes.c_uint32),
        ("size_low", ctypes.c_uint32),
        ("links", ctypes.c_uint32),
        ("index_high", ctypes.c_uint32),
        ("index_low", ctypes.c_uint32),
    ]


class _FileDispositionInfo(ctypes.Structure):
    _fields_ = [("delete_file", ctypes.c_int)]


class _FileFullDirectoryInfo(ctypes.Structure):
    _fields_ = [
        ("next_entry_offset", ctypes.c_uint32),
        ("file_index", ctypes.c_uint32),
        ("creation_time", ctypes.c_int64),
        ("last_access_time", ctypes.c_int64),
        ("last_write_time", ctypes.c_int64),
        ("change_time", ctypes.c_int64),
        ("end_of_file", ctypes.c_int64),
        ("allocation_size", ctypes.c_int64),
        ("file_attributes", ctypes.c_uint32),
        ("file_name_length", ctypes.c_uint32),
        ("ea_size", ctypes.c_uint32),
        ("file_name", ctypes.c_wchar * 1),
    ]


class _UnicodeString(ctypes.Structure):
    _fields_ = [
        ("length", ctypes.c_ushort),
        ("maximum_length", ctypes.c_ushort),
        ("buffer", ctypes.c_wchar_p),
    ]


class _ObjectAttributes(ctypes.Structure):
    _fields_ = [
        ("length", ctypes.c_ulong),
        ("root_directory", ctypes.c_void_p),
        ("object_name", ctypes.POINTER(_UnicodeString)),
        ("attributes", ctypes.c_ulong),
        ("security_descriptor", ctypes.c_void_p),
        ("security_quality_of_service", ctypes.c_void_p),
    ]


class _IoStatusValue(ctypes.Union):
    _fields_ = [("status", ctypes.c_long), ("pointer", ctypes.c_void_p)]


class _IoStatusBlock(ctypes.Structure):
    _anonymous_ = ("value",)
    _fields_ = [("value", _IoStatusValue), ("information", ctypes.c_size_t)]


class _OpenedHandle:
    __slots__ = ("final_path", "handle", "path")

    def __init__(self, handle: int, path: Path, final_path: Path) -> None:
        self.handle = handle
        self.path = path
        self.final_path = final_path


class WindowsSafeFilesystem:
    """Perform project reads, existence checks, and deletion through pinned handles."""

    def __init__(self, root: Path) -> None:
        if os.name != "nt":
            raise RuntimeError("Windows safe filesystem is available only on Windows")
        self._root = Path(os.path.abspath(root))
        self._reject_remote_root()

    def _reject_remote_root(self) -> None:
        anchor = self._root.anchor
        if anchor.startswith("\\\\"):
            raise _unsafe()
        kernel32: Any = ctypes.WinDLL("kernel32", use_last_error=True)
        get_drive_type = kernel32.GetDriveTypeW
        get_drive_type.argtypes = (ctypes.c_wchar_p,)
        get_drive_type.restype = ctypes.c_uint32
        if get_drive_type(anchor) == _DRIVE_REMOTE:
            raise _unsafe()

    def read_bytes(self, *relative_parts: str) -> bytes:
        with _WindowsSafeSession(self._root) as session:
            opened = session.open_file(relative_parts, _GENERIC_READ)
            try:
                return session.read_all(opened)
            finally:
                session.close(opened)

    def exists(self, *relative_parts: str) -> bool:
        try:
            with _WindowsSafeSession(self._root) as session:
                opened = session.open_file(relative_parts, _FILE_READ_ATTRIBUTES)
                session.close(opened)
        except FileNotFoundError:
            return False
        return True

    def delete_project(self, aggregate_name: str, project_id: str) -> None:
        with _WindowsSafeSession(self._root) as session:
            session.delete_file((aggregate_name,), required=True)
            # The index and page documents are derived.  Removing the index is
            # safer than rewriting it by pathname; the next metadata read
            # deterministically rebuilds it from the remaining aggregates.
            session.delete_file(("_metadata_index.json",), required=False)
            session.delete_json_directory(("_pages", project_id))


class _WindowsSafeSession:
    """Pin one root-to-leaf Windows namespace for a complete repository operation."""

    def __init__(self, root: Path) -> None:
        self._root = root
        self._kernel32: Any = ctypes.WinDLL("kernel32", use_last_error=True)
        self._ntdll: Any = ctypes.WinDLL("ntdll")
        self._handles: list[_OpenedHandle] = []
        self._pinned_directories: dict[str, _OpenedHandle] = {}
        self._root_handle: _OpenedHandle | None = None
        self._configure_functions()

    def __enter__(self) -> _WindowsSafeSession:
        try:
            self._pin_absolute_root()
        except Exception:
            self._close_all(suppress_errors=True)
            raise
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self._close_all(suppress_errors=exc is not None)

    def open_file(self, relative_parts: tuple[str, ...], desired_access: int) -> _OpenedHandle:
        parts = _validated_relative_parts(relative_parts)
        parent = self._pin_relative_directories(parts[:-1])
        opened = self._open_relative_validated(
            parent,
            parts[-1],
            self._root.joinpath(*parts),
            desired_access,
            directory=False,
        )
        try:
            self._validate_relative_identity(opened, parts)
            self._after_target_open(opened.path, False)
            return opened
        except Exception:
            self.close(opened)
            raise

    def read_all(self, opened: _OpenedHandle) -> bytes:
        read_file = self._kernel32.ReadFile
        read_file.argtypes = (
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.POINTER(ctypes.c_uint32),
            ctypes.c_void_p,
        )
        read_file.restype = ctypes.c_bool
        chunks: list[bytes] = []
        buffer = ctypes.create_string_buffer(64 * 1024)
        while True:
            amount = ctypes.c_uint32()
            if not read_file(
                ctypes.c_void_p(opened.handle),
                buffer,
                len(buffer),
                ctypes.byref(amount),
                None,
            ):
                raise _unsafe()
            if amount.value == 0:
                return b"".join(chunks)
            chunks.append(buffer.raw[: amount.value])

    def delete_file(self, relative_parts: tuple[str, ...], *, required: bool) -> bool:
        try:
            opened = self.open_file(
                relative_parts,
                _DELETE | _FILE_READ_ATTRIBUTES,
            )
        except FileNotFoundError:
            if required:
                raise
            return False
        try:
            self._mark_for_deletion(opened)
        finally:
            self.close(opened)
        return True

    def delete_json_directory(self, relative_parts: tuple[str, ...]) -> None:
        parts = _validated_relative_parts(relative_parts)
        try:
            parent = self._pin_relative_directories(parts[:-1])
            directory = self._open_relative_validated(
                parent,
                parts[-1],
                self._root.joinpath(*parts),
                _DELETE | _FILE_LIST_DIRECTORY | _FILE_READ_ATTRIBUTES,
                directory=True,
            )
            self._validate_relative_identity(directory, parts)
            self._after_target_open(directory.path, True)
            self._pinned_directories[_canonical_path(directory.path)] = directory
        except FileNotFoundError:
            return
        try:
            names = [
                name for name in self._directory_names(directory) if name.endswith(".json")
            ]
            for name in names:
                self.delete_file((*parts, name), required=True)
            self._mark_for_deletion(directory)
        finally:
            self._pinned_directories.pop(_canonical_path(directory.path), None)
            self.close(directory)

    def close(self, opened: _OpenedHandle) -> None:
        try:
            self._handles.remove(opened)
        except ValueError:
            return
        if not self._kernel32.CloseHandle(ctypes.c_void_p(opened.handle)):
            raise _unsafe()

    def _pin_absolute_root(self) -> None:
        if not self._root.anchor:
            raise _unsafe()
        # Pin the configured owner directory and projects root.  Exact final-
        # path comparison rejects any pre-existing indirection in higher
        # components without requiring access to protected profile ancestors.
        owner_root = self._root.parent
        if owner_root == Path(self._root.anchor):
            raise _unsafe()
        owner = self._pin_absolute_directory(owner_root)
        self._root_handle = self._pin_child_directory(
            owner,
            self._root.name,
            self._root,
        )

    def _pin_relative_directories(self, parts: tuple[str, ...]) -> _OpenedHandle:
        parent = self._root_handle
        if parent is None:
            raise _unsafe()
        current = self._root
        for component in parts:
            current /= component
            opened = self._pin_child_directory(parent, component, current)
            relative = current.relative_to(self._root).parts
            self._validate_relative_identity(opened, relative)
            parent = opened
        return parent

    def _pin_absolute_directory(
        self,
        path: Path,
    ) -> _OpenedHandle:
        key = _canonical_path(path)
        existing = self._pinned_directories.get(key)
        if existing is not None:
            return existing
        opened = self._open_validated(
            path,
            _FILE_READ_ATTRIBUTES | _FILE_TRAVERSE,
            directory=True,
        )
        self._pinned_directories[key] = opened
        self._after_component_open(path)
        return opened

    def _pin_child_directory(
        self,
        parent: _OpenedHandle,
        name: str,
        path: Path,
    ) -> _OpenedHandle:
        key = _canonical_path(path)
        existing = self._pinned_directories.get(key)
        if existing is not None:
            return existing
        opened = self._open_relative_validated(
            parent,
            name,
            path,
            _FILE_READ_ATTRIBUTES | _FILE_TRAVERSE,
            directory=True,
        )
        self._pinned_directories[key] = opened
        self._after_component_open(path)
        return opened

    def _open_validated(
        self,
        path: Path,
        desired_access: int,
        *,
        directory: bool,
    ) -> _OpenedHandle:
        flags = _FILE_FLAG_OPEN_REPARSE_POINT
        if directory:
            flags |= _FILE_FLAG_BACKUP_SEMANTICS
        handle = self._create_file(
            path,
            desired_access,
            flags,
        )
        return self._register_validated_handle(handle, path, directory=directory)

    def _open_relative_validated(
        self,
        parent: _OpenedHandle,
        name: str,
        path: Path,
        desired_access: int,
        *,
        directory: bool,
    ) -> _OpenedHandle:
        if name != _validated_relative_parts((name,))[0]:
            raise _unsafe()
        handle = self._nt_create_file(
            parent.handle,
            name,
            desired_access,
            directory=directory,
        )
        return self._register_validated_handle(handle, path, directory=directory)

    def _register_validated_handle(
        self,
        handle: int,
        path: Path,
        *,
        directory: bool,
    ) -> _OpenedHandle:
        opened = _OpenedHandle(handle, path, path)
        self._handles.append(opened)
        try:
            attributes, final_path = self._handle_identity(handle)
            opened.final_path = final_path
            if attributes & _FILE_ATTRIBUTE_REPARSE_POINT:
                raise _unsafe()
            if bool(attributes & _FILE_ATTRIBUTE_DIRECTORY) is not directory:
                raise _unsafe()
            if _canonical_path(final_path) != _canonical_path(path):
                raise _unsafe()
            return opened
        except Exception:
            self.close(opened)
            raise

    def _nt_create_file(
        self,
        parent_handle: int,
        name: str,
        desired_access: int,
        *,
        directory: bool,
    ) -> int:
        name_buffer = ctypes.create_unicode_buffer(name)
        object_name = _UnicodeString(
            len(name) * ctypes.sizeof(ctypes.c_wchar),
            (len(name) + 1) * ctypes.sizeof(ctypes.c_wchar),
            ctypes.cast(name_buffer, ctypes.c_wchar_p),
        )
        attributes = _ObjectAttributes(
            ctypes.sizeof(_ObjectAttributes),
            ctypes.c_void_p(parent_handle),
            ctypes.pointer(object_name),
            _OBJ_CASE_INSENSITIVE,
            None,
            None,
        )
        io_status = _IoStatusBlock()
        output_handle = ctypes.c_void_p()
        create_options = _FILE_OPEN_REPARSE_POINT | _FILE_SYNCHRONOUS_IO_NONALERT
        create_options |= _FILE_DIRECTORY_FILE if directory else _FILE_NON_DIRECTORY_FILE
        status = int(
            self._ntdll.NtCreateFile(
                ctypes.byref(output_handle),
                desired_access | _SYNCHRONIZE,
                ctypes.byref(attributes),
                ctypes.byref(io_status),
                None,
                0,
                _FILE_SHARE_READ | _FILE_SHARE_WRITE,
                _FILE_OPEN,
                create_options,
                None,
                0,
            )
        )
        if status < 0:
            error = int(self._ntdll.RtlNtStatusToDosError(status))
            if error in {_ERROR_FILE_NOT_FOUND, _ERROR_PATH_NOT_FOUND}:
                raise FileNotFoundError(error, "Project does not exist")
            raise _unsafe()
        if not output_handle.value:
            raise _unsafe()
        return int(output_handle.value)

    def _create_file(
        self,
        path: Path,
        desired_access: int,
        flags: int,
    ) -> int:
        share_mode = _FILE_SHARE_READ | _FILE_SHARE_WRITE
        handle = self._kernel32.CreateFileW(
            _extended_path(path),
            desired_access,
            share_mode,
            None,
            _OPEN_EXISTING,
            flags,
            None,
        )
        invalid = ctypes.c_void_p(-1).value
        if not handle or handle == invalid:
            error = ctypes.get_last_error()
            if error in {_ERROR_FILE_NOT_FOUND, _ERROR_PATH_NOT_FOUND}:
                raise FileNotFoundError(error, "Project does not exist")
            raise _unsafe()
        return int(handle)

    def _validate_relative_identity(
        self,
        opened: _OpenedHandle,
        relative_parts: tuple[str, ...],
    ) -> None:
        root = self._root_handle
        if root is None:
            raise _unsafe()
        attributes, current_root_path = self._handle_identity(root.handle)
        if (
            not attributes & _FILE_ATTRIBUTE_DIRECTORY
            or attributes & _FILE_ATTRIBUTE_REPARSE_POINT
            or _canonical_path(opened.final_path)
            != _canonical_path(current_root_path.joinpath(*relative_parts))
        ):
            raise _unsafe()

    def _handle_identity(self, handle: int) -> tuple[int, Path]:
        raw_handle = ctypes.c_void_p(handle)
        information = _ByHandleFileInformation()
        if not self._kernel32.GetFileInformationByHandle(
            raw_handle,
            ctypes.byref(information),
        ):
            raise _unsafe()
        if self._kernel32.GetFileType(raw_handle) != _FILE_TYPE_DISK:
            raise _unsafe()
        return int(information.attributes), self._final_path(raw_handle)

    def _final_path(self, handle: ctypes.c_void_p) -> Path:
        required = int(
            self._kernel32.GetFinalPathNameByHandleW(
                handle,
                None,
                0,
                _FILE_NAME_NORMALIZED,
            )
        )
        if required < 1:
            raise _unsafe()
        buffer = ctypes.create_unicode_buffer(required + 1)
        written = int(
            self._kernel32.GetFinalPathNameByHandleW(
                handle,
                buffer,
                len(buffer),
                _FILE_NAME_NORMALIZED,
            )
        )
        if written < 1 or written >= len(buffer):
            raise _unsafe()
        raw = buffer.value
        if raw.startswith("\\\\?\\UNC\\"):
            raw = "\\\\" + raw[8:]
        elif raw.startswith("\\\\?\\"):
            raw = raw[4:]
        return Path(raw)

    def _mark_for_deletion(self, opened: _OpenedHandle) -> None:
        disposition = _FileDispositionInfo(1)
        if not self._kernel32.SetFileInformationByHandle(
            ctypes.c_void_p(opened.handle),
            _FILE_DISPOSITION_INFO_CLASS,
            ctypes.byref(disposition),
            ctypes.sizeof(disposition),
        ):
            raise _unsafe()

    def _directory_names(self, opened: _OpenedHandle) -> list[str]:
        buffer = ctypes.create_string_buffer(64 * 1024)
        information_class = _FILE_FULL_DIRECTORY_RESTART_INFO_CLASS
        names: list[str] = []
        while True:
            if not self._kernel32.GetFileInformationByHandleEx(
                ctypes.c_void_p(opened.handle),
                information_class,
                buffer,
                len(buffer),
            ):
                error = ctypes.get_last_error()
                if error in {_ERROR_NO_MORE_FILES, _ERROR_HANDLE_EOF}:
                    return names
                raise _unsafe()
            offset = 0
            while True:
                entry = _FileFullDirectoryInfo.from_buffer(buffer, offset)
                name_address = (
                    ctypes.addressof(buffer)
                    + offset
                    + _FileFullDirectoryInfo.file_name.offset
                )
                name = ctypes.wstring_at(name_address, entry.file_name_length // 2)
                if name not in {".", ".."}:
                    names.append(name)
                if entry.next_entry_offset == 0:
                    break
                offset += entry.next_entry_offset
            information_class = _FILE_FULL_DIRECTORY_INFO_CLASS

    def _close_all(self, *, suppress_errors: bool) -> None:
        failed = False
        while self._handles:
            opened = self._handles.pop()
            if not self._kernel32.CloseHandle(ctypes.c_void_p(opened.handle)):
                failed = True
        self._pinned_directories.clear()
        if failed and not suppress_errors:
            raise _unsafe()

    def _configure_functions(self) -> None:
        self._ntdll.NtCreateFile.argtypes = (
            ctypes.POINTER(ctypes.c_void_p),
            ctypes.c_ulong,
            ctypes.POINTER(_ObjectAttributes),
            ctypes.POINTER(_IoStatusBlock),
            ctypes.c_void_p,
            ctypes.c_ulong,
            ctypes.c_ulong,
            ctypes.c_ulong,
            ctypes.c_ulong,
            ctypes.c_void_p,
            ctypes.c_ulong,
        )
        self._ntdll.NtCreateFile.restype = ctypes.c_long
        self._ntdll.RtlNtStatusToDosError.argtypes = (ctypes.c_long,)
        self._ntdll.RtlNtStatusToDosError.restype = ctypes.c_ulong
        self._kernel32.CreateFileW.argtypes = (
            ctypes.c_wchar_p,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_void_p,
        )
        self._kernel32.CreateFileW.restype = ctypes.c_void_p
        self._kernel32.CloseHandle.argtypes = (ctypes.c_void_p,)
        self._kernel32.CloseHandle.restype = ctypes.c_bool
        self._kernel32.GetFileInformationByHandle.argtypes = (
            ctypes.c_void_p,
            ctypes.POINTER(_ByHandleFileInformation),
        )
        self._kernel32.GetFileInformationByHandle.restype = ctypes.c_bool
        self._kernel32.GetFileType.argtypes = (ctypes.c_void_p,)
        self._kernel32.GetFileType.restype = ctypes.c_uint32
        self._kernel32.GetFinalPathNameByHandleW.argtypes = (
            ctypes.c_void_p,
            ctypes.c_wchar_p,
            ctypes.c_uint32,
            ctypes.c_uint32,
        )
        self._kernel32.GetFinalPathNameByHandleW.restype = ctypes.c_uint32
        self._kernel32.GetFileInformationByHandleEx.argtypes = (
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_void_p,
            ctypes.c_uint32,
        )
        self._kernel32.GetFileInformationByHandleEx.restype = ctypes.c_bool
        self._kernel32.SetFileInformationByHandle.argtypes = (
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_void_p,
            ctypes.c_uint32,
        )
        self._kernel32.SetFileInformationByHandle.restype = ctypes.c_bool

    def _after_component_open(self, path: Path) -> None:
        """Private synchronization seam for deterministic adversarial tests."""

    def _after_target_open(self, path: Path, directory: bool) -> None:
        """Private synchronization seam for deterministic adversarial tests."""


def _validated_relative_parts(parts: tuple[str, ...]) -> tuple[str, ...]:
    if not parts:
        raise _unsafe()
    for part in parts:
        if (
            not part
            or part in {".", ".."}
            or "/" in part
            or "\\" in part
            or ":" in part
            or "\x00" in part
        ):
            raise _unsafe()
    return parts


def _canonical_path(path: Path) -> str:
    return os.path.normcase(os.path.normpath(os.fspath(path)))


def _extended_path(path: Path) -> str:
    raw = os.fspath(path)
    if raw.startswith("\\\\"):
        return "\\\\?\\UNC\\" + raw[2:]
    return "\\\\?\\" + raw
