"""
PyInstaller Extractor v2.0 (Supports pyinstaller 5.1, 5.0.1, 5.0, 4.10, 4.9, 4.8, 4.7, 4.6, 4.5.1, 4.5, 4.4, 4.3, 4.2, 4.1, 4.0, 3.6, 3.5, 3.4, 3.3, 3.2, 3.1, 3.0, 2.1, 2.0)
Author : Extreme Coders
E-mail : extremecoders(at)hotmail(dot)com
Web    : https://0xec.blogspot.com
Date   : 26-March-2020
Url    : https://github.com/extremecoders-re/pyinstxtractor

For any suggestions, leave a comment on
https://forum.tuts4you.com/topic/34455-pyinstaller-extractor/

This script extracts a pyinstaller generated executable file.
Pyinstaller installation is not needed. The script has it all.

For best results, it is recommended to run this script in the
same version of python as was used to create the executable.
This is just to prevent unmarshalling errors(if any) while
extracting the PYZ archive.

Usage : Just copy this script to the directory where your exe resides
        and run the script with the exe file name as a parameter

C:\path\to\exe\>python pyinstxtractor.py <filename>
$ /path/to/exe/python pyinstxtractor.py <filename>

Licensed under GNU General Public License (GPL) v3.
You are free to modify this source.

CHANGELOG
================================================

Version 1.1 (Jan 28, 2014)
-------------------------------------------------
- First Release
- Supports only pyinstaller 2.0

Version 1.2 (Sept 12, 2015)
-------------------------------------------------
- Added support for pyinstaller 2.1 and 3.0 dev
- Cleaned up code
- Script is now more verbose
- Executable extracted within a dedicated sub-directory

(Support for pyinstaller 3.0 dev is experimental)

Version 1.3 (Dec 12, 2015)
-------------------------------------------------
- Added support for pyinstaller 3.0 final
- Script is compatible with both python 2.x & 3.x (Thanks to Moritz Kroll @ Avira Operations GmbH & Co. KG)

Version 1.4 (Jan 19, 2016)
-------------------------------------------------
- Fixed a bug when writing pyc files >= version 3.3 (Thanks to Daniello Alto: https://github.com/Djamana)

Version 1.5 (March 1, 2016)
-------------------------------------------------
- Added support for pyinstaller 3.1 (Thanks to Berwyn Hoyt for reporting)

Version 1.6 (Sept 5, 2016)
-------------------------------------------------
- Added support for pyinstaller 3.2
- Extractor will use a random name while extracting unnamed files.
- For encrypted pyz archives it will dump the contents as is. Previously, the tool would fail.

Version 1.7 (March 13, 2017)
-------------------------------------------------
- Made the script compatible with python 2.6 (Thanks to Ross for reporting)

Version 1.8 (April 28, 2017)
-------------------------------------------------
- Support for sub-directories in .pyz files (Thanks to Moritz Kroll @ Avira Operations GmbH & Co. KG)

Version 1.9 (November 29, 2017)
-------------------------------------------------
- Added support for pyinstaller 3.3
- Display the scripts which are run at entry (Thanks to Michael Gillespie @ malwarehunterteam for the feature request)

Version 2.0 (March 26, 2020)
-------------------------------------------------
- Project migrated to github
- Supports pyinstaller 3.6
- Added support for Python 3.7, 3.8
- The header of all extracted pyc's are now automatically fixed
"""

from __future__ import print_function

import marshal
import os
import struct
import sys
import zlib
from uuid import uuid4 as uniquename

# imp is deprecated in Python3 in favour of importlib
if sys.version_info.major == 3:
    from importlib.util import MAGIC_NUMBER

    pyc_magic = MAGIC_NUMBER
else:
    import imp

    pyc_magic = imp.get_magic()


class CTOCEntry:
    def __init__(
        self, position, cmprsdDataSize, uncmprsdDataSize, cmprsFlag, typeCmprsData, name
    ):
        self.position = position
        self.cmprsdDataSize = cmprsdDataSize
        self.uncmprsdDataSize = uncmprsdDataSize
        self.cmprsFlag = cmprsFlag
        self.typeCmprsData = typeCmprsData
        self.name = name


