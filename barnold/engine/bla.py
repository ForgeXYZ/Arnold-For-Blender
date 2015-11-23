# -*- coding: utf-8 -*-

__author__ = "Ildar Nikolaev"
__email__ = "nildar@users.sourceforge.net"
__doc__ = "blender low level data access module"

import ctypes
import itertools

import numpy
from numpy import ndarray as _NDARRAY
from numpy.linalg import norm as _NORM

_S = (..., numpy.newaxis)


# <...>\source\blender\blenlib\intern\noise.c:160
hash = [
    0xA2, 0xA0, 0x19, 0x3B, 0xF8, 0xEB, 0xAA, 0xEE, 0xF3, 0x1C, 0x67, 0x28, 0x1D, 0xED, 0x0,  0xDE, 0x95, 0x2E, 0xDC,
    0x3F, 0x3A, 0x82, 0x35, 0x4D, 0x6C, 0xBA, 0x36, 0xD0, 0xF6, 0xC,  0x79, 0x32, 0xD1, 0x59, 0xF4, 0x8,  0x8B, 0x63,
    0x89, 0x2F, 0xB8, 0xB4, 0x97, 0x83, 0xF2, 0x8F, 0x18, 0xC7, 0x51, 0x14, 0x65, 0x87, 0x48, 0x20, 0x42, 0xA8, 0x80,
    0xB5, 0x40, 0x13, 0xB2, 0x22, 0x7E, 0x57, 0xBC, 0x7F, 0x6B, 0x9D, 0x86, 0x4C, 0xC8, 0xDB, 0x7C, 0xD5, 0x25, 0x4E,
    0x5A, 0x55, 0x74, 0x50, 0xCD, 0xB3, 0x7A, 0xBB, 0xC3, 0xCB, 0xB6, 0xE2, 0xE4, 0xEC, 0xFD, 0x98, 0xB,  0x96, 0xD3,
    0x9E, 0x5C, 0xA1, 0x64, 0xF1, 0x81, 0x61, 0xE1, 0xC4, 0x24, 0x72, 0x49, 0x8C, 0x90, 0x4B, 0x84, 0x34, 0x38, 0xAB,
    0x78, 0xCA, 0x1F, 0x1,  0xD7, 0x93, 0x11, 0xC1, 0x58, 0xA9, 0x31, 0xF9, 0x44, 0x6D, 0xBF, 0x33, 0x9C, 0x5F, 0x9,
    0x94, 0xA3, 0x85, 0x6,  0xC6, 0x9A, 0x1E, 0x7B, 0x46, 0x15, 0x30, 0x27, 0x2B, 0x1B, 0x71, 0x3C, 0x5B, 0xD6, 0x6F,
    0x62, 0xAC, 0x4F, 0xC2, 0xC0, 0xE,  0xB1, 0x23, 0xA7, 0xDF, 0x47, 0xB0, 0x77, 0x69, 0x5,  0xE9, 0xE6, 0xE7, 0x76,
    0x73, 0xF,  0xFE, 0x6E, 0x9B, 0x56, 0xEF, 0x12, 0xA5, 0x37, 0xFC, 0xAE, 0xD9, 0x3,  0x8E, 0xDD, 0x10, 0xB9, 0xCE,
    0xC9, 0x8D, 0xDA, 0x2A, 0xBD, 0x68, 0x17, 0x9F, 0xBE, 0xD4, 0xA,  0xCC, 0xD2, 0xE8, 0x43, 0x3D, 0x70, 0xB7, 0x2,
    0x7D, 0x99, 0xD8, 0xD,  0x60, 0x8A, 0x4,  0x2C, 0x3E, 0x92, 0xE5, 0xAF, 0x53, 0x7,  0xE0, 0x29, 0xA6, 0xC5, 0xE3,
    0xF5, 0xF7, 0x4A, 0x41, 0x26, 0x6A, 0x16, 0x5E, 0x52, 0x2D, 0x21, 0xAD, 0xF0, 0x91, 0xFF, 0xEA, 0x54, 0xFA, 0x66,
    0x1A, 0x45, 0x39, 0xCF, 0x75, 0xA4, 0x88, 0xFB, 0x5D, 0xA2, 0xA0, 0x19, 0x3B, 0xF8, 0xEB, 0xAA, 0xEE, 0xF3, 0x1C,
    0x67, 0x28, 0x1D, 0xED, 0x0,  0xDE, 0x95, 0x2E, 0xDC, 0x3F, 0x3A, 0x82, 0x35, 0x4D, 0x6C, 0xBA, 0x36, 0xD0, 0xF6,
    0xC,  0x79, 0x32, 0xD1, 0x59, 0xF4, 0x8,  0x8B, 0x63, 0x89, 0x2F, 0xB8, 0xB4, 0x97, 0x83, 0xF2, 0x8F, 0x18, 0xC7,
    0x51, 0x14, 0x65, 0x87, 0x48, 0x20, 0x42, 0xA8, 0x80, 0xB5, 0x40, 0x13, 0xB2, 0x22, 0x7E, 0x57, 0xBC, 0x7F, 0x6B,
    0x9D, 0x86, 0x4C, 0xC8, 0xDB, 0x7C, 0xD5, 0x25, 0x4E, 0x5A, 0x55, 0x74, 0x50, 0xCD, 0xB3, 0x7A, 0xBB, 0xC3, 0xCB,
    0xB6, 0xE2, 0xE4, 0xEC, 0xFD, 0x98, 0xB,  0x96, 0xD3, 0x9E, 0x5C, 0xA1, 0x64, 0xF1, 0x81, 0x61, 0xE1, 0xC4, 0x24,
    0x72, 0x49, 0x8C, 0x90, 0x4B, 0x84, 0x34, 0x38, 0xAB, 0x78, 0xCA, 0x1F, 0x1,  0xD7, 0x93, 0x11, 0xC1, 0x58, 0xA9,
    0x31, 0xF9, 0x44, 0x6D, 0xBF, 0x33, 0x9C, 0x5F, 0x9,  0x94, 0xA3, 0x85, 0x6,  0xC6, 0x9A, 0x1E, 0x7B, 0x46, 0x15,
    0x30, 0x27, 0x2B, 0x1B, 0x71, 0x3C, 0x5B, 0xD6, 0x6F, 0x62, 0xAC, 0x4F, 0xC2, 0xC0, 0xE,  0xB1, 0x23, 0xA7, 0xDF,
    0x47, 0xB0, 0x77, 0x69, 0x5,  0xE9, 0xE6, 0xE7, 0x76, 0x73, 0xF,  0xFE, 0x6E, 0x9B, 0x56, 0xEF, 0x12, 0xA5, 0x37,
    0xFC, 0xAE, 0xD9, 0x3,  0x8E, 0xDD, 0x10, 0xB9, 0xCE, 0xC9, 0x8D, 0xDA, 0x2A, 0xBD, 0x68, 0x17, 0x9F, 0xBE, 0xD4,
    0xA,  0xCC, 0xD2, 0xE8, 0x43, 0x3D, 0x70, 0xB7, 0x2,  0x7D, 0x99, 0xD8, 0xD,  0x60, 0x8A, 0x4,  0x2C, 0x3E, 0x92,
    0xE5, 0xAF, 0x53, 0x7,  0xE0, 0x29, 0xA6, 0xC5, 0xE3, 0xF5, 0xF7, 0x4A, 0x41, 0x26, 0x6A, 0x16, 0x5E, 0x52, 0x2D,
    0x21, 0xAD, 0xF0, 0x91, 0xFF, 0xEA, 0x54, 0xFA, 0x66, 0x1A, 0x45, 0x39, 0xCF, 0x75, 0xA4, 0x88, 0xFB, 0x5D,
]

