import os
import ctypes
import itertools
import collections
import numpy
import math
import time
import re
from contextlib import contextmanager
import traceback

import bpy
import bgl
from mathutils import Matrix, Vector, geometry

import arnold


class _AiFilters():
    def __init__(self):
        # Get the global options node
        self._opts = bpy.context.scene.arnold
        self._sft = self._opts.sample_filter_type
        self._filter = arnold.AiNode(self._sft)

    def export(self):
        
        arnold.AiNodeSetStr(self._filter, "name", "__filter")
        if self._sft == 'blackman_harris_filter':
            arnold.AiNodeSetFlt(self._filter, "width", self._opts.sample_filter_bh_width)
        elif self._sft == 'sinc_filter':
            arnold.AiNodeSetFlt(self._filter, "width", self._opts.sample_filter_sinc_width)
        elif self._sft in {'cone_filter',
                    'cook_filter',
                    'disk_filter',
                    'gaussian_filter',
                    'triangle_filter',
                    'contour_filter'}:
            arnold.AiNodeSetFlt(self._filter, "width", self._opts.sample_filter_width)
        elif self._sft == 'farthest_filter':
            arnold.AiNodeSetStr(self._filter, "domain", self._opts.sample_filter_domain)
        elif self._sft == 'heatmap_filter':
            arnold.AiNodeSetFlt(self._filter, "minumum", self._opts.sample_filter_min)
            arnold.AiNodeSetFlt(self._filter, "maximum", self._opts.sample_filter_max)
        elif self._sft == 'variance_filter':
            arnold.AiNodeSetFlt(self._filter, "width", self._opts.sample_filter_width)
            arnold.AiNodeSetBool(self._filter, "scalar_mode", self._opts.sample_filter_scalar_mode)
            arnold.AiNodeSetStr(self._filter, "filter_weights", self._opts.sample_filter_weights)
        elif self._sft == 'cryptomatte_filter':
            arnold.AiNodeSetFlt(self._filter, "width", self._opts.sample_filter_width)
            arnold.AiNodeSetInt(self._filter, "rank", self._opts.sample_filter_rank)
            arnold.AiNodeSetStr(self._filter, "filter", self._opts.cryptomatte_filter)
        elif self._sft == 'denoise_optix_filter':
            arnold.AiNodeSetFlt(self._filter, "blend", self._opts.optix_blend)
        elif self._sft == 'diff_filter':
            arnold.AiNodeSetFlt(self._filter, "width", self._opts.sample_filter_width)
            arnold.AiNodeSetStr(self._filter, "filter_weights", self._opts.sample_filter_weights)

        arnold.AiMsgDebug(b"ARNOLD DEBUG: <<<")
