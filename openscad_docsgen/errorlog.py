from __future__ import print_function

import sys
import json

class ErrorLog(object):
    NOTE = "notice"
    WARN = "warning"
    FAIL = "error"

    REPORT_FILE = "docsgen_report.json"

    def __init__(self):
        self.errlist = []
        self.has_errors = False
        self.badfiles = {}

    def add_entry(self, file, line, msg, level):
        self.errlist.append( (file, line, msg, level) )
        self.badfiles[file] = 1
        print("\n!! {} at {}:{}: {}".format(level.upper(), file, line, msg) , file=sys.stderr)
        sys.stderr.flush()
        if level == self.FAIL:
            self.has_errors = True

    def write_report(self):
        report = [
            {
                "file": file,
                "line": line,
                "title": "DocsGen {}".format(level),
                "message": msg,
                "annotation_level": level
            }
            for file, line, msg, level in self.errlist
        ]
        with open(self.REPORT_FILE, "w") as f:
            f.write(json.dumps(report, sort_keys=False, indent=4))

    def file_has_errors(self, file):
        return file in self.badfiles

errorlog = ErrorLog()


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