# <...>\source\blender\blenlib\intern\rand.c:47
MULTIPLIER = 0x5deece66d
MASK = 0x0000ffffffffffff

ADDEND = 0xb
LOWSEED = 0x330e

# <...>\source\blender\blenkernel\BKE_particle.h:247
PSYS_FRAND_COUNT = 1024
PSYS_FRAND_SEED_OFFSET = []
PSYS_FRAND_SEED_MULTIPLIER = []
PSYS_FRAND_BASE = []


class RNG():
    def __init__(self, x):
        self.X = ctypes.c_uint64(x)

    # <...>\source\blender\blenlib\intern\rand.c:96
    def srandom(self, seed: int):
        self.seed(seed + hash[seed & 255])
        seed = self.get_uint()
        self.seed(seed + hash[seed & 255])
        seed = self.get_uint()
        self.seed(seed + hash[seed & 255])

    # <...>\source\blender\blenlib\intern\rand.c:88
    def seed(self, seed: int):
        self.X = ctypes.c_uint64((seed << 16) | LOWSEED)

    # <...>\source\blender\blenlib\intern\rand.c:105
    def step(self):
        self.X = ctypes.c_uint64((MULTIPLIER * self.X.value + ADDEND) & MASK)

    # <...>\source\blender\blenlib\intern\rand.c:110
    def get_int(self):
        self.step()
        return ctypes.c_int(self.X.value >> 17).value

    # <...>\source\blender\blenlib\intern\rand.c:116
    def get_uint(self):
        self.step()
        return ctypes.c_uint(self.X.value >> 17).value

    # <...>\source\blender\blenlib\intern\rand.c:133
    def get_float(self):
        return ctypes.c_float(self.get_int() / 0x80000000).value

