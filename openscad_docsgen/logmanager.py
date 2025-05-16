from __future__ import print_function

import os
import re
import tempfile
import subprocess
import sys
import shutil
import platform

from .errorlog import errorlog, ErrorLog


class LogRequest(object):
    _echo_re = re.compile(r"ECHO:\s*(.+)$")

    def __init__(self, src_file, src_line, script_lines, starting_cb=None, completion_cb=None, verbose=False):
        self.src_file = src_file
        self.src_line = src_line
        self.script_lines = [
            line[2:] if line.startswith("--") else line
            for line in script_lines
        ]
        self.starting_cb = starting_cb
        self.completion_cb = completion_cb
        self.verbose = verbose

        self.complete = False
        self.status = "INCOMPLETE"
        self.success = False
        self.cmdline = []
        self.return_code = None
        self.stdout = []
        self.stderr = []
        self.echos = []
        self.warnings = []
        self.errors = []

    def starting(self):
        if self.verbose:
            print(f"Starting log request for {self.src_file}:{self.src_line}")
        if self.starting_cb:
            self.starting_cb(self)

    def completed(self, status, stdout=None, stderr=None, return_code=None):
        self.complete = True
        self.status = status
        self.success = (status == "SUCCESS")
        self.return_code = return_code
        self.stdout = stdout or []
        self.stderr = stderr or []
        self.echos = []
        self.warnings = []
        self.errors = []

        # Parse ECHO from stdout, warnings/errors from stderr
        for line in self.stdout:
            if self.verbose:
                print(f"Parsing stdout line: {line}")
            match = self._echo_re.match(line)
            if match:
                echo_content = match.group(1)
                if self.verbose:
                    print(f"Matched ECHO: {echo_content}")
                self.echos.append(echo_content)
        for line in self.stderr:
            if self.verbose:
                print(f"Parsing stderr line: {line}")
            if "WARNING:" in line:
                self.warnings.append(line)
            elif "ERROR:" in line:
                self.errors.append(line)

        if self.verbose:
            print(f"Log request completed: {self.status}, Echos: {self.echos}, Warnings: {self.warnings}, Errors: {self.errors}")

        if self.completion_cb:
            self.completion_cb(self)


class LogManager(object):
    def __init__(self):
        self.requests = []
        self.test_only = False

    def find_openscad_binary(self):
        exepath = shutil.which("openscad")
        if exepath is not None:
            if self.test_only:
                print(f"Found OpenSCAD in PATH: {exepath}")
            return exepath
        # Platform-specific fallback paths
        system = platform.system()
        if system == "Darwin":  # macOS
            exepath = shutil.which("/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD")
            if exepath is not None:
                if self.test_only:
                    print(f"Found OpenSCAD in macOS path: {exepath}")
                return exepath
        elif system == "Windows":
            test_paths = [
                r"C:\Program Files\OpenSCAD\openscad.com",
                r"C:\Program Files\OpenSCAD\openscad.exe",
                r"C:\Program Files (x86)\OpenSCAD\openscad.com",
                r"C:\Program Files (x86)\OpenSCAD\openscad.exe",
            ]
            for p in test_paths:
                exepath = shutil.which(p)
                if exepath is not None:
                    if self.test_only:
                        print(f"Found OpenSCAD in Windows path: {exepath}")
                    return exepath
        else:  # Linux or other
            test_paths = [
                "/usr/bin/openscad",
                "/usr/local/bin/openscad",
                "/opt/openscad/bin/openscad"
            ]
            for p in test_paths:
                exepath = shutil.which(p)
                if exepath is not None:
                    if self.test_only:
                        print(f"Found OpenSCAD in Linux/other path: {exepath}")
                    return exepath
        raise Exception(
            "Can't find OpenSCAD executable. Please install OpenSCAD and ensure it is in your system PATH "
            "or located in a standard directory (e.g., /Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD on macOS, "
            "C:\\Program Files\\OpenSCAD\\openscad.exe on Windows, /usr/bin/openscad on Linux)."
        )

    def purge_requests(self):
        self.requests = []

    def new_request(self, src_file, src_line, script_lines, starting_cb=None, completion_cb=None, verbose=False):
        req = LogRequest(src_file, src_line, script_lines, starting_cb, completion_cb, verbose=verbose)
        self.requests.append(req)
        if verbose:
            print(f"New log request created for {src_file}:{src_line}")
        return req

    def process_request(self, req):
        req.starting()
        try:
            openscad_bin = self.find_openscad_binary()
        except Exception as e:
            error_msg = str(e)
            req.completed("FAIL", [], [error_msg], -1)
            errorlog.add_entry(req.src_file, req.src_line, error_msg, ErrorLog.FAIL)
            return

        # Create a temporary script file
        with tempfile.NamedTemporaryFile(suffix=".scad", delete=False, mode="w") as temp_file:
            for line in req.script_lines:
                temp_file.write(line + "\n")
            script_file = temp_file.name

        try:
            # Run OpenSCAD with no output file to capture ECHO output

            #openscad_bin = shutil.which("openscad")
            #print (f"openscad_bin",openscad_bin)
            #openscad_bin = "/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD"
            #cmdline = ["/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD", "-o", "/dev/null", script_file]
            cmdline = [openscad_bin, "-o", "-", "--export-format=echo", script_file]
            #cmdline = ["openscad", "-o", "/dev/null", script_file]
            if self.test_only:
                cmdline.append("--hardwarnings")
            if req.verbose:
                print(f"Executing: {' '.join(cmdline)}")
            process = subprocess.run(
                cmdline,
                capture_output=True,
                text=True,
                timeout=10
            )
            stdout = process.stdout.splitlines()
            stderr = process.stderr.splitlines()
            return_code = process.returncode

            if req.verbose:
                print(f"OpenSCAD return code: {return_code}")
                print(f"Stdout: {stdout}")
                print(f"Stderr: {stderr}")

            if return_code != 0 or any("ERROR:" in line for line in stderr):
                req.completed("FAIL", stdout, stderr, return_code)
            else:
                req.completed("SUCCESS", stdout, stderr, return_code)

        except subprocess.TimeoutExpired:
            req.completed("FAIL", [], ["Timeout expired"], -1)
            errorlog.add_entry(req.src_file, req.src_line, "OpenSCAD execution timed out", ErrorLog.FAIL)
        except Exception as e:
            req.completed("FAIL", [], [str(e)], -1)
            errorlog.add_entry(req.src_file, req.src_line, f"OpenSCAD execution failed: {str(e)}", ErrorLog.FAIL)
        finally:
            if os.path.exists(script_file):
                os.unlink(script_file)

    def process_requests(self, test_only=False):
        self.test_only = test_only
        if not self.requests:
            if self.test_only:
                print("No log requests to process")
        for req in self.requests:
            self.process_request(req)
        self.requests = []

log_manager = LogManager()