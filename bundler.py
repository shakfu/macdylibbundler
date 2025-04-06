#!/usr/bin/env python3

import os
import sys
import shutil
import subprocess
import tempfile



class Settings:
    overwrite_files = False
    overwrite_dir = False
    create_dir = False
    codesign = True
    bundle_libs = False
    dest_folder = "./libs/"
    inside_lib_path = "@executable_path/../libs/"
    files_to_fix: list[str] = []
    prefixes_to_ignore: list[str] = []
    search_paths: list[str] = []

    @classmethod
    def can_overwrite_files(cls) -> bool:
        return cls.overwrite_files

    @classmethod
    def can_overwrite_dir(cls) -> bool:
        return cls.overwrite_dir

    @classmethod
    def can_create_dir(cls) -> bool:
        return cls.create_dir

    @classmethod
    def can_codesign(cls) -> bool:
        return cls.codesign

    @classmethod
    def bundle_libs_enabled(cls) -> bool:
        return cls.bundle_libs

    @classmethod
    def add_file_to_fix(cls, path: str) -> None:
        cls.files_to_fix.append(path)

    @classmethod
    def file_to_fix_amount(cls) -> int:
        return len(cls.files_to_fix)

    @classmethod
    def file_to_fix(cls, index: int) -> str:
        return cls.files_to_fix[index]

    @classmethod
    def ignore_prefix(cls, prefix: str) -> None:
        if not prefix.endswith("/"):
            prefix += "/"
        cls.prefixes_to_ignore.append(prefix)

    @classmethod
    def is_system_library(cls, prefix: str) -> bool:
        return prefix.startswith("/usr/lib/") or prefix.startswith("/System/Library/")

    @classmethod
    def is_prefix_ignored(cls, prefix: str) -> bool:
        return prefix in cls.prefixes_to_ignore

    @classmethod
    def is_prefix_bundled(cls, prefix: str) -> bool:
        if ".framework" in prefix:
            return False
        if "@executable_path" in prefix:
            return False
        if cls.is_system_library(prefix):
            return False
        if cls.is_prefix_ignored(prefix):
            return False
        return True

    @classmethod
    def add_search_path(cls, path: str) -> None:
        cls.search_paths.append(path)

    @classmethod
    def search_path_amount(cls) -> int:
        return len(cls.search_paths)

    @classmethod
    def search_path(cls, index: int) -> str:
        return cls.search_paths[index]