# <...>\source\blender\blenlib\intern\rand.c:226
theBLI_rng = RNG(611330372042337130)

# <...>\source\blender\blenkernel\intern\particle.c:93
def psys_init_rng():
    theBLI_rng.srandom(5831)
    for i in range(PSYS_FRAND_COUNT):
        PSYS_FRAND_BASE.append(theBLI_rng.get_float())
        PSYS_FRAND_SEED_OFFSET.append(theBLI_rng.get_uint())
        PSYS_FRAND_SEED_MULTIPLIER.append(theBLI_rng.get_uint())

psys_init_rng()

# <...>\source\blender\blenkernel\BKE_particle.h:254
def psys_frand(pss, seed):
    offset = PSYS_FRAND_SEED_OFFSET[pss.seed % PSYS_FRAND_COUNT]
    multiplier = PSYS_FRAND_SEED_MULTIPLIER[pss.seed % PSYS_FRAND_COUNT]
    return PSYS_FRAND_BASE[(offset * seed * multiplier) % PSYS_FRAND_COUNT]


# <...>\source\blender\makesdna\DNA_listBase.h:59
class _ListBase(ctypes.Structure):
    pass

_ListBase._fields_ = [
    ("first", ctypes.POINTER(_ListBase)),
    ("last", ctypes.POINTER(_ListBase))
]


# <...>\source\blender\blenkernel\BKE_particle.h:121
class _ParticleCacheKey(ctypes.Structure):
    _fields_ = [
        ("co", ctypes.c_float * 3),
        ("vel", ctypes.c_float * 3),
        ("rot", ctypes.c_float * 4),
        ("col", ctypes.c_float * 3),
        ("time", ctypes.c_float),
        ("segments", ctypes.c_int),
    ]


# <...>\source\blender\makesdna\DNA_particle_types.h:72
class _ChildParticle(ctypes.Structure):
    _fields_ = [
        # num is face index on the final derived mesh
        ("num", ctypes.c_int),
        ("parent", ctypes.c_int),
        # nearest particles to the child, used for the interpolation
        ("pa", ctypes.c_int * 4),
        # interpolation weights for the above particles
        ("w", ctypes.c_float * 4),
        # face vertex weights and offset
        ("fuv", ctypes.c_float * 4),
        ("foffset", ctypes.c_float),
        ("rt", ctypes.c_float)
    ]


# <...>\source\blender\makesdna\DNA_particle_types.h:264
class _ParticleSystem(ctypes.Structure):
    pass

