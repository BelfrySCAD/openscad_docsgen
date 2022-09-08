#!/usr/bin/env python3

from __future__ import print_function

import os
import sys
import glob
import os.path
import argparse

from .errorlog import ErrorLog, errorlog
from .parser import DocsGenParser, DocsGenException
from .target import default_target, target_classes


class Options(object):
    def __init__(self, args):
        self.files = args.srcfiles
        self.target_profile = args.target_profile
        self.project_name = args.project_name
        self.docs_dir = args.docs_dir.rstrip("/")
        self.quiet = args.quiet
        self.force = args.force
        self.strict = args.strict
        self.test_only = args.test_only
        self.gen_imgs = not args.no_images
        self.gen_files = args.gen_files
        self.gen_toc = args.gen_toc
        self.gen_index = args.gen_index
        self.gen_topics = args.gen_topics
        self.gen_cheat = args.gen_cheat
        self.gen_sidebar = args.gen_sidebar
        self.report = args.report
        self.dump_tree = args.dump_tree
        self.png_animation = args.png_animation
        self.update_target()

    def set_target(self, targ):
        if targ not in target_classes:
            return False
        self.target_profile = targ
        return True

    def update_target(self):
        self.target = target_classes[self.target_profile](
            project_name=self.project_name,
            docs_dir=self.docs_dir
        )

def processFiles(opts):
    docsgen = DocsGenParser(opts)
    # DocsGenParser may change opts settings, based on the _rc file.

    if not opts.files:
        opts.files = glob.glob("*.scad")

    fail = False
    for infile in opts.files:
        if not os.path.exists(infile):
            print("{} does not exist.".format(infile))
            fail = True
        elif not os.path.isfile(infile):
            print("{} is not a file.".format(infile))
            fail = True
        elif not os.access(infile, os.R_OK):
            print("{} is not readable.".format(infile))
            fail = True
    if fail:
        sys.exit(-1)

    docsgen.parse_files(opts.files, False)

    if opts.dump_tree:
        docsgen.dump_full_tree()

    if opts.gen_files or opts.test_only:
        docsgen.write_docs_files()
    if opts.gen_toc:
        docsgen.write_toc_file()
    if opts.gen_index:
        docsgen.write_index_file()
    if opts.gen_topics:
        docsgen.write_topics_file()
    if opts.gen_cheat:
        docsgen.write_cheatsheet_file()
    if opts.gen_sidebar:
        docsgen.write_sidebar_file()

    if opts.report:
        errorlog.write_report()
    if errorlog.has_errors:
        print("WARNING: Errors encountered.", file=sys.stderr)
        sys.exit(-1)


def main():
    target_profiles = ["githubwiki", "stdwiki"]

    parser = argparse.ArgumentParser(prog='openscad-docsgen')
    parser.add_argument('-D', '--docs-dir', default="docs",
                        help='The directory to put generated documentation in.')
    parser.add_argument('-T', '--test-only', action="store_true",
                        help="If given, don't generate images, but do try executing the scripts.")
    parser.add_argument('-q', '--quiet', action="store_true",
                        help="Suppress printing of progress data.")
    parser.add_argument('-S', '--strict', action="store_true",
                        help="If given, require File/LibFile and Section headers.")
    parser.add_argument('-f', '--force', action="store_true",
                        help='If given, force regeneration of images.')
    parser.add_argument('-n', '--no-images', action="store_true",
                        help='If given, skips image generation.')
    parser.add_argument('-m', '--gen-files', action="store_true",
                        help='If given, generate documents for each source file.')
    parser.add_argument('-i', '--gen-index', action="store_true",
                        help='If given, generate alphabetical Index.md file.')
    parser.add_argument('-I', '--gen-topics', action="store_true",
                        help='If given, generate Topics.md topics index file.')
    parser.add_argument('-t', '--gen-toc', action="store_true",
                        help='If given, generate TOC.md table of contents file.')
    parser.add_argument('-c', '--gen-cheat', action="store_true",
                        help='If given, generate CheatSheet.md file with all Usage lines.')
    parser.add_argument('-s', '--gen_sidebar', action="store_true",
                        help="If given, generate _Sidebar.md file index.")
    parser.add_argument('-a', '--png-animation', action="store_true",
                        help='If given, animations are created using animated PNGs instead of GIFs.')
    parser.add_argument('-P', '--project-name',
                        help='If given, sets the name of the project to be shown in titles.')
    parser.add_argument('-r', '--report', action="store_true",
                        help='If given, write all warnings and errors to docsgen_report.json')
    parser.add_argument('-d', '--dump-tree', action="store_true",
                        help='If given, dumps the documentation tree for debugging.')
    parser.add_argument('-p', '--target-profile', choices=target_classes.keys(), default=default_target,
                        help='Sets the output target profile.  Defaults to "{}"'.format(default_target))
    parser.add_argument('srcfiles', nargs='*', help='List of input source files.')
    opts = Options(parser.parse_args())

    try:
        processFiles(opts)
    except DocsGenException as e:
        print(e)
        sys.exit(-1)
    except OSError as e:
        print(e)
        sys.exit(-1)
    except KeyboardInterrupt as e:
        print(" Aborting.", file=sys.stderr)
        sys.exit(-1)

    sys.exit(0)


if __name__ == "__main__":
    main()


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