class PyInstArchive:
    PYINST20_COOKIE_SIZE = 24  # For pyinstaller 2.0
    PYINST21_COOKIE_SIZE = 24 + 64  # For pyinstaller 2.1+
    MAGIC = b"MEI\014\013\012\013\016"  # Magic number which identifies pyinstaller

    def __init__(self, path):
        self.filePath = path

    def open(self):
        try:
            self.fPtr = open(self.filePath, "rb")
            self.fileSize = os.stat(self.filePath).st_size
        except:
            print("[!] Error: Could not open {0}".format(self.filePath))
            return False
        return True

    def close(self):
        try:
            self.fPtr.close()
        except:
            pass

    def checkFile(self):
        print("[+] Processing {0}".format(self.filePath))

        searchChunkSize = 8192
        endPos = self.fileSize
        self.cookiePos = -1

        if endPos < len(self.MAGIC):
            print("[!] Error : File is too short or truncated")
            return False

        while True:
            startPos = endPos - searchChunkSize if endPos >= searchChunkSize else 0
            chunkSize = endPos - startPos

            if chunkSize < len(self.MAGIC):
                break

            self.fPtr.seek(startPos, os.SEEK_SET)
            data = self.fPtr.read(chunkSize)

            offs = data.rfind(self.MAGIC)

            if offs != -1:
                self.cookiePos = startPos + offs
                break

            endPos = startPos + len(self.MAGIC) - 1

            if startPos == 0:
                break

        if self.cookiePos == -1:
            print(
                "[!] Error : Missing cookie, unsupported pyinstaller version or not a pyinstaller archive"
            )
            return False

        self.fPtr.seek(self.cookiePos + self.PYINST20_COOKIE_SIZE, os.SEEK_SET)

        if b"python" in self.fPtr.read(64).lower():
            print("[+] Pyinstaller version: 2.1+")
            self.pyinstVer = 21  # pyinstaller 2.1+
        else:
            self.pyinstVer = 20  # pyinstaller 2.0
            print("[+] Pyinstaller version: 2.0")

        return True

    def getCArchiveInfo(self):
        try:
            if self.pyinstVer == 20:
                self.fPtr.seek(self.cookiePos, os.SEEK_SET)

                # Read CArchive cookie
                (magic, lengthofPackage, toc, tocLen, pyver) = struct.unpack(
                    "!8siiii", self.fPtr.read(self.PYINST20_COOKIE_SIZE)
                )

            elif self.pyinstVer == 21:
                self.fPtr.seek(self.cookiePos, os.SEEK_SET)

                # Read CArchive cookie
                (magic, lengthofPackage, toc, tocLen, pyver, pylibname) = struct.unpack(
                    "!8siiii64s", self.fPtr.read(self.PYINST21_COOKIE_SIZE)
                )
            else:
                raise RuntimeError("Unknown PyInstaller version")

        except:
            print("[!] Error : The file is not a pyinstaller archive")
            return False

        self.pymaj, self.pymin = (
            (pyver // 100, pyver % 100) if pyver >= 100 else (pyver // 10, pyver % 10)
        )
        print("[+] Python version: {0}.{1}".format(self.pymaj, self.pymin))

        # Additional data after the cookie
        tailBytes = (
            self.fileSize
            - self.cookiePos
            - (
                self.PYINST20_COOKIE_SIZE
                if self.pyinstVer == 20
                else self.PYINST21_COOKIE_SIZE
            )
        )

        # Overlay is the data appended at the end of the PE
        self.overlaySize = lengthofPackage + tailBytes
        self.overlayPos = self.fileSize - self.overlaySize
        self.tableOfContentsPos = self.overlayPos + toc
        self.tableOfContentsSize = tocLen

        print("[+] Length of package: {0} bytes".format(lengthofPackage))
        return True

    def parseTOC(self):
        # Go to the table of contents
        self.fPtr.seek(self.tableOfContentsPos, os.SEEK_SET)

        self.tocList = []
        parsedLen = 0

        # Parse table of contents
        while parsedLen < self.tableOfContentsSize:
            (entrySize,) = struct.unpack("!i", self.fPtr.read(4))
            nameLen = struct.calcsize("!iiiiBc")

            (
                entryPos,
                cmprsdDataSize,
                uncmprsdDataSize,
                cmprsFlag,
                typeCmprsData,
                name,
            ) = struct.unpack(
                "!iiiBc{0}s".format(entrySize - nameLen), self.fPtr.read(entrySize - 4)
            )

            name = name.decode("utf-8").rstrip("\0")
            if len(name) == 0:
                name = str(uniquename())
                print(
                    "[!] Warning: Found an unamed file in CArchive. Using random name {0}".format(
                        name
                    )
                )

            self.tocList.append(
                CTOCEntry(
                    self.overlayPos + entryPos,
                    cmprsdDataSize,
                    uncmprsdDataSize,
                    cmprsFlag,
                    typeCmprsData,
                    name,
                )
            )

            parsedLen += entrySize
        print("[+] Found {0} files in CArchive".format(len(self.tocList)))

    def _writeRawData(self, filepath, data):
        nm = (
            filepath.replace("\\", os.path.sep)
            .replace("/", os.path.sep)
            .replace("..", "__")
        )
        nmDir = os.path.dirname(nm)
        if nmDir != "" and not os.path.exists(
            nmDir
        ):  # Check if path exists, create if not
            os.makedirs(nmDir)

        with open(nm, "wb") as f:
            f.write(data)

    def extractFiles(self, extractionDir, no_sanity_check):
        print("[+] Beginning extraction...please standby")

        if not os.path.exists(extractionDir):
            os.mkdir(extractionDir)

        os.chdir(extractionDir)

        for entry in self.tocList:
            self.fPtr.seek(entry.position, os.SEEK_SET)
            data = self.fPtr.read(entry.cmprsdDataSize)

            if entry.cmprsFlag == 1:
                data = zlib.decompress(data)
                # Malware may tamper with the uncompressed size
                # Comment out the assertion in such a case
                if not no_sanity_check:
                    assert len(data) == entry.uncmprsdDataSize  # Sanity Check
                else:
                    if len(data) != entry.uncmprsdDataSize:
                        print(
                            "[!] Uncompressed data size not equal to size defined in header. Maybe tampered."
                        )

            if entry.typeCmprsData == b"d" or entry.typeCmprsData == b"o":
                # d -> ARCHIVE_ITEM_DEPENDENCY
                # o -> ARCHIVE_ITEM_RUNTIME_OPTION
                # These are runtime options, not files
                continue

            basePath = os.path.dirname(entry.name)
            if basePath != "":
                # Check if path exists, create if not
                if not os.path.exists(basePath):
                    os.makedirs(basePath)

            if entry.typeCmprsData == b"s":
                # s -> ARCHIVE_ITEM_PYSOURCE
                # Entry point are expected to be python scripts
                print("[+] Possible entry point: {0}.pyc".format(entry.name))
                self._writePyc(entry.name + ".pyc", data)

            elif entry.typeCmprsData == b"M" or entry.typeCmprsData == b"m":
                # M -> ARCHIVE_ITEM_PYPACKAGE
                # m -> ARCHIVE_ITEM_PYMODULE
                # packages and modules are pyc files with their header's intact
                self._writeRawData(entry.name + ".pyc", data)

            else:
                self._writeRawData(entry.name, data)

                if entry.typeCmprsData == b"z" or entry.typeCmprsData == b"Z":
                    self._extractPyz(entry.name)

    def _writePyc(self, filename, data):
        with open(filename, "wb") as pycFile:
            pycFile.write(pyc_magic)  # pyc magic

            if self.pymaj >= 3 and self.pymin >= 7:  # PEP 552 -- Deterministic pycs
                pycFile.write(b"\0" * 4)  # Bitfield
                pycFile.write(b"\0" * 8)  # (Timestamp + size) || hash

            else:
                pycFile.write(b"\0" * 4)  # Timestamp
                if self.pymaj >= 3 and self.pymin >= 3:
                    pycFile.write(b"\0" * 4)  # Size parameter added in Python 3.3

            pycFile.write(data)

    def _extractPyz(self, name):
        dirName = name + "_extracted"
        # Create a directory for the contents of the pyz
        if not os.path.exists(dirName):
            os.mkdir(dirName)

        with open(name, "rb") as f:
            pyzMagic = f.read(4)
            assert pyzMagic == b"PYZ\0"  # Sanity Check

            pycHeader = f.read(4)  # Python magic value

            # Skip PYZ extraction if not running under the same python version
            if pyc_magic != pycHeader:
                print(
                    "[!] Warning: This script is running in a different Python version than the one used to build the executable."
                )
                print(
                    "[!] Please run this script in Python {0}.{1} to prevent extraction errors during unmarshalling".format(
                        self.pymaj, self.pymin
                    )
                )
                print("[!] Skipping pyz extraction")
                return

            (tocPosition,) = struct.unpack("!i", f.read(4))
            f.seek(tocPosition, os.SEEK_SET)

            try:
                toc = marshal.load(f)
            except:
                print(
                    "[!] Unmarshalling FAILED. Cannot extract {0}. Extracting remaining files.".format(
                        name
                    )
                )
                return

            print("[+] Found {0} files in PYZ archive".format(len(toc)))

            # From pyinstaller 3.1+ toc is a list of tuples
            if type(toc) == list:
                toc = dict(toc)

            for key in toc.keys():
                (ispkg, pos, length) = toc[key]
                f.seek(pos, os.SEEK_SET)
                fileName = key

                try:
                    # for Python > 3.3 some keys are bytes object some are str object
                    fileName = fileName.decode("utf-8")
                except:
                    pass

                # Prevent writing outside dirName
                fileName = fileName.replace("..", "__").replace(".", os.path.sep)

                if ispkg == 1:
                    filePath = os.path.join(dirName, fileName, "__init__.pyc")

                else:
                    filePath = os.path.join(dirName, fileName + ".pyc")

                fileDir = os.path.dirname(filePath)
                if not os.path.exists(fileDir):
                    os.makedirs(fileDir)

                try:
                    data = f.read(length)
                    data = zlib.decompress(data)
                except:
                    print(
                        "[!] Error: Failed to decompress {0}, probably encrypted. Extracting as is.".format(
                            filePath
                        )
                    )
                    open(filePath + ".encrypted", "wb").write(data)
                else:
                    self._writePyc(filePath, data)


def get_pyinstaller_python_version(archive_path):
    arch = PyInstArchive(archive_path)
    result = None

    if arch.open():
        if arch.checkFile():
            if arch.getCArchiveInfo():
                if hasattr(arch, "pymaj") and hasattr(arch, "pymin"):
                    result = arch.pymaj, arch.pymin

    arch.close()
    return result


def extract_arvhive(output_dir, archive_path):
    arch = PyInstArchive(archive_path)
    if arch.open():
        if arch.checkFile():
            if arch.getCArchiveInfo():
                arch.parseTOC()
                arch.extractFiles(output_dir, True)

        arch.close()


def usage():
    print(
        "Usage:\npyinstxtractor.py i <archive_path>\npyinstxtractor.py e <archive_path> <output_dir>"
    )
    exit(1)


def main():
    if len(sys.argv) < 3:
        usage()

    if sys.argv[1] == "i":
        info_mode = True
    elif sys.argv[1] == "e":
        info_mode = False
    else:
        raise ValueError("Invalid first param. Must be 'i' or 'e'")

    archive_path = sys.argv[2]

    if info_mode:
        version = get_pyinstaller_python_version(archive_path)
        if version is not None:
            print(
                "[*] Archive requires python version {}.{}".format(
                    version[0], version[1]
                )
            )
        else:
            print("[!] Failed to detect python version")
    else:
        if len(sys.argv) != 4:
            usage()
        output_dir = sys.argv[3]
        extract_arvhive(output_dir, archive_path)


if __name__ == "__main__":
    main()