_ParticleSystem._fields_ = [
    ("next", ctypes.POINTER(_ParticleSystem)),
    ("prev", ctypes.POINTER(_ParticleSystem)),
    # particle settings
    ("part", ctypes.c_void_p),
    # (parent) particles
    ("particles", ctypes.c_void_p),
    # child particles
    ("child", ctypes.c_void_p),
    # particle editmode (runtime)
    ("edit", ctypes.c_void_p),
    # free callback
    ("free_edit", ctypes.c_void_p),
    # path cache (runtime)
    ("pathcache", ctypes.POINTER(ctypes.POINTER(_ParticleCacheKey))),
    # child cache (runtime)
    ("childcache", ctypes.POINTER(ctypes.POINTER(_ParticleCacheKey))),
    # buffers for the above
    ("pathcachebufs", _ListBase),
    ("childcachebufs", _ListBase),
    # cloth simulation for hair
    ("clmd", ctypes.c_void_p),
    # input/output for cloth simulation
    ("hair_in_dm", ctypes.c_void_p),
    ("hair_out_dm", ctypes.c_void_p),
    #
    ("target_ob", ctypes.c_void_p),
    # run-time only lattice deformation data
    ("lattice_deform_data", ctypes.c_void_p),
    # particles from global space -> parent space
    ("parent", ctypes.c_void_p),
    # used for keyed and boid physics
    ("targets", _ListBase),
    # particle system name, MAX_NAME
    ("name", ctypes.c_char * 64),
    # used for duplicators
    ("imat", ctypes.c_float * 4 * 4),
    #
    ("cfra", ctypes.c_float),
    ("tree_frame", ctypes.c_float),
    ("bvhtree_frame", ctypes.c_float),
    ("seed", ctypes.c_int),
    ("child_seed", ctypes.c_int),
    ("flag", ctypes.c_int),
    ("totpart", ctypes.c_int),
    ("totunexist", ctypes.c_int),
    ("totchild", ctypes.c_int),
    ("totcached", ctypes.c_int),
    ("totchildcache", ctypes.c_int),
    ("recalc", ctypes.c_short),
    ("target_psys", ctypes.c_short),
    ("totkeyed", ctypes.c_short),
    ("bakespace", ctypes.c_short),
    # billboard uv name, MAX_CUSTOMDATA_LAYER_NAME
    ("bb_uvname", ctypes.c_char * 64 * 3),
    # vertex groups, 0==disable, 1==starting index
    ("vgroup", ctypes.c_short * 12),
    ("vg_neg", ctypes.c_short),
    ("rt3", ctypes.c_short),
    # temporary storage during render
    ("renderdata", ctypes.c_void_p)
]


# <...>\source\blender\makesdna\DNA_object_force.h:159
class _PTCacheMem(ctypes.Structure):
    pass

_PTCacheMem._fields_ = [
    ("next", ctypes.POINTER(_PTCacheMem)),
    ("prev", ctypes.POINTER(_PTCacheMem)),
    ("frame", ctypes.c_uint),
    ("totpoint", ctypes.c_uint),
    ("data_types", ctypes.c_uint),
    ("flag", ctypes.c_uint),
    ("data", ctypes.c_void_p * 8),
    ("cur", ctypes.c_void_p * 8),
    ("extradata", _ListBase)
]


# <...>\source\blender\makesdna\DNA_object_force.h:170
class _PointCache(ctypes.Structure):
    pass

_PointCache._fields_ = [
    ("next", ctypes.POINTER(_PointCache)),
    ("prev", ctypes.POINTER(_PointCache)),
    ("flag", ctypes.c_int),
    ("step", ctypes.c_int),
    ("simframe", ctypes.c_int),
    ("startframe", ctypes.c_int),
    ("endframe", ctypes.c_int),
    ("editframe", ctypes.c_int),
    ("last_exact", ctypes.c_int),
    ("last_valid", ctypes.c_int),
    ("pad", ctypes.c_int),
    ("totpoint", ctypes.c_int),
    ("index", ctypes.c_int),
    ("compression", ctypes.c_short),
    ("rt", ctypes.c_short),
    ("name", ctypes.c_char * 64),
    ("prev_name", ctypes.c_char * 64),
    ("info", ctypes.c_char * 64),
    ("path", ctypes.c_char * 1024),
    ("cached_frames", ctypes.c_char_p),
    ("mem_cache", _ListBase),
    ("edit", ctypes.c_void_p),
    ("free_edit", ctypes.c_void_p)
]


def _BezierInterpolate(pts, n, cache, npts, steps, scale):
    """Interpolate points cache to bezier curve
        pts:
            numpy.ndarray([x, y, 3], dtype='f')
            array for bezier interpolated control points
        n:
            int
            position in pts array
        cache:
            ctypes.POINTER(_ParticleCacheKey)
            points cache
        npts:
            int
            points number in cache.
        scale:
            float
            interpolation scale factor
    """
    for i in range(npts):
        c = cache[i]

        a = _NDARRAY([steps, 3], dtype='f')
        for j in range(steps):
            a[j] = c[j].co

        s = a[1:-1]
        t = a[2:] - a[:-2]
        t *= scale / _NORM(t, axis=1)[_S]  # tangents
        m = _NORM(a[1:] - a[:-1], axis=1)[_S]  # magnitudes

        pts[n, ::3] = a
        pts[n, 1] = a[0] + (a[1] - a[0]) * scale
        pts[n, -2] = a[-1] - (a[-1] - a[-2]) * scale
        pts[n, 2:-3:3] = s - t * m[:-1]
        pts[n, 4::3] = s + t * m[1:]
        n += 1
    return n


