# -*- coding: utf-8 -*-

__author__ = "Ildar Nikolaev"
__email__ = "nildar@users.sourceforge.net"

import os
import sys
import multiprocessing as _mp


def _main(conn):
    dir = os.path.dirname(__file__)
    if dir not in sys.path:
        sys.path.append(dir)
    import arnold

    print("fn:", conn.recv())
    conn.send(["xxx", 10])


if __name__ == "__main__":
    import bpy
    _mp.set_executable(bpy.app.binary_path_python)

    _in, _out = _mp.Pipe()
    p = _mp.Process(target=_main, args=(_out, ))
    p.start()

    def send(data):
        _in.send(data)

    def recv():
        return _in.recv()

    #p.join()
