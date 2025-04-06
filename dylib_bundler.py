"""dylib_bundler.py

A python translation of macdylibbundler

"""

from pathlib import Path
from copy import deepcopy
from typing import Optional


class Settings:
    """settings class"""

    def __init__(
        self,
        dest_dir: str = "./libs/",
        overwrite_files: bool = False,
        overwrite_dir: bool = False,
        create_dir: bool = False,
        codesign: bool = True,
        bundle_libs: bool = True,
        inside_lib_path: str = "@executable_path/../libs/",
        files_to_fix: Optional[list[str]] = None,
        prefixes_to_ignore: Optional[list[str]] = None,
        search_paths: Optional[list[str]] = None,
    ):
        self.dest_dir = self.ensure_endswith_slash(dest_dir)
        self.can_overwrite_files = overwrite_files
        self.overwrite_dir = overwrite_dir
        self.create_dir = create_dir
        self.codesign = codesign
        self.bundle_libs = bundle_libs
        self.inside_lib_path = self.ensure_endswith_slash(inside_lib_path)
        self.files_to_fix = files_to_fix or []
        self.prefixes_to_ignore = prefixes_to_ignore or []
        self.search_paths = search_paths or []

    def ensure_endswith_slash(self, path: str):
        """ensure path endswith '/'"""
        if not path.endswith("/"):
            path += "/"
        return path

    def is_system_library(self, prefix: str) -> bool:
        """is system library"""
        return prefix in [
            "/usr/lib/",
            "/System/Library/",
        ]

    def is_prefix_bundled(self, prefix: str) -> bool:
        """is prefix bundled"""
        return not any(
            [
                ".framework" in prefix,
                "@executable_path" in prefix,
                self.is_system_library(prefix),
                self.is_prefix_ignored(prefix),
            ]
        )

    def is_prefix_ignored(self, prefix: str) -> bool:
        """is prefix ignored"""
        return prefix in self.prefixes_to_ignore

    def add_prefix_to_ignore(self, prefix: str):
        """ignore prefix"""
        self.prefixes_to_ignore.append(self.ensure_endswith_slash(prefix))


class Dependency:
    """
    dependency class
    """

    # origin
    filename: str
    prefix: str
    symlinks: list[str]

    # installation
    new_name: str

    def __init__(self, path: str | Path, dependent_file: str | Path):
        self.path = Path(path)
        self.dependent_file = Path(dependent_file)

    def print(self):
        """print something"""

    def get_original_filename(self) -> str:
        """retrieve original filename"""
        return self.filename

    def get_original_path(self) -> str:
        """retrieve original path"""
        return f"{self.prefix}{self.filename}"

    def get_install_path(self) -> str:
        """get install path"""
        return ""

    def get_inner_path(self) -> str:
        """get inner path"""
        return ""

    def add_symlink(self, link: str):
        """add symlink"""
        self.symlinks.append(link)

    def get_symlink_amount(self) -> int:
        """get number of symlinks"""
        return len(self.symlinks)

    def get_symlink(self, index: int):
        """get symlink by index"""
        return self.symlinks[index]

    def get_prefix(self) -> str:
        """get prefix"""
        return self.prefix

    def copy_yourself(self):
        """get copy"""
        return deepcopy(self)

    def fix_file_that_depends_on_me(self, afile: str):
        """fix file that depends on me"""

    def merge_if_same_as(self, dep2: "Dependency") -> bool:
        """Compares the given dependency with this one.

        If both refer to the same file, returns true and merges
        both entries into one.
        """
        return bool(dep2)


# DylibBundler


class DylibBundler:
    """main class"""

    def __init__(
        self,
        target: str,
        dest_dir: str = "./libs/",
        overwrite_dir: bool = False,
    ):
        self.target = target  # (executable or plug-in filepath)
        self.dest_dir = dest_dir
        self.setting = Settings(
            dest_dir=dest_dir,
            files_to_fix=[target],
            overwrite_dir=overwrite_dir,
        )
        self.deps_collected: dict[str, bool] = {}


    # def collect_dependencies(self, filename: str):
    #     """collect dependencies"""
    #     if filename in self.deps_collected:
    #         return

    #     self.collect_rpaths(filename)





# def collect_dependencies(filename: str):
#     """collect dependencies"""
#     assert filename


def collect_subdependencies():
    """collect subdependencies"""


def done_with_deps_go():
    """done with deps go"""


def is_rpath(path: str) -> bool:
    """path is rpath"""
    return any(
        [
            "@rpath" in path,
            "@loader_path" in path,
        ]
    )


def search_filename_in_rpaths(rpath_file: str, dependent_file: str) -> str:
    """search filename in rpaths"""
    assert rpath_file
    assert dependent_file
    return "result"


def search_filename_in_rpaths2(rpath_dep: str) -> str:
    """search filename in rpaths 2"""
    return rpath_dep


## utils
