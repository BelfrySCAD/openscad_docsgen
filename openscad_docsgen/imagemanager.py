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
    _size_re = re.compile(r'Size *= *([0-9]+) *x *([0-9]+)')
    _frames_re = re.compile(r'Frames *= *([0-9]+)')
    _framems_re = re.compile(r'FrameMS *= *([0-9]+)')
    _fps_re = re.compile(r'FPS *= *([0-9]+)')
    _vpt_re = re.compile(r'VPT *= *\[([^]]+)\]')
    _vpr_re = re.compile(r'VPR *= *\[([^]]+)\]')
    _vpd_re = re.compile(r'VPD *= *([0-9]+)')

    def __init__(self, src_file, src_line, image_file, script_lines, image_meta, starting_cb=None, completion_cb=None, verbose=False):
        self.src_file = src_file
        self.src_line = src_line
        self.image_file = image_file
        self.image_meta = image_meta
        self.script_lines = script_lines
        self.completion_cb = completion_cb
        self.starting_cb = starting_cb
        self.verbose = verbose

        self.render_mode = RenderMode.preview
        self.imgsize = (320, 240)
        self.camera = None
        self.animation_frames = None
        self.frame_ms = 250
        self.show_edges = "Edges" in image_meta
        self.show_axes = "NoAxes" not in image_meta
        self.show_scales = "NoScales" not in image_meta
        self.orthographic = "Perspective" not in image_meta
        self.script_under = False

        if "ThrownTogether" in image_meta:
            self.render_mode = RenderMode.thrown_together
        elif "Render" in image_meta:
            self.render_mode = RenderMode.render

        m = self._size_re.search(image_meta)
        scale = 1.0
        if m:
            self.imgsize = (int(m.group(1)), int(m.group(2)))
        elif "Small" in image_meta:
            scale = 0.75
        elif "Med" in image_meta:
            scale = 1.5
        elif "Big" in image_meta:
            scale = 2.0
        elif "Huge" in image_meta:
            scale = 2.5
        self.imgsize = [scale*x for x in self.imgsize]

        has_vp_splat = False
        match = self._vpr_re.search(image_meta)
        if match:
            self.script_lines.insert(0, "$vpr = [{}];".format(match.group(1)))
            has_vp_splat = True
        match = self._vpt_re.search(image_meta)
        if match:
            self.script_lines.insert(0, "$vpt = [{}];".format(match.group(1)))
            has_vp_splat = True
        match = self._vpd_re.search(image_meta)
        if match:
            self.script_lines.insert(0, "$vpd = {};".format(match.group(1)))
            has_vp_splat = True

        if "FlatSpin" in image_meta:
            self.script_lines.insert(0, "$vpr = [55, 0, 360*$t];")
            has_vp_splat = True
        elif "Spin" in image_meta:
            match = self._vpr_re.search(image_meta)
            if match:
                self.script_lines.insert(0, "$vpr = [{}];".format(match.group(1)))
            else:
                self.script_lines.insert(0, "$vpr = [90-45*cos(360*$t), 0, 360*$t];")
            has_vp_splat = True
        elif "3D" in image_meta:
            self.camera = [0,0,0,55,0,25,444]
        elif "2D" in image_meta:
            self.camera = [0,0,0,0,0,0,444]
        if has_vp_splat:
            self.camera = None

        match = self._fps_re.search(image_meta)
        if match:
            self.frame_ms = int(1000/match.group(1))
        match = self._framems_re.search(image_meta)
        if match:
            self.frame_ms = int(match.group(1))

        if "Spin" in image_meta or "Anim" in image_meta:
            self.animation_frames = 36
        match = self._frames_re.search(image_meta)
        if match:
            self.animation_frames = int(match.group(1))

        longest = max(len(line) for line in self.script_lines)
        maxlen = (880 - self.imgsize[0]) / 9
        if longest > maxlen or "ScriptUnder" in image_meta:
            self.script_under = True

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
        if self.starting_cb:
            self.starting_cb(self)

    def completed(self, status, osc=None):
        self.complete = True
        self.status = status
        if osc:
            self.success = osc.success
            self.cmdline = osc.cmdline
            self.return_code = osc.return_code
            self.stdout = osc.stdout
            self.stderr = osc.stderr
            self.echos = osc.echos
            self.warnings = osc.warnings
            self.errors = osc.errors
        else:
            self.success = True
        if self.completion_cb:
            self.completion_cb(self)


class ImageManager(object):

    def __init__(self):
        self.requests = []
        self.test_only = False

    def purge_requests(self):
        self.requests = []

    def new_request(self, src_file, src_line, image_file, script_lines, image_meta, starting_cb=None, completion_cb=None, verbose=False):
        if "NORENDER" in image_meta:
            raise Exception("Cannot render scripts marked NORENDER")
        req = ImageRequest(src_file, src_line, image_file, script_lines, image_meta, starting_cb, completion_cb, verbose=verbose)
        self.requests.append(req)
        return req

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

        with open(script_file, "w") as f:
            for line in req.script_lines:
                f.write(line + "\n")

        try:
            no_vp = True
            for line in req.script_lines:
                if "$vp" in line:
                    no_vp = False

            render_mode = req.render_mode
            animate = req.animation_frames
            if self.test_only:
                render_mode = RenderMode.test_only
                animate = None

            osc = OpenScadRunner(
                script_file,
                new_img_file,
                animate=animate,
                animate_duration=req.frame_ms,
                imgsize=req.imgsize,
                antialias=2,
                orthographic=True,
                camera=req.camera,
                auto_center=no_vp,
                view_all=no_vp,
                show_edges=req.show_edges,
                show_axes=req.show_axes,
                show_scales=req.show_scales,
                render_mode=render_mode,
                hard_warnings=no_vp,
                verbose=req.verbose
            )
            osc.run()
            osc.warnings = [line for line in osc.warnings if "Viewall and autocenter disabled" not in line]

        finally:
            os.unlink(script_file)

        if not osc.good() or osc.warnings or osc.errors:
            osc.success = False
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


image_manager = ImageManager()



# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
