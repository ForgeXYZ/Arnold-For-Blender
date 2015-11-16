# -*- coding: utf-8 -*-

__author__ = "Ildar Nikolaev"
__email__ = "nildar@users.sourceforge.net"

import ctypes
import numpy
import itertools

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


# <blender sources>\source\blender\makesdna\DNA_listBase.h:59
class _ListBase(ctypes.Structure):
    pass

_ListBase._fields_ = [
    ("first", ctypes.POINTER(_ListBase)),
    ("last", ctypes.POINTER(_ListBase))
]


# <blender sources>\source\blender\blenkernel\BKE_particle.h:121
class _ParticleCacheKey(ctypes.Structure):
    _fields_ = [
        ("co", ctypes.c_float * 3),
        ("vel", ctypes.c_float * 3),
        ("rot", ctypes.c_float * 4),
        ("col", ctypes.c_float * 3),
        ("time", ctypes.c_float),
        ("segments", ctypes.c_int),
    ]


# <blender sources>\source\blender\makesdna\DNA_particle_types.h:264
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


# <blender sources>\source\blender\makesdna\DNA_object_force.h:159
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


# <blender sources>\source\blender\makesdna\DNA_object_force.h:170
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


def psys_get_points(ps, pss, frame_current):
    nch = len(ps.child_particles)
    trail_count = pss.trail_count
    if trail_count > 1:
        def _it():
            path_end = pss.path_end
            randlength = pss.length_random
            use_absolute_path_time = pss.use_absolute_path_time

            _cache = _PointCache.from_address(ps.point_cache.as_pointer())
            _mem = ctypes.cast(_cache.mem_cache.first, ctypes.POINTER(_PTCacheMem))

            for i, p in enumerate(ps.particles):
                pa_birthtime = p.birth_time
                pa_dietime = p.die_time
                pa_time = (frame_current - pa_birthtime) / p.lifetime

                if randlength > 0:
                    r_length = psys_frand(pss, i + 22)
                    tc = trail_count * (1.0 - randlength * r_length)
                    length = path_end * (1.0 - randlength * r_length)
                else:
                    tc = trail_count
                    length = path_end
                ct = (frame_current if use_absolute_path_time else pa_time) - length
                dt = length / (tc if tc else 1.0)

                for j in range(trail_count):
                    ct += dt
                    if use_absolute_path_time:
                        if ct < pa_birthtime or ct > pa_dietime:
                            continue
                        t = ct
                    elif ct < 0 or ct > 1:
                        continue
                    else:
                        t = pa_birthtime + ct * (pa_dietime - pa_birthtime)

                    print(t)

                    prev = None
                    pt = None
                    while _mem:
                        cur = _mem.contents
                        if cur.frame >= t:
                            totpoint = cur.totpoint

                            print(cur.frame, totpoint)

                            if totpoint > 0 and cur.data[0]:
                                idxs = ctypes.cast(cur.data[0], ctypes.POINTER(ctypes.c_int))
                                locs = ctypes.cast(cur.data[1], ctypes.POINTER(ctypes.c_float * 3))
                                for k in range(totpoint):
                                    co = locs[idxs[k]]
                                    if prev is not None:
                                        idxs = ctypes.cast(prev.data[0], ctypes.POINTER(ctypes.c_int))
                                        locs = ctypes.cast(prev.data[1], ctypes.POINTER(ctypes.c_float * 3))
                                        pco = locs[idx[k]]
                                        dfra = t - pt
                                        co = pco
                                    yield co
                            break
                        prev = cur
                        pt = t
                        #if 1 or frame < _mem.frame:
                        #    if _mem.frame > frame_current:
                        #        break
                        #    if _mem.totpoint > 0 and _mem.data[0]:
                        #        totpoint = _mem.totpoint
                        #        idxs = ctypes.cast(_mem.data[0], ctypes.POINTER(ctypes.c_int))
                        #        cos = ctypes.cast(_mem.data[1], ctypes.POINTER(ctypes.c_float * 3))
                        #        for i in range(totpoint):
                        #            a[n] = cos[idxs[i]]
                        #            n += 1
                        _mem = cur.next
        it = _it()
    elif nch > 0:
        return None
    else:
        it = (p.location for p in ps.particles if p.alive_state == 'ALIVE')
    return numpy.fromiter(itertools.chain.from_iterable(it), dtype=numpy.float32).reshape([-1, 3])
