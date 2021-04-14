#!/usr/bin/env python3

from __future__ import print_function

import sys
import os
import os.path
import argparse

from .blocks import DocsGenParser, DocsGenException, errorlog

def processFiles(
    files, docs_dir,
    strict=False,
    test_only=False,
    force=False,
    gen_imgs=False,
    gen_md=False,
    gen_toc=False,
    gen_index=False,
    gen_topics=False,
    gen_cheat=False,
    report=False,
    dump_tree=False
):
    fail = False
    for infile in files:
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

    docsgen = DocsGenParser(strict=strict)
    for infile in files:
        docsgen.parse_file(
            infile,
            images=gen_imgs and gen_md,
            test_only=test_only,
            force=force
        )

    if not test_only and gen_md:
        docsgen.write_markdown_docsfiles()
    if gen_toc:
        docsgen.write_toc_file()
    if gen_index:
        docsgen.write_index_file()
    if gen_topics:
        docsgen.write_topics_file()
    if gen_index:
        docsgen.write_cheatsheet_file()

    if dump_tree:
        docsgen.dump_full_tree()
    if report:
        errorlog.write_report()
    if errorlog.has_errors:
        sys.exit(-1)


def main():
    parser = argparse.ArgumentParser(prog='openscad-docsgen')
    parser.add_argument('-D', '--docs-dir', default="docs",
                        help='The directory to put generated documentation in.')
    parser.add_argument('-S', '--strict', action="store_true",
                        help='If given, section blocks are required.')
    parser.add_argument('-T', '--test-only', action="store_true",
                        help="If given, don't generate images, but do try executing the scripts.")
    parser.add_argument('-f', '--force', action="store_true",
                        help='If given, force regeneration of images.')
    parser.add_argument('-n', '--no-images', action="store_true",
                        help='If given, skips image generation.')
    parser.add_argument('-m', '--gen-md', action="store_true",
                        help='If given, generate markdown documents for each file.')
    parser.add_argument('-i', '--gen-index', action="store_true",
                        help='If given, generate alphabetical Index.md file.')
    parser.add_argument('-I', '--gen-topics', action="store_true",
                        help='If given, generate Topics.md topics index file.')
    parser.add_argument('-t', '--gen-toc', action="store_true",
                        help='If given, generate TOC.md table of contents file.')
    parser.add_argument('-c', '--gen-cheat', action="store_true",
                        help='If given, generate CheatSheet.md file with all Usage lines.')
    parser.add_argument('-r', '--report', action="store_true",
                        help='If given, write all warnings and errors to docsgen_report.json')
    parser.add_argument('-d', '--dump-tree', action="store_true",
                        help='If given, dumps the documentation tree for debugging.')
    parser.add_argument('srcfile', nargs='+', help='List of input source files.')
    args = parser.parse_args()

    try:
        processFiles(
            args.srcfile,
            docs_dir=args.docs_dir,
            strict=args.strict,
            test_only=args.test_only,
            force=args.force,
            gen_imgs=not args.no_images,
            gen_md=args.gen_md,
            gen_toc=args.gen_toc,
            gen_index=args.gen_index,
            gen_topics=args.gen_topics,
            gen_cheat=args.gen_cheat,
            report=args.report,
            dump_tree=args.dump_tree
        )

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