class Dependency:
    def __init__(self, path: str, dependent_file: str):
        self.filename = ""
        self.prefix = ""
        self.symlinks: list[str] = []
        self.new_name = ""

        # Resolve the original file path
        path = path.strip()
        if self._is_rpath(path):
            original_file = self._search_filename_in_rpaths(path, dependent_file)
        else:
            try:
                original_file = os.path.realpath(path)
            except OSError:
                print(f"WARNING : Cannot resolve path '{path}'")
                original_file = path

        # Check if given path is a symlink
        if original_file != path:
            self.add_symlink(path)

        self.filename = os.path.basename(original_file)
        self.prefix = os.path.dirname(original_file) + "/"

        # Check if this dependency should be bundled
        if not Settings.is_prefix_bundled(self.prefix):
            return

        # Check if the lib is in a known location
        if not self.prefix or not os.path.exists(self.prefix + self.filename):
            if Settings.search_path_amount() == 0:
                self._init_search_paths()

            # Check if file is contained in one of the paths
            for search_path in Settings.search_paths:
                if os.path.exists(search_path + self.filename):
                    print(f"FOUND {self.filename} in {search_path}")
                    self.prefix = search_path
                    break

        # If location still unknown, ask user for search path
        if not Settings.is_prefix_ignored(self.prefix) and (
            not self.prefix or not os.path.exists(self.prefix + self.filename)
        ):
            print(
                f"WARNING : Library {self.filename} has an incomplete name (location unknown)"
            )
            Settings.add_search_path(self._get_user_input_dir_for_file(self.filename))

        self.new_name = self.filename

    def _is_rpath(self, path: str) -> bool:
        return path.startswith("@rpath") or path.startswith("@loader_path")

    def _search_filename_in_rpaths(self, rpath_file: str, dependent_file: str) -> str:
        # Implementation of rpath resolution
        # This is a simplified version - the full implementation would need to handle
        # all the rpath resolution logic from the C++ code
        return rpath_file  # Placeholder

    def _init_search_paths(self) -> None:
        # Initialize search paths from environment variables
        search_paths = []

        for env_var in [
            "DYLD_LIBRARY_PATH",
            "DYLD_FALLBACK_FRAMEWORK_PATH",
            "DYLD_FALLBACK_LIBRARY_PATH",
        ]:
            if env_var in os.environ:
                paths = os.environ[env_var].split(":")
                search_paths.extend(paths)

        for path in search_paths:
            if not path.endswith("/"):
                path += "/"
            Settings.add_search_path(path)

    def _get_user_input_dir_for_file(self, filename: str) -> str:
        # Implementation of user input for missing libraries
        # This is a simplified version - the full implementation would need to handle
        # all the user interaction logic from the C++ code
        return os.getcwd()  # Placeholder

    def get_original_filename(self) -> str:
        return self.filename

    def get_original_path(self) -> str:
        return self.prefix + self.filename

    def get_install_path(self) -> str:
        return Settings.dest_folder + self.new_name

    def get_inner_path(self) -> str:
        return Settings.inside_lib_path + self.new_name

    def add_symlink(self, symlink: str) -> None:
        if symlink not in self.symlinks:
            self.symlinks.append(symlink)

    def get_symlink_amount(self) -> int:
        return len(self.symlinks)

    def get_symlink(self, index: int) -> str:
        return self.symlinks[index]

    def copy_yourself(self) -> None:
        # Copy the file
        shutil.copy2(self.get_original_path(), self.get_install_path())

        # Fix the lib's inner name
        command = f'install_name_tool -id "{self.get_inner_path()}" "{self.get_install_path()}"'
        if subprocess.call(command, shell=True) != 0:
            print(
                f"Error: An error occurred while trying to change identity of library {self.get_install_path()}"
            )
            sys.exit(1)

    def fix_file_that_depends_on_me(self, file_to_fix: str) -> None:
        # Fix dependencies in the file
        self._change_install_name(
            file_to_fix, self.get_original_path(), self.get_inner_path()
        )

        # Fix symlinks
        for symlink in self.symlinks:
            self._change_install_name(file_to_fix, symlink, self.get_inner_path())

    def _change_install_name(
        self, binary_file: str, old_name: str, new_name: str
    ) -> None:
        command = f'install_name_tool -change "{old_name}" "{new_name}" "{binary_file}"'
        if subprocess.call(command, shell=True) != 0:
            print(
                f"Error: An error occurred while trying to fix dependencies of {binary_file}"
            )
            sys.exit(1)

    def merge_if_same_as(self, dep2: "Dependency") -> bool:
        """Compares this dependency with another. If both refer to the same file,
        returns true and merges both entries into one."""
        if dep2.get_original_filename() == self.filename:
            for i in range(self.get_symlink_amount()):
                dep2.add_symlink(self.get_symlink(i))
            return True
        return False

    def print(self):
        print(f" * {self.filename} from {self.prefix}")
        for sym in self.symlinks:
            print(f"    symlink --> {sym}")




