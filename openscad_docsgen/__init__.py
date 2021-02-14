#!/usr/bin/env python3

from __future__ import print_function

import sys
import os
import os.path
import argparse

from .blocks import DocsGenParser


def processFile(
    files, docs_dir,
    gen_imgs=False,
    test_only=False,
    gen_toc=False,
    gen_index=False,
    gen_cheat=False
):
    if not test_only and not os.path.exists(docs_dir):
        os.makedirs(docs_dir)

    docsgen = DocsGenParser()
    for infile in files:
        docsgen.parse_file(
            infile,
            images=gen_imgs,
            test_only=test_only
        )

    if not test_only:
        docsgen.write_markdown_docsfiles()
    if gen_toc:
        docsgen.write_toc_file()
    if gen_index:
        docsgen.write_index_file()
    if gen_index:
        docsgen.write_cheatsheet_file()


def main():
    parser = argparse.ArgumentParser(prog='docs_gen')
    parser.add_argument('-D', '--docs-dir', default="docs",
                        help='The directory to put generated documentation in.')
    parser.add_argument('-T', '--test-only', action="store_true",
                        help="If given, don't generate images, but do try executing the scripts.")
    parser.add_argument('-n', '--no-images', action="store_true",
                        help='If given, skips image generation.')
    parser.add_argument('-i', '--gen-index', action="store_true",
                        help='If given, generate alphabetical Index.md file.')
    parser.add_argument('-t', '--gen-toc', action="store_true",
                        help='If given, generate table of contents TOC.md file.')
    parser.add_argument('-c', '--gen-cheat', action="store_true",
                        help='If given, generate CheatSheet.md file with all Usage lines.')
    parser.add_argument('srcfile', type=argparse.FileType('r'), nargs='+', help='List of input source files.')
    args = parser.parse_args()

    processFiles(
        args.srcfile,
        docs_dir=args.docs_dir,
        test_only=args.test_only,
        gen_imgs=not args.no_images,
        gen_toc=args.gen_toc,
        gen_index=args.gen_index,
        gen_cheat=args.gen_cheat,
    )

    sys.exit(0)


if __name__ == "__main__":
    main()


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
