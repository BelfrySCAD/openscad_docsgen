#!/usr/bin/env python3

from __future__ import print_function

import os
import re
import math
import filecmp
import os.path
import subprocess
from collections import namedtuple

from PIL import Image, ImageChops
from openscad_runner import RenderMode, OpenScadRunner


class ImageRequest(object):
    def __init__(self, src_file, src_line, image_file, script_lines, image_meta, starting_cb=None, completion_cb=None):
        self.src_file = src_file
        self.src_line = src_line
        self.image_file = image_file
        self.script_lines = script_lines
        self.image_meta = image_meta
        self.completion_cb = completion_cb
        self.starting_cb = starting_cb

        self.complete = False
        self.status = "INCOMPLETE"
        self.success = False
        self.echos = []
        self.warnings = []
        self.errors = []

    def starting(self):
        if self.starting_cb:
            self.starting_cb(self)

    def completed(self, status, osc=None):
        self.complete = True
        self.status = status
        if osc:
            self.success = osc.success
            self.echos = osc.echos
            self.warnings = osc.warnings
            self.errors = osc.errors
        else:
            self.success = True
        if self.completion_cb:
            self.completion_cb(self)


class ImageManager(object):
    _size_re = re.compile(r'Size=([0-9]+)x([0-9]+)')
    _vpt_re = re.compile(r'VPT=\[([^]]+)\]')
    _vpr_re = re.compile(r'VPR=\[([^]]+)\]')
    _vpd_re = re.compile(r'VPD=([0-9]+)')
    _framems_re = re.compile(r'FrameMS=([0-9]+)')

    def __init__(self):
        self.requests = []
        self.test_only = False

    def purge_requests(self):
        self.requests = []

    def new_request(self, src_file, src_line, image_file, script_lines, image_meta, starting_cb=None, completion_cb=None):
        if "NORENDER" in image_meta:
            raise Exception("Cannot render scripts marked NORENDER")
        req = ImageRequest(src_file, src_line, image_file, script_lines, image_meta, starting_cb, completion_cb)
        self.requests.append(req)

    def process_requests(self, test_only=False):
        self.test_only = test_only
        for req in self.requests:
            self.process_request(req)
        self.requests = []

    def process_request(self, req):
        req.starting()

        dir_name = os.path.dirname(req.image_file)
        base_name = os.path.basename(req.image_file)
        file_base, file_ext = os.path.splitext(base_name)
        script_file = "tmp_{0}.scad".format(base_name.replace(".", "_"))
        targ_img_file = req.image_file
        new_img_file = "tmp_{0}{1}".format(file_base, file_ext)

        camera = None
        if "FlatSpin" in req.image_meta:
            req.script_lines.insert(0, "$vpr = [55, 0, 360*$t];")
        elif "Spin" in req.image_meta:
            match = self._vpr_re.search(req.image_meta)
            if match:
                req.script_lines.insert(0, "$vpr = [{}];".format(match.group(1)))
            else:
                req.script_lines.insert(0, "$vpr = [90-45*cos(360*$t), 0, 360*$t];")
        elif "3D" in req.image_meta:
            camera = [0,0,0,55,0,25,444]
        elif "2D" in req.image_meta:
            camera = [0,0,0,0,0,0,444]
        else:
            match = self._vpr_re.search(req.image_meta)
            if match:
                req.script_lines.insert(0, "$vpr = [{}];".format(match.group(1)))
            else:
                camera = [0,0,0,55,0,25,444]

        match = self._vpt_re.search(req.image_meta)
        if match:
            req.script_lines.insert(0, "$vpt = [{}];".format(match.group(1)))

        match = self._vpd_re.search(req.image_meta)
        if match:
            req.script_lines.insert(0, "$vpd = {};".format(match.group(1)))

        with open(script_file, "w") as f:
            for line in req.script_lines:
                f.write(line + "\n")

        m = self._size_re.search(req.image_meta)
        if m:
            imgsize = (int(m.group(1)), int(m.group(2)))
        else:
            imgsize = (320, 240)

        if "Small" in req.image_meta:
            imgsize = [0.75*x for x in imgsize]
        elif "Med" in req.image_meta:
            imgsize = [1.5*x for x in imgsize]
        elif "Big" in req.image_meta:
            imgsize = [2.0*x for x in imgsize]
        elif "Huge" in req.image_meta:
            imgsize = [2.5*x for x in imgsize]

        render_mode = RenderMode.preview
        if self.test_only:
            render_mode = RenderMode.test_only
        elif "Render" in req.image_meta:
            render_mode = RenderMode.render

        no_vp = True
        for line in req.script_lines:
            if "$vp" in line:
                no_vp = False

        frame_ms = 250
        match = self._vpd_re.search(req.image_meta)
        if match:
            frame_ms = int(match.group(1))

        osc = OpenScadRunner(
            script_file,
            new_img_file,
            animate=36 if (("Spin" in req.image_meta or "Anim" in req.image_meta) and not self.test_only) else None,
            animate_duration=frame_ms,
            imgsize=imgsize, antialias=2,
            orthographic=True,
            camera=camera,
            auto_center=no_vp,
            view_all=no_vp,
            show_edges="Edges" in req.image_meta,
            show_axes="NoAxes" not in req.image_meta,
            render_mode=render_mode,
            hard_warnings=no_vp
        )
        osc.run()

        os.unlink(script_file)

        if not osc.good():
            req.completed("FAIL", osc)
            return

        if self.test_only:
            req.completed("SKIP", osc)
            return

        os.makedirs(os.path.dirname(targ_img_file), exist_ok=True)

        # Time to compare image.
        if not os.path.isfile(targ_img_file):
            os.rename(new_img_file, targ_img_file)
            req.completed("NEW", osc)
        elif self.image_compare(targ_img_file, new_img_file):
            os.unlink(new_img_file)
            req.completed("SKIP", osc)
        else:
            os.unlink(targ_img_file)
            os.rename(new_img_file, targ_img_file)
            req.completed("REPLACE", osc)

    @staticmethod
    def image_compare(file1, file2, max_rms=2.0):
        """
        Compare two image files.  Returns true if they are almost exactly the same.
        """
        if file1.endswith(".gif") and file2.endswith(".gif"):
            return filecmp.cmp(file1, file2, shallow=False)
        else:
            img1 = Image.open(file1)
            img2 = Image.open(file2)
            if img1.size != img2.size or img1.getbands() != img2.getbands():
                return False
            diff = ImageChops.difference(img1, img2).histogram()
            sq = (value * (i % 256) ** 2 for i, value in enumerate(diff))
            sum_squares = sum(sq)
            rms = math.sqrt(sum_squares / float(img1.size[0] * img1.size[1]))
            return rms <= max_rms


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
