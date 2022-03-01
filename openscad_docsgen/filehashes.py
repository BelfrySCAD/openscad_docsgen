from __future__ import print_function

import os
import os.path
import sys
import hashlib

class FileHashes(object):
    def __init__(self, hashfile):
        self.hashfile = hashfile
        self.load()

    def _sha256sum(self, filename):
        """Calculate the hash value for the given file's contents.
        """
        h = hashlib.sha256()
        b = bytearray(128*1024)
        mv = memoryview(b)
        try:
            with open(filename, 'rb', buffering=0) as f:
                for n in iter(lambda : f.readinto(mv), 0):
                    h.update(mv[:n])
        except FileNotFoundError as e:
            pass
        return h.hexdigest()

    def load(self):
        """Reads all known file hash values from the hashes file.
        """
        self.file_hashes = {}
        if os.path.isfile(self.hashfile):
            try:
                with open(self.hashfile, "r") as f:
                    for line in f.readlines():
                        filename, hashstr = line.strip().split("|")
                        self.file_hashes[filename] = hashstr
            except ValueError as e:
                print("Corrrupt hashes file.  Ignoring.", file=sys.stderr)
                sys.stderr.flush()
                self.file_hashes = {}

    def save(self):
        """Writes out all known hash values.
        """
        os.makedirs(os.path.dirname(self.hashfile), exist_ok=True)
        with open(self.hashfile, "w") as f:
            for filename, hashstr in self.file_hashes.items():
                f.write("{}|{}\n".format(filename, hashstr))

    def is_changed(self, filename):
        """Returns True if the given file matches it's recorded hash value.
        Updates the hash value in memory for the file if it doesn't match.
        Does NOT save hash values to disk.
        """
        newhash = self._sha256sum(filename)
        if filename not in self.file_hashes:
            self.file_hashes[filename] = newhash
            return True
        oldhash = self.file_hashes[filename]
        if oldhash != newhash:
            self.file_hashes[filename] = newhash
            return True
        return False

    def invalidate(self,filename):
        """Invalidates the has value for the given file.
        """
        self.file_hashes.pop(filename)



# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
