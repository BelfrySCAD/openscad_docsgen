#!/usr/bin/env python3

from __future__ import print_function

import os
import sys
import yaml
import glob
import os.path
import argparse

from .errorlog import errorlog, ErrorLog
from .imagemanager import image_manager
from .filehashes import FileHashes


class MarkdownImageGen(object):
    HASHFILE = ".source_hashes"

    def __init__(self, opts):
        self.opts = opts
        self.filehashes = FileHashes(os.path.join(self.opts.docs_dir, self.HASHFILE))

    def img_started(self, req):
        print("  {}... ".format(os.path.basename(req.image_file)), end='')
        sys.stdout.flush()

    def img_completed(self, req):
        if req.success:
            if req.status == "SKIP":
                print()
            else:
                print(req.status)
            sys.stdout.flush()
            return
        out = "\n\n"
        for line in req.echos:
            out += line + "\n"
        for line in req.warnings:
            out += line + "\n"
        for line in req.errors:
            out += line + "\n"
        out += "//////////////////////////////////////////////////////////////////////\n"
        out += "// LibFile: {}  Line: {}  Image: {}\n".format(
            req.src_file, req.src_line, os.path.basename(req.image_file)
        )
        out += "//////////////////////////////////////////////////////////////////////\n"
        for line in req.script_lines:
            out += line + "\n"
        out += "//////////////////////////////////////////////////////////////////////\n"
        errorlog.add_entry(req.src_file, req.src_line, out, ErrorLog.FAIL)
        sys.stderr.flush()

    def processFiles(self, srcfiles):
        opts = self.opts
        image_root = os.path.join(opts.docs_dir, opts.image_root)
        for infile in srcfiles:
            fileroot = os.path.splitext(os.path.basename(infile))[0]
            outfile = os.path.join(opts.docs_dir, opts.file_prefix + fileroot + ".md")
            print(outfile)
            sys.stdout.flush()

            out = []
            with open(infile, "r") as f:
                script = []
                extyp = ""
                in_script = False
                imgnum = 0
                show_script = True
                linenum = -1
                for line in f.readlines():
                    linenum += 1
                    line = line.rstrip("\n")
                    if line.startswith("```openscad"):
                        in_script = True;
                        if "-" in line:
                            extyp = line.split("-")[1]
                        else:
                            extyp = ""
                        show_script = "ImgOnly" not in extyp
                        script = []
                        imgnum = imgnum + 1
                    elif in_script:
                        if line == "```":
                            in_script = False
                            if opts.png_animation:
                                fext = "png"
                            elif any(x in extyp for x in ("Anim", "Spin")):
                                fext = "gif"
                            else:
                                fext = "png"
                            fname = "{}_{}.{}".format(fileroot, imgnum, fext)
                            img_rel_url = os.path.join(opts.image_root, fname)
                            imgfile = os.path.join(opts.docs_dir, img_rel_url)
                            image_manager.new_request(
                                fileroot+".md", linenum,
                                imgfile, script, extyp,
                                starting_cb=self.img_started,
                                completion_cb=self.img_completed
                            )
                            if show_script:
                                out.append("```openscad")
                                out.extend(script)
                                out.append("```")
                            out.append("![Figure {}]({})".format(imgnum, img_rel_url))
                            show_script = True
                            extyp = ""
                        else:
                            script.append(line)
                    else:
                        out.append(line)

            if not opts.test_only:
                with open(outfile, "w") as f:
                    for line in out:
                        print(line, file=f)

            has_changed = self.filehashes.is_changed(infile)
            if opts.force or opts.test_only or has_changed:
                image_manager.process_requests(test_only=opts.test_only)
            image_manager.purge_requests()

            if errorlog.file_has_errors(infile):
                self.filehashes.invalidate(infile)
            self.filehashes.save()


def mdimggen_main():
    rcfile = ".openscad_mdimggen_rc"
    defaults = {}
    if os.path.exists(rcfile):
        with open(rcfile, "r") as f:
            data = yaml.safe_load(f)
        if data is not None:
            defaults = data

    parser = argparse.ArgumentParser(prog='openscad-mdimggen')
    parser.add_argument('-D', '--docs-dir', default=defaults.get("docs_dir", "docs"),
                        help='The directory to put generated documentation in.')
    parser.add_argument('-P', '--file-prefix', default=defaults.get("file_prefix", ""),
                        help='The prefix to put in front of each output markdown file.')
    parser.add_argument('-T', '--test-only', action="store_true",
                        help="If given, don't generate images, but do try executing the scripts.")
    parser.add_argument('-I', '--image_root', default=defaults.get("image_root", "images"),
                        help='The directory to put generated images in.')
    parser.add_argument('-f', '--force', action="store_true",
                        help='If given, force regeneration of images.')
    parser.add_argument('-a', '--png-animation', action="store_true",
                        default=defaults.get("png_animations", True),
                        help='If given, animations are created using animated PNGs instead of GIFs.')
    parser.add_argument('srcfiles', nargs='*', help='List of input markdown files.')
    args = parser.parse_args()

    if not args.srcfiles:
        srcfiles = defaults.get("source_files", [])
        if isinstance(srcfiles, str):
            args.srcfiles = glob.glob(srcfiles)
        elif isinstance(srcfiles, list):
            args.srcfiles = []
            for srcfile in srcfiles:
                if isinstance(srcfile, str):
                    args.srcfiles.extend(glob.glob(srcfile))
        if not args.srcfiles:
            print("No files to parse.  Aborting.", file=sys.stderr)
            sys.exit(-1)

    try:
        mdimggen = MarkdownImageGen(args)
        mdimggen.processFiles(args.srcfiles)
    except OSError as e:
        print(e)
        sys.exit(-1)
    except KeyboardInterrupt as e:
        print(" Aborting.", file=sys.stderr)
        sys.exit(-1)

    if errorlog.has_errors:
        print("WARNING: Errors encountered.", file=sys.stderr)
        sys.exit(-1)

    sys.exit(0)


if __name__ == "__main__":
    mdimggen_main()


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