class DylibBunder:
    def __init__(self):
        self.deps: list[Dependency] = []
        self.deps_per_file: dict[str, list[Dependency]] = {}
        self.deps_collected: dict[str, bool] = {}
        self.rpaths_per_file: dict[str, list[str]] = {}
        self.rpath_to_fullpath: dict[str, str] = {}

    def collect_dependencies(self, filename: str) -> None:
        """Collect dependencies for a given file."""
        if filename in self.deps_collected:
            return

        self.collect_rpaths(filename)
        lines = self._collect_dependency_lines(filename)

        print(".", end="", flush=True)

        for line in lines:
            print(".", end="", flush=True)
            if not line.startswith("\t"):
                continue  # only lines beginning with a tab interest us
            if ".framework" in line:
                continue  # Ignore frameworks, we cannot handle them

            # trim useless info, keep only library name
            dep_path = line[1 : line.rfind(" (")]
            if Settings.is_system_library(dep_path):
                continue

            self.add_dependency(dep_path, filename)

        self.deps_collected[filename] = True


    def _collect_dependency_lines(self, filename: str) -> list[str]:
        """Execute otool -l and collect dependency lines."""
        if not os.path.exists(filename):
            print(f"Cannot find file {filename} to read its dependencies")
            sys.exit(1)

        cmd = f'otool -l "{filename}"'
        try:
            output = subprocess.check_output(cmd, shell=True, text=True)
        except subprocess.CalledProcessError:
            print(f"Error running otool on {filename}")
            sys.exit(1)

        lines = []
        raw_lines = output.split("\n")
        searching = False

        for line in raw_lines:
            if "cmd LC_LOAD_DYLIB" in line or "cmd LC_REEXPORT_DYLIB" in line:
                if searching:
                    print("ERROR: Failed to find name before next cmd")
                    sys.exit(1)
                searching = True
            elif searching:
                found = line.find("name ")
                if found != -1:
                    lines.append("\t" + line[found + 5 :])
                    searching = False

        return lines


    def collect_rpaths(self, filename: str) -> None:
        """Collect rpaths for a given file."""
        if not os.path.exists(filename):
            print(f"WARNING : can't collect rpaths for nonexistent file '{filename}'")
            return

        cmd = f'otool -l "{filename}"'
        try:
            output = subprocess.check_output(cmd, shell=True, text=True)
        except subprocess.CalledProcessError:
            return

        lc_lines = output.split("\n")
        pos = 0
        read_rpath = False

        while pos < len(lc_lines):
            line = lc_lines[pos]
            pos += 1

            if read_rpath:
                start_pos = line.find("path ")
                end_pos = line.find(" (")
                if start_pos == -1 or end_pos == -1:
                    print("WARNING: Unexpected LC_RPATH format")
                    continue
                start_pos += 5
                rpath = line[start_pos:end_pos]
                if filename not in self.rpaths_per_file:
                    self.rpaths_per_file[filename] = []
                self.rpaths_per_file[filename].append(rpath)
                read_rpath = False
                continue

            if "LC_RPATH" in line:
                read_rpath = True
                pos += 1


    def add_dependency(self, path: str, filename: str) -> None:
        """Add a new dependency."""
        dep = Dependency(path, filename)

        # Check if this library was already added to avoid duplicates
        in_deps = False
        for existing_dep in self.deps:
            if dep.merge_if_same_as(existing_dep):
                in_deps = True
                break

        # Check if this library was already added to deps_per_file[filename]
        in_deps_per_file = False
        deps_in_file = self.deps_per_file.get(filename, [])
        for existing_dep in deps_in_file:
            if dep.merge_if_same_as(existing_dep):
                in_deps_per_file = True
                break

        if not Settings.is_prefix_bundled(dep.prefix):
            return

        if not in_deps:
            self.deps.append(dep)
        if not in_deps_per_file:
            self.deps_per_file[filename] = self.deps_per_file.get(filename, []) + [dep]


    def collect_sub_dependencies(self) -> None:
        """Recursively collect each dependency's dependencies."""
        print(".", end="", flush=True)
        dep_amount = len(self.deps)

        while True:
            dep_amount = len(self.deps)
            for dep in self.deps[:dep_amount]:
                print(".", end="", flush=True)
                original_path = dep.get_original_path()
                if dep._is_rpath(original_path):
                    original_path = dep._search_filename_in_rpaths(
                        original_path, original_path
                    )

                self.collect_dependencies(original_path)

            if len(self.deps) == dep_amount:
                break  # no more dependencies were added on this iteration, stop searching


    def done_with_deps_go(self) -> None:
        """Process all collected dependencies."""
        print()
        for dep in self.deps:
            dep.print()
        print()

        if Settings.bundle_libs_enabled():
            self.create_dest_dir()

            for dep in reversed(self.deps):
                print(f"* Processing dependency {dep.get_install_path()}")
                dep.copy_yourself()
                self.change_lib_paths_on_file(dep.get_install_path())
                self.fix_rpaths_on_file(dep.get_original_path(), dep.get_install_path())
                self.adhoc_codesign(dep.get_install_path())

        for i in range(Settings.file_to_fix_amount() - 1, -1, -1):
            file_to_fix = Settings.file_to_fix(i)
            print(f"* Processing {file_to_fix}")
            try:
                shutil.copy2(file_to_fix, file_to_fix)  # to set write permission
            except shutil.SameFileError:
                pass
            self.change_lib_paths_on_file(file_to_fix)
            self.fix_rpaths_on_file(file_to_fix, file_to_fix)
            self.adhoc_codesign(file_to_fix)


    def create_dest_dir(self) -> None:
        """Create the destination directory if needed."""
        dest_folder = Settings.dest_folder
        print(f"* Checking output directory {dest_folder}")

        dest_exists = os.path.exists(dest_folder)

        if dest_exists and Settings.can_overwrite_dir():
            print(f"* Erasing old output directory {dest_folder}")
            try:
                shutil.rmtree(dest_folder)
            except OSError:
                print("Error: An error occurred while attempting to overwrite dest folder.")
                sys.exit(1)
            dest_exists = False

        if not dest_exists:
            if Settings.can_create_dir():
                print(f"* Creating output directory {dest_folder}")
                try:
                    os.makedirs(dest_folder)
                except OSError:
                    print("Error: An error occurred while creating dest folder.")
                    sys.exit(1)
            else:
                print("Error: Dest folder does not exist. Create it or pass the appropriate flag for automatic dest dir creation.")
                sys.exit(1)


    def change_lib_paths_on_file(self, file_to_fix: str) -> None:
        """Change library paths in a file."""
        if file_to_fix not in self.deps_collected:
            print("    ", end="")
            self.collect_dependencies(file_to_fix)
            print()

        print(f"  * Fixing dependencies on {file_to_fix}")
        deps_in_file = self.deps_per_file.get(file_to_fix, [])
        for dep in deps_in_file:
            dep.fix_file_that_depends_on_me(file_to_fix)


    def fix_rpaths_on_file(self, original_file: str, file_to_fix: str) -> None:
        """Fix rpaths in a file."""
        rpaths_to_fix = self.rpaths_per_file.get(original_file, [])

        for rpath in rpaths_to_fix:
            command = f'install_name_tool -rpath "{rpath}" "{Settings.inside_lib_path}" "{file_to_fix}"'
            if subprocess.call(command, shell=True) != 0:
                print(f"Error: An error occurred while trying to fix dependencies of {file_to_fix}")


    def adhoc_codesign(self, file: str) -> None:
        """Apply ad-hoc code signing to a file."""
        if not Settings.can_codesign():
            return

        sign_command = f'codesign --force --deep --preserve-metadata=entitlements,requirements,flags,runtime --sign - "{file}"'
        if subprocess.call(sign_command, shell=True) != 0:
            print(
                f"  * Error: An error occurred while applying ad-hoc signature to {file}. Attempting workaround"
            )

            try:
                machine = subprocess.check_output("machine", shell=True, text=True)
                is_arm = "arm" in machine
            except subprocess.CalledProcessError:
                is_arm = False

            temp_dir = os.path.join(os.getenv("TMPDIR", "/tmp"), "dylibbundler.XXXXXXXX")
            filename = os.path.basename(file)
            try:
                temp_dir = tempfile.mkdtemp(prefix="dylibbundler.")
                temp_file = os.path.join(temp_dir, filename)

                # Copy file to temp location
                shutil.copy2(file, temp_file)
                # Move it back
                shutil.move(temp_file, file)
                # Remove temp dir
                shutil.rmtree(temp_dir)
                # Try signing again
                if subprocess.call(sign_command, shell=True) != 0:
                    print(
                        f"  * Error: An error occurred while applying ad-hoc signature to {file}"
                    )
                    if is_arm:
                        sys.exit(1)
            except Exception as e:
                print(f"  * Error: {str(e)}")
                if is_arm:
                    sys.exit(1)

    def show_help(self):
        print("dylibbundler 1.0.5")
        print(
            "dylibbundler is a utility that helps bundle dynamic libraries inside macOS app bundles."
        )
        print("-x, --fix-file <file to fix (executable or app plug-in)>")
        print("-b, --bundle-deps")
        print("-d, --dest-dir <directory to send bundled libraries (relative to cwd)>")
        print(
            "-p, --install-path <'inner' path of bundled libraries (usually relative to executable, by default '@executable_path/../libs/')>"
        )
        print("-s, --search-path <directory to add to list of locations searched>")
        print("-of, --overwrite-files (allow overwriting files in output directory)")
        print(
            "-od, --overwrite-dir (totally overwrite output directory if it already exists. implies --create-dir)"
        )
        print("-cd, --create-dir (creates output directory if necessary)")
        print("-ns, --no-codesign (disables ad-hoc codesigning)")
        print("-i, --ignore <location to ignore> (will ignore libraries in this directory)")
        print("-h, --help")

    def process(self):
        # Parse command line arguments
        i = 1
        while i < len(sys.argv):
            arg = sys.argv[i]
            if arg in ["-x", "--fix-file"]:
                i += 1
                Settings.add_file_to_fix(sys.argv[i])
            elif arg in ["-b", "--bundle-deps"]:
                Settings.bundle_libs = True
            elif arg in ["-p", "--install-path"]:
                i += 1
                Settings.inside_lib_path = sys.argv[i]
            elif arg in ["-i", "--ignore"]:
                i += 1
                Settings.ignore_prefix(sys.argv[i])
            elif arg in ["-d", "--dest-dir"]:
                i += 1
                Settings.dest_folder = sys.argv[i]
            elif arg in ["-of", "--overwrite-files"]:
                Settings.overwrite_files = True
            elif arg in ["-od", "--overwrite-dir"]:
                Settings.overwrite_dir = True
                Settings.create_dir = True
            elif arg in ["-cd", "--create-dir"]:
                Settings.create_dir = True
            elif arg in ["-ns", "--no-codesign"]:
                Settings.codesign = False
            elif arg in ["-s", "--search-path"]:
                i += 1
                Settings.add_search_path(sys.argv[i])
            elif arg in ["-h", "--help"]:
                self.show_help()
                sys.exit(0)
            else:
                print(f"Unknown flag {arg}")
                self.show_help()
                sys.exit(1)
            i += 1

        if not Settings.bundle_libs_enabled() and Settings.file_to_fix_amount() < 1:
            self.show_help()
            sys.exit(0)

        print("* Collecting dependencies", end="", flush=True)

        # Collect dependencies
        for i in range(Settings.file_to_fix_amount()):
            self.collect_dependencies(Settings.file_to_fix(i))

        self.collect_sub_dependencies()
        self.done_with_deps_go()







if __name__ == "__main__":
    DylibBunder().process()