def psys_get_curves(ps, steps, use_parent_particles, props):
    nch = len(ps.child_particles)
    if nch == 0 or use_parent_particles:
        np = len(ps.particles)
        tot = np + nch
        if tot <= 0:
            return None
        use_parent_particles = True
    elif nch > 0:
        tot = nch
        use_parent_particles = False
    else:
        return None

    _ps = _ParticleSystem.from_address(ps.as_pointer())
    n = 0

    if props.basis == 'bezier':
        nsteps = steps * 3 - 2
        points = _NDARRAY([tot, nsteps, 3], dtype=numpy.float32)
        scale = props.bezier_scale
        if use_parent_particles:
            n = _BezierInterpolate(points, n, _ps.pathcache, np, steps, scale)
        _BezierInterpolate(points, n, _ps.childcache, nch, steps, scale)
        radius = numpy.linspace(props.radius_root, props.radius_tip, steps, dtype=numpy.float32)
        return (points.reshape(-1, 3), numpy.tile(radius, tot), nsteps)

    if props.basis in {'b-spline', 'catmull-rom'}:
        points = _NDARRAY([tot * (steps + 4), 3], dtype=numpy.float32)
        if use_parent_particles:
            _cache = _ps.pathcache
            for i in range(np):
                c = _cache[i]
                points[n:n + 2] = c[0].co
                n += 2
                for j in range(steps):
                    points[n] = c[j].co
                    n += 1
                points[n:n + 2] = points[n - 1]
                n += 2
        _cache = _ps.childcache
        for i in range(nch):
            c = _cache[i]
            points[n:n + 2] = c[0].co
            n += 2
            for j in range(steps):
                points[n] = c[j].co
                n += 1
            points[n: n + 2] = points[n - 1]
            n += 2
        radius = numpy.ndarray(steps + 2, dtype=numpy.float32)
        radius[1:-1] = numpy.linspace(props.radius_root, props.radius_tip, steps, dtype=numpy.float32)
        radius[0] = 0
        radius[-1] = 0
        return (points, numpy.tile(radius, tot), steps + 4)

    if props.basis == 'linear':
        points = _NDARRAY([tot * steps, 3], dtype=numpy.float32)
        if use_parent_particles:
            _cache = _ps.pathcache
            for i in range(np):
                c = _cache[i]
                for j in range(steps):
                    points[n] = c[j].co
                    n += 1
        _cache = _ps.childcache
        for i in range(nch):
            c = _cache[i]
            for j in range(steps):
                points[n] = c[j].co
                n += 1
        radius = numpy.linspace(props.radius_root, props.radius_tip, steps, dtype=numpy.float32)
        return (points, numpy.tile(radius, tot), steps)

    return None


def psys_get_points(ps, pss, frame_current):
    nch = len(ps.child_particles)
    trail_count = pss.trail_count
    if trail_count > 1:
        def _it():
            path_end = pss.path_end
            randlength = pss.length_random
            use_absolute_path_time = pss.use_absolute_path_time
            time_tweak = pss.time_tweak

            length = path_end
            if use_absolute_path_time:
                _ct = frame_current - length
            tc = trail_count if trail_count else 1.0

            cast = ctypes.cast
            p_uint = ctypes.POINTER(ctypes.c_uint)
            p_float3 = ctypes.POINTER(ctypes.c_float * 3)

            _cache = _PointCache.from_address(ps.point_cache.as_pointer())
            _mem = ctypes.cast(_cache.mem_cache.first, ctypes.POINTER(_PTCacheMem))

            #def parts():
            #    i = 0
            #    particles = ps.particles
            #    if nch == 0 or pss.use_parent_particles:
            #        for p in particles:
            #            # <...>\source\blender\editors\space_view3d\drawobject.c:5354
            #            bt = p.birth_time
            #            yield (i, bt, p.die_time, (frame_current - bt) / p.lifetime)
            #            i += 1
            #    PART_CHILD_FACES = (pss.child_type == 'INTERPOLATED')
            #    for c, p in enumerate(ps.child_particles):
            #        cpa = _ChildParticle.from_address(p.as_pointer())
            #        # <...>\source\blender\blenkernel\intern\particle.c:3561
            #        if PART_CHILD_FACES:
            #            bt = 0.0
            #            cpaw = cpa.w
            #            for w, n in enumerate(cpa.pa):
            #                if n < 0:
            #                    break
            #                bt += cpaw[w] * particles[n].birth_time
            #            lt = pss.lifetime
            #            if randlength > 0:
            #                lt *= 1.0 - randlength * psys_frand(pss, c + 25)
            #        else:
            #            p = particles[cpa.parent]
            #            bt = p.birth_time
            #            lt = p.lifetime
            #        yield (i, bt, bt + lt, (frame_current - bt) / lt)
            #        i += 1

            #for a, pa_birthtime, pa_dietime, pa_time in parts():
            for a, pa in enumerate(ps.particles):
                # <...>\source\blender\editors\space_view3d\drawobject.c:5354
                pa_birthtime = pa.birth_time
                pa_dietime = pa.die_time
                pa_time = (frame_current - pa_birthtime) / pa.lifetime

                if randlength > 0:
                    r_length = psys_frand(pss, a + 22)
                    tc = trail_count * (1.0 - randlength * r_length)
                    if not tc:
                        tc = 1.0
                    length = path_end * (1.0 - randlength * r_length)
                if not use_absolute_path_time:
                    _ct = pa_time - length

                # <...>\source\blender\editors\space_view3d\drawobject.c:5404
                for j in range(1, trail_count + 1):
                    ct = _ct + (j / tc) * length
                    if use_absolute_path_time:
                        if pa_birthtime > ct or ct > pa_dietime:
                            continue
                        t = ct
                    elif 0 > ct or ct > 1:
                        continue
                    else:
                        t = pa_birthtime + ct * (pa_dietime - pa_birthtime)

                    prev = None
                    while _mem:
                        # <...>\source\blender\blenkernel\intern\particle.c:839
                        cur = _mem.contents
                        cf = cur.frame
                        if t <= cf:
                            tp = cur.totpoint
                            data = cur.data
                            if tp > 0 and data[0]:
                                idxs = cast(data[0], p_uint)
                                locs = cast(data[1], p_float3)

                                if prev is not None:
                                    vels = cast(data[2], p_float3)

                                    data = prev.data
                                    pidxs = cast(data[0], p_uint)
                                    plocs = cast(data[1], p_float3)
                                    pvels = cast(data[2], p_float3)
                                    ptp = prev.totpoint

                                for k in range(tp):
                                    i = idxs[k]
                                    co = locs[i]
                                    if prev is not None and k < ptp:
                                        ve = vels[i]

                                        i = pidxs[k]
                                        pco = plocs[i]
                                        pve = pvels[i]

                                        # <...>\source\blender\blenkernel\intern\particle.c:1118
                                        pf = prev.frame
                                        dfra = cf - pf
                                        kt = (t - pf) / dfra

                                        # <...>\source\blender\blenkernel\intern\particle.c:1123
                                        invdt = dfra * 0.04 * time_tweak
                                        v0 = ve[0] * invdt
                                        v1 = ve[1] * invdt
                                        v2 = ve[2] * invdt
                                        pv0 = pve[0] * invdt
                                        pv1 = pve[1] * invdt
                                        pv2 = pve[2] * invdt

                                        # <...>\source\blender\blenlib\intern\math_geom.c:3283
                                        t2 = kt * kt
                                        t3 = t2 * kt
                                        c0 = pco[0] - co[0]
                                        c1 = pco[1] - co[1]
                                        c2 = pco[2] - co[2]
                                        a0 = pv0 + v0 + 2 * c0
                                        a1 = pv1 + v1 + 2 * c1
                                        a2 = pv2 + v2 + 2 * c2
                                        b0 = -2 * pv0 - v0 - 3 * c0
                                        b1 = -2 * pv1 - v1 - 3 * c1
                                        b2 = -2 * pv2 - v2 - 3 * c2
                                        co = [
                                            a0 * t3 + b0 * t2 + pv0 * kt + pco[0],
                                            a1 * t3 + b1 * t2 + pv1 * kt + pco[1],
                                            a2 * t3 + b2 * t2 + pv2 * kt + pco[2]
                                        ]
                                    yield co
                            break
                        prev = cur
                        _mem = cur.next
        it = _it()
    elif nch > 0:
        # TODO: child particles
        return None
    else:
        it = (p.location for p in ps.particles if p.alive_state == 'ALIVE')
    return numpy.fromiter(itertools.chain.from_iterable(it), dtype=numpy.float32).reshape([-1, 3])
