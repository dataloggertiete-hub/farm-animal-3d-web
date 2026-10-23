#!/usr/bin/env python3
"""
Gerador de Animais de Fazenda em 3D - Módulo Core
Sem dependências externas, apenas Python padrão.
"""

import math
import os
import struct
from dataclasses import dataclass, field
from typing import List, Tuple

# ============================================================================
# ESTRUTURAS DE DADOS
# ============================================================================

@dataclass
class Vertex:
    x: float
    y: float
    z: float

    def __add__(self, other):
        return Vertex(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other):
        return Vertex(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, s):
        if isinstance(s, (int, float)):
            return Vertex(self.x * s, self.y * s, self.z * s)
        return NotImplemented

@dataclass
class Triangle:
    normal: Vertex
    v1: Vertex
    v2: Vertex
    v3: Vertex

@dataclass
class Joint:
    name: str
    type: str
    position: Tuple[float, float, float]
    diameter: float
    length: float
    rotation_axes: Tuple[bool, bool, bool]
    description: str

@dataclass
class Part:
    name: str
    description: str
    triangles: List[Triangle]
    joints: List[Joint] = field(default_factory=list)
    connect_to: str = ""
    movement_range: str = ""

@dataclass
class AnimalModel:
    name: str
    species: str
    solid_triangles: List[Triangle]
    parts: List[Part] = field(default_factory=list)
    assembly_guide: str = ""

# ============================================================================
# UTILITÁRIOS
# ============================================================================

def vec_normalize(x, y, z):
    length = math.sqrt(x*x + y*y + z*z)
    if length == 0:
        return (0.0, 0.0, 0.0)
    return (x/length, y/length, z/length)

def cross(ax, ay, az, bx, by, bz):
    return (ay*bz - az*by, az*bx - ax*bz, ax*by - ay*bx)

def tri_normal(v1, v2, v3):
    ax, ay, az = v2.x - v1.x, v2.y - v1.y, v2.z - v1.z
    bx, by, bz = v3.x - v1.x, v3.y - v1.y, v3.z - v1.z
    nx, ny, nz = cross(ax, ay, az, bx, by, bz)
    return Vertex(*vec_normalize(nx, ny, nz))

def flatten(triangles):
    flat = []
    def add(t):
        if isinstance(t, list):
            for x in t:
                add(x)
        else:
            flat.append(t)
    for t in triangles:
        add(t)
    return flat

def write_stl(triangles, filepath):
    triangles = flatten(triangles)
    with open(filepath, 'wb') as f:
        header = b'Farm Animal 3D Generator v2.0'
        f.write(header.ljust(80, b'\0'))
        f.write(struct.pack('<I', len(triangles)))
        for t in triangles:
            f.write(struct.pack('<fff', t.normal.x, t.normal.y, t.normal.z))
            f.write(struct.pack('<fff', t.v1.x, t.v1.y, t.v1.z))
            f.write(struct.pack('<fff', t.v2.x, t.v2.y, t.v2.z))
            f.write(struct.pack('<fff', t.v3.x, t.v3.y, t.v3.z))
            f.write(struct.pack('<H', 0))

# ============================================================================
# PRIMITIVOS
# ============================================================================

def box(w, h, d, cx=0, cy=0, cz=0):
    hw, hh, hd = w/2, h/2, d/2
    v = [
        Vertex(cx-hw, cy-hh, cz-hd), Vertex(cx+hw, cy-hh, cz-hd),
        Vertex(cx+hw, cy+hh, cz-hd), Vertex(cx-hw, cy+hh, cz-hd),
        Vertex(cx-hw, cy-hh, cz+hd), Vertex(cx+hw, cy-hh, cz+hd),
        Vertex(cx+hw, cy+hh, cz+hd), Vertex(cx-hw, cy+hh, cz+hd),
    ]
    faces = [(0,3,2, 0,2,1), (4,5,6, 4,6,7), (0,1,5, 0,5,4),
             (2,3,7, 2,7,6), (0,4,7, 0,7,3), (1,2,6, 1,6,5)]
    tris = []
    for a,b,c,d,e,f in faces:
        for idx3 in [(a,b,c), (d,e,f)]:
            va, vb, vc = v[idx3[0]], v[idx3[1]], v[idx3[2]]
            tris.append(Triangle(tri_normal(va, vb, vc), va, vb, vc))
    return tris

def sphere(r, cx=0, cy=0, cz=0, seg=12, ring=8):
    tris = []
    for i in range(ring):
        lat0 = math.pi * (-0.5 + i / ring)
        lat1 = math.pi * (-0.5 + (i + 1) / ring)
        for j in range(seg):
            lon0 = 2 * math.pi * j / seg
            lon1 = 2 * math.pi * (j + 1) / seg
            pts = []
            for lat in [lat0, lat1]:
                for lon in [lon0, lon1]:
                    pts.append(Vertex(
                        r * math.cos(lat) * math.cos(lon) + cx,
                        r * math.sin(lat) + cy,
                        r * math.cos(lat) * math.sin(lon) + cz
                    ))
            for idx3 in [(0, 2, 1), (1, 2, 3)]:
                va, vb, vc = pts[idx3[0]], pts[idx3[1]], pts[idx3[2]]
                mx = (va.x+vb.x+vc.x)/3 - cx
                my = (va.y+vb.y+vc.y)/3 - cy
                mz = (va.z+vb.z+vc.z)/3 - cz
                n = vec_normalize(mx, my, mz)
                tris.append(Triangle(Vertex(*n), va, vb, vc))
    return tris

def ellipsoid(rx, ry, rz, cx=0, cy=0, cz=0, seg=12, ring=8):
    tris = []
    for i in range(ring):
        lat0 = math.pi * (-0.5 + i / ring)
        lat1 = math.pi * (-0.5 + (i + 1) / ring)
        for j in range(seg):
            lon0 = 2 * math.pi * j / seg
            lon1 = 2 * math.pi * (j + 1) / seg
            pts = []
            for lat in [lat0, lat1]:
                for lon in [lon0, lon1]:
                    pts.append(Vertex(
                        rx * math.cos(lat) * math.cos(lon) + cx,
                        ry * math.sin(lat) + cy,
                        rz * math.cos(lat) * math.sin(lon) + cz
                    ))
            for idx3 in [(0, 2, 1), (1, 2, 3)]:
                va, vb, vc = pts[idx3[0]], pts[idx3[1]], pts[idx3[2]]
                mx = (va.x+vb.x+vc.x)/3 - cx
                my = (va.y+vb.y+vc.y)/3 - cy
                mz = (va.z+vb.z+vc.z)/3 - cz
                n = vec_normalize(mx, my, mz)
                tris.append(Triangle(Vertex(*n), va, vb, vc))
    return tris

def cylinder(r, h, cx=0, cy=0, cz=0, seg=12):
    tris = []
    hh = h / 2
    for i in range(seg):
        a0 = 2*math.pi*i/seg
        a1 = 2*math.pi*(i+1)/seg
        x0, z0 = r*math.cos(a0)+cx, r*math.sin(a0)+cz
        x1, z1 = r*math.cos(a1)+cx, r*math.sin(a1)+cz
        mid = (a0+a1)/2
        n = vec_normalize(math.cos(mid), 0, math.sin(mid))
        normal = Vertex(*n)
        tris.append(Triangle(normal, Vertex(x0,cy-hh,z0), Vertex(x1,cy-hh,z1), Vertex(x1,cy+hh,z1)))
        tris.append(Triangle(normal, Vertex(x0,cy-hh,z0), Vertex(x1,cy+hh,z1), Vertex(x0,cy+hh,z0)))
    for i in range(seg):
        a0, a1 = 2*math.pi*i/seg, 2*math.pi*(i+1)/seg
        tris.append(Triangle(Vertex(0,1,0), Vertex(cx,cy+hh,cz),
            Vertex(r*math.cos(a0)+cx, cy+hh, r*math.sin(a0)+cz),
            Vertex(r*math.cos(a1)+cx, cy+hh, r*math.sin(a1)+cz)))
    for i in range(seg):
        a0, a1 = 2*math.pi*i/seg, 2*math.pi*(i+1)/seg
        tris.append(Triangle(Vertex(0,-1,0), Vertex(cx,cy-hh,cz),
            Vertex(r*math.cos(a1)+cx, cy-hh, r*math.sin(a1)+cz),
            Vertex(r*math.cos(a0)+cx, cy-hh, r*math.sin(a0)+cz)))
    return tris

def cone(r, h, cx=0, cy=0, cz=0, seg=12):
    tris = []
    hh = h/2
    apex_y, base_y = cy + hh, cy - hh
    for i in range(seg):
        a0, a1 = 2*math.pi*i/seg, 2*math.pi*(i+1)/seg
        x0, z0 = r*math.cos(a0)+cx, r*math.sin(a0)+cz
        x1, z1 = r*math.cos(a1)+cx, r*math.sin(a1)+cz
        mid = (a0+a1)/2
        n = vec_normalize(math.cos(mid), r/h, math.sin(mid))
        tris.append(Triangle(Vertex(*n), Vertex(cx, apex_y, cz), Vertex(x1, base_y, z1), Vertex(x0, base_y, z0)))
    for i in range(seg):
        a0, a1 = 2*math.pi*i/seg, 2*math.pi*(i+1)/seg
        tris.append(Triangle(Vertex(0,-1,0), Vertex(cx,base_y,cz),
            Vertex(r*math.cos(a0)+cx, base_y, r*math.sin(a0)+cz),
            Vertex(r*math.cos(a1)+cx, base_y, r*math.sin(a1)+cz)))
    return tris

def ball_joint(r, seg=10, ring=6):
    return sphere(r, seg=seg, ring=ring)

def ball_socket(r, depth, seg=10):
    tris = []
    for i in range(seg):
        a0, a1 = 2*math.pi*i/seg, 2*math.pi*(i+1)/seg
        tris.append(Triangle(Vertex(0,-1,0), Vertex(0,0,0),
            Vertex(r*math.cos(a0), -depth, r*math.sin(a0)),
            Vertex(r*math.cos(a1), -depth, r*math.sin(a1))))
    for i in range(ring//2):
        lat0 = math.pi * (i / ring)
        lat1 = math.pi * ((i + 1) / ring)
        for j in range(seg):
            lon0, lon1 = 2*math.pi*j/seg, 2*math.pi*(j+1)/seg
            pts = []
            for lat in [lat0, lat1]:
                for lon in [lon0, lon1]:
                    pts.append(Vertex(
                        r*math.cos(lat)*math.cos(lon),
                        -depth - r*math.sin(lat),
                        r*math.cos(lat)*math.sin(lon)
                    ))
            for idx3 in [(0,2,1), (1,2,3)]:
                va, vb, vc = pts[idx3[0]], pts[idx3[1]], pts[idx3[2]]
                n = tri_normal(va, vb, vc)
                tris.append(Triangle(Vertex(-n.x,-n.y,-n.z), va, vb, vc))
    return tris

# ============================================================================
# BIOMECÂNICA
# ============================================================================

BIOMECHANICS = {
    'bovino': {
        'head_neck': {'type': 'ball_socket', 'pitch': (-30, 45), 'yaw': (-40, 40)},
        'front_leg': {'type': 'hinge', 'pitch': (-45, 30)},
        'hind_leg': {'type': 'hinge', 'pitch': (-50, 35)},
        'tail': {'type': 'pin', 'pitch': (-20, 60), 'yaw': (-30, 30)},
    },
    'equino': {
        'head_neck': {'type': 'ball_socket', 'pitch': (-30, 50), 'yaw': (-45, 45)},
        'front_leg': {'type': 'hinge', 'pitch': (-55, 40)},
        'hind_leg': {'type': 'hinge', 'pitch': (-60, 45)},
        'tail': {'type': 'pin', 'pitch': (-10, 50), 'yaw': (-35, 35)},
    },
    'suino': {
        'head_neck': {'type': 'ball_socket', 'pitch': (-40, 30), 'yaw': (-50, 50)},
        'front_leg': {'type': 'hinge', 'pitch': (-35, 25)},
        'hind_leg': {'type': 'hinge', 'pitch': (-40, 30)},
        'tail': {'type': 'pin', 'pitch': (-30, 80), 'yaw': (-40, 40)},
    },
    'ave': {
        'head_neck': {'type': 'ball_socket', 'pitch': (-50, 30), 'yaw': (-60, 60)},
        'wing': {'type': 'hinge', 'pitch': (-20, 80)},
        'leg': {'type': 'hinge', 'pitch': (-40, 20)},
    },
    'ovino': {
        'head_neck': {'type': 'ball_socket', 'pitch': (-35, 40), 'yaw': (-45, 45)},
        'front_leg': {'type': 'hinge', 'pitch': (-45, 30)},
        'hind_leg': {'type': 'hinge', 'pitch': (-50, 35)},
    },
}

# ============================================================================
# GERADORES SÓLIDOS
# ============================================================================

def gen_bovine(s):
    m = []
    m.append(ellipsoid(2.0*s, 1.8*s, 3.5*s, 0, 2.5*s, 0, 16, 12))
    m.append(cylinder(0.9*s, 2.0*s, 0, 4.0*s, 0.5*s, 12))
    m.append(ellipsoid(1.0*s, 0.9*s, 1.5*s, 0, 5.2*s, 1.2*s, 12, 10))
    m.append(ellipsoid(0.7*s, 0.6*s, 0.8*s, 0, 4.8*s, 2.2*s, 10, 8))
    m.append(cone(0.2*s, 0.8*s, -0.5*s, 5.5*s, 1.0*s, 8))
    m.append(cone(0.2*s, 0.8*s, 0.5*s, 5.5*s, 1.0*s, 8))
    m.append(ellipsoid(0.3*s, 0.4*s, 0.5*s, -0.7*s, 5.3*s, 0.8*s, 8, 6))
    m.append(ellipsoid(0.3*s, 0.4*s, 0.5*s, 0.7*s, 5.3*s, 0.8*s, 8, 6))
    for lx, lz in [(-1.2*s, 2.0*s),(1.2*s, 2.0*s),(-1.2*s,-2.0*s),(1.2*s,-2.0*s)]:
        m.append(cylinder(0.4*s, 2.5*s, lx, 0.8*s, lz, 10))
        m.append(cylinder(0.45*s, 0.3*s, lx, 0.15*s, lz, 10))
    m.append(cylinder(0.15*s, 2.0*s, 0, 3.0*s, -3.5*s, 8))
    m.append(ellipsoid(0.3*s, 0.3*s, 0.5*s, 0, 2.0*s, -4.2*s, 8, 6))
    m.append(ellipsoid(0.8*s, 0.6*s, 1.0*s, 0, 0.8*s, -1.0*s, 10, 8))
    return m

def gen_equine(s):
    m = []
    m.append(ellipsoid(1.8*s, 1.6*s, 4.0*s, 0, 3.0*s, 0, 16, 12))
    m.append(cylinder(0.7*s, 2.5*s, 0, 4.5*s, 0.8*s, 12))
    m.append(ellipsoid(0.8*s, 0.7*s, 1.8*s, 0, 5.8*s, 1.5*s, 12, 10))
    m.append(ellipsoid(0.5*s, 0.5*s, 1.0*s, 0, 5.5*s, 2.5*s, 10, 8))
    m.append(cone(0.15*s, 0.5*s, -0.4*s, 6.2*s, 1.2*s, 8))
    m.append(cone(0.15*s, 0.5*s, 0.4*s, 6.2*s, 1.2*s, 8))
    for lx, lz in [(-1.0*s, 2.2*s),(1.0*s, 2.2*s),(-1.0*s,-2.2*s),(1.0*s,-2.2*s)]:
        m.append(cylinder(0.3*s, 3.0*s, lx, 0.8*s, lz, 10))
        m.append(cylinder(0.35*s, 0.25*s, lx, 0.15*s, lz, 10))
    m.append(cylinder(0.12*s, 2.5*s, 0, 3.2*s, -3.8*s, 8))
    m.append(ellipsoid(0.4*s, 0.8*s, 0.3*s, 0, 1.5*s, -4.8*s, 8, 6))
    m.append(ellipsoid(0.3*s, 0.8*s, 1.5*s, 0.8*s, 4.5*s, 0.5*s, 8, 10))
    return m

def gen_porine(s):
    m = []
    m.append(ellipsoid(2.2*s, 1.5*s, 2.8*s, 0, 2.0*s, 0, 16, 12))
    m.append(ellipsoid(1.2*s, 1.0*s, 1.3*s, 0, 2.5*s, 1.8*s, 12, 10))
    m.append(cylinder(0.6*s, 0.5*s, 0, 2.3*s, 2.8*s, 12))
    m.append(ellipsoid(0.5*s, 0.3*s, 0.2*s, 0, 2.3*s, 3.1*s, 10, 8))
    m.append(ellipsoid(0.4*s, 0.5*s, 0.2*s, -0.7*s, 3.0*s, 1.2*s, 8, 6))
    m.append(ellipsoid(0.4*s, 0.5*s, 0.2*s, 0.7*s, 3.0*s, 1.2*s, 8, 6))
    for lx, lz in [(-1.3*s, 1.5*s),(1.3*s, 1.5*s),(-1.3*s,-1.5*s),(1.3*s,-1.5*s)]:
        m.append(cylinder(0.35*s, 1.2*s, lx, 0.5*s, lz, 10))
        m.append(cylinder(0.4*s, 0.2*s, lx, 0.1*s, lz, 10))
    m.append(cylinder(0.1*s, 0.8*s, 0, 2.5*s, -2.5*s, 8))
    return m

def gen_ave(s):
    m = []
    m.append(ellipsoid(1.5*s, 1.3*s, 2.0*s, 0, 2.0*s, 0, 16, 12))
    m.append(sphere(0.7*s, 0, 3.2*s, 0.5*s, 12, 10))
    m.append(cone(0.2*s, 0.5*s, 0, 3.5*s, 1.0*s, 8))
    m.append(ellipsoid(0.15*s, 0.4*s, 0.3*s, 0, 3.6*s, 0.3*s, 6, 4))
    m.append(ellipsoid(0.15*s, 0.35*s, 0.3*s, 0, 3.5*s, 0.6*s, 6, 4))
    m.append(ellipsoid(0.2*s, 0.25*s, 0.15*s, 0, 3.0*s, 1.0*s, 6, 4))
    m.append(ellipsoid(0.3*s, 0.5*s, 0.8*s, -1.3*s, 2.0*s, 0.5*s, 8, 6))
    m.append(ellipsoid(0.3*s, 0.5*s, 0.8*s, 1.3*s, 2.0*s, 0.5*s, 8, 6))
    for lx in [-0.5*s, 0.5*s]:
        m.append(cylinder(0.15*s, 1.0*s, lx, 0.5*s, 0.5*s, 8))
        m.append(ellipsoid(0.3*s, 0.1*s, 0.4*s, lx, 0.05*s, 0.8*s, 6, 4))
    m.append(ellipsoid(0.4*s, 0.3*s, 0.8*s, 0, 2.5*s, -1.8*s, 8, 6))
    return m

def gen_ovine(s):
    m = []
    m.append(ellipsoid(2.0*s, 1.8*s, 3.0*s, 0, 2.5*s, 0, 16, 12))
    for wx, wy, wz in [(-1.5*s, 3.0*s, 1.0*s),(1.5*s, 3.0*s, 1.0*s),(-1.5*s, 3.0*s, -1.0*s),(1.5*s, 3.0*s, -1.0*s),(0, 3.5*s, 2.0*s),(0, 3.5*s, -2.0*s),(-1.8*s, 2.5*s, 0),(1.8*s, 2.5*s, 0),(0, 3.2*s, 0)]:
        m.append(sphere(0.6*s, wx, wy, wz, 10, 8))
    m.append(ellipsoid(0.8*s, 0.9*s, 1.2*s, 0, 2.8*s, 1.5*s, 12, 10))
    m.append(ellipsoid(0.5*s, 0.5*s, 0.6*s, 0, 2.5*s, 2.2*s, 10, 8))
    m.append(ellipsoid(0.25*s, 0.4*s, 0.15*s, -0.5*s, 2.9*s, 1.3*s, 8, 6))
    m.append(ellipsoid(0.25*s, 0.4*s, 0.15*s, 0.5*s, 2.9*s, 1.3*s, 8, 6))
    for lx, lz in [(-1.0*s, 1.5*s),(1.0*s, 1.5*s),(-1.0*s,-1.5*s),(1.0*s,-1.5*s)]:
        m.append(cylinder(0.25*s, 1.5*s, lx, 0.6*s, lz, 8))
        m.append(cylinder(0.3*s, 0.2*s, lx, 0.1*s, lz, 8))
    m.append(ellipsoid(0.3*s, 0.3*s, 0.4*s, 0, 2.2*s, -2.5*s, 6, 4))
    return m

SOLID_GENERATORS = {
    'bovino': ('Bovino (Vaca/Touro)', gen_bovine, 8.0),
    'equino': ('Equino (Cavalo)', gen_equine, 8.0),
    'suino':  ('Suíno (Porco)', gen_porine, 10.0),
    'ave':    ('Ave (Galinha)', gen_ave, 12.0),
    'ovino':  ('Ovino (Ovelha)', gen_ovine, 9.0),
}

# ============================================================================
# GERADORES ARTICULADOS (simplificados para web)
# ============================================================================

def articulated_bovine(s, jd):
    parts = []
    biomech = BIOMECHANICS['bovino']
    
    trunk = [ellipsoid(2.0*s, 1.8*s, 3.5*s, 0, 2.5*s, 0, 16, 12)]
    trunk.append(ellipsoid(0.8*s, 0.6*s, 1.0*s, 0, 0.8*s, -1.0*s, 10, 8))
    trunk.extend(ball_socket(0.5*s, 0.3*s, 10))
    parts.append(Part(name="01_tronco", description="Corpo + úbere", triangles=trunk,
        joints=[Joint("pescoço", "ball_socket", (0, 4.0*s, 0.5*s), jd, jd*0.8, (True,True,True), "Cabeça")] +
               [Joint(f"pata_{side}", "hinge", (lx, 1.8*s, lz), jd*0.8, jd, (False,True,False), "Pata")
                for side, (lx, lz) in [("fe", -1.2*s, 2.0*s),("fd", 1.2*s, 2.0*s),("te", -1.2*s, -2.0*s),("td", 1.2*s, -2.0*s)]]))
    
    head = [ellipsoid(1.0*s, 0.9*s, 1.5*s, 0, 0, 0.7*s, 12, 10)]
    head.append(ellipsoid(0.7*s, 0.6*s, 0.8*s, 0, -0.4*s, 1.7*s, 10, 8))
    head.append(cone(0.2*s, 0.8*s, -0.5*s, 0.3*s, 0.5*s, 8))
    head.append(cone(0.2*s, 0.8*s, 0.5*s, 0.3*s, 0.5*s, 8))
    head.extend(ball_joint(0.5*s, 10, 6))
    parts.append(Part(name="02_cabeca", description="Cabeça + chifres", triangles=head, connect_to="01_tronco"))
    
    for pname, pdesc, lx, lz in [("03_pata_fe", "Pata frontal ESQ", -1.2*s, 2.0*s),("04_pata_fd", "Pata frontal DIR", 1.2*s, 2.0*s),("05_pata_te", "Pata traseira ESQ", -1.2*s, -2.0*s),("06_pata_td", "Pata traseira DIR", 1.2*s, -2.0*s)]:
        leg = [ball_socket(0.3*s, 0.2*s, 8)]
        leg.append(cylinder(0.35*s, 1.5*s, 0, 0.7*s, 0, 10))
        leg.append(cylinder(0.3*s, 0.8*s, 0, 0.2*s, 0, 10))
        leg.append(cylinder(0.4*s, 0.25*s, 0, -0.2*s, 0, 10))
        parts.append(Part(name=pname, description=pdesc, triangles=leg, connect_to="01_tronco"))
    
    tail = [cylinder(0.12*s, 2.0*s, 0, 0, 0, 8)]
    tail.append(ellipsoid(0.3*s, 0.3*s, 0.5*s, 0, -1.0*s, -0.2*s, 8, 6))
    parts.append(Part(name="07_rabo", description="Rabo", triangles=tail, connect_to="01_tronco"))
    
    guide = "BOVINO ARTICULADO\nPeças: 7\n1. Encaixe a CABEÇA no tronco\n2. Insira as 4 PATAS\n3. Conecte o RABO"
    return AnimalModel("bovino", "Bovino", [], parts, guide)

def articulated_equine(s, jd):
    parts = []
    trunk = [ellipsoid(1.8*s, 1.6*s, 4.0*s, 0, 3.0*s, 0, 16, 12)]
    trunk.extend(ball_socket(0.45*s, 0.3*s, 10))
    parts.append(Part(name="01_tronco", description="Corpo", triangles=trunk))
    
    head = [ellipsoid(0.8*s, 0.7*s, 1.8*s, 0, 0, 0.8*s, 12, 10)]
    head.append(ellipsoid(0.5*s, 0.5*s, 1.0*s, 0, -0.3*s, 1.8*s, 10, 8))
    head.extend(ball_joint(0.45*s, 10, 6))
    parts.append(Part(name="02_cabeca", description="Cabeça", triangles=head, connect_to="01_tronco"))
    
    for pname, pdesc, lx, lz in [("03_pata_fe", "Pata frontal ESQ", -1.0*s, 2.2*s),("04_pata_fd", "Pata frontal DIR", 1.0*s, 2.2*s),("05_pata_te", "Pata traseira ESQ", -1.0*s, -2.2*s),("06_pata_td", "Pata traseira DIR", 1.0*s, -2.2*s)]:
        leg = [ball_socket(0.25*s, 0.2*s, 8)]
        leg.append(cylinder(0.25*s, 1.0*s, 0, 0.6*s, 0, 10))
        leg.append(cylinder(0.22*s, 0.8*s, 0, 0.3*s, 0, 10))
        leg.append(cylinder(0.3*s, 0.2*s, 0, -0.3*s, 0, 10))
        parts.append(Part(name=pname, description=pdesc, triangles=leg, connect_to="01_tronco"))
    
    tail = [cylinder(0.1*s, 2.5*s, 0, 0, 0, 8)]
    tail.append(ellipsoid(0.4*s, 0.8*s, 0.3*s, 0, -1.2*s, 0, 8, 6))
    parts.append(Part(name="07_rabo", description="Rabo", triangles=tail, connect_to="01_tronco"))
    
    return AnimalModel("equino", "Equino", [], parts, "EQUINO: Monte cabeça, 4 patas e rabo no tronco.")

def articulated_porine(s, jd):
    parts = []
    trunk = [ellipsoid(2.2*s, 1.5*s, 2.8*s, 0, 2.0*s, 0, 16, 12)]
    trunk.extend(ball_socket(0.5*s, 0.3*s, 10))
    parts.append(Part(name="01_tronco", description="Corpo", triangles=trunk))
    
    head = [ellipsoid(1.2*s, 1.0*s, 1.3*s, 0, 0, 0.3*s, 12, 10)]
    head.append(cylinder(0.6*s, 0.5*s, 0, -0.2*s, 1.3*s, 12))
    head.append(ellipsoid(0.4*s, 0.5*s, 0.2*s, -0.5*s, 0.2*s, 0.2*s, 8, 6))
    head.append(ellipsoid(0.4*s, 0.5*s, 0.2*s, 0.5*s, 0.2*s, 0.2*s, 8, 6))
    head.extend(ball_joint(0.5*s, 10, 6))
    parts.append(Part(name="02_cabeca", description="Cabeça + focinho", triangles=head, connect_to="01_tronco"))
    
    for pname, pdesc, lx, lz in [("03_pata_fe", "Pata frontal ESQ", -1.3*s, 1.5*s),("04_pata_fd", "Pata frontal DIR", 1.3*s, 1.5*s),("05_pata_te", "Pata traseira ESQ", -1.3*s, -1.5*s),("06_pata_td", "Pata traseira DIR", 1.3*s, -1.5*s)]:
        leg = [ball_socket(0.25*s, 0.15*s, 8)]
        leg.append(cylinder(0.3*s, 0.7*s, 0, 0.3*s, 0, 10))
        leg.append(cylinder(0.35*s, 0.15*s, 0, -0.1*s, 0, 10))
        parts.append(Part(name=pname, description=pdesc, triangles=leg, connect_to="01_tronco"))
    
    return AnimalModel("suino", "Suíno", [], parts, "SUÍNO: Monte cabeça e 4 patas curtas.")

def articulated_ave(s, jd):
    parts = []
    trunk = [ellipsoid(1.5*s, 1.3*s, 2.0*s, 0, 2.0*s, 0, 16, 12)]
    trunk.extend(ball_socket(0.4*s, 0.25*s, 10))
    parts.append(Part(name="01_tronco", description="Corpo", triangles=trunk))
    
    head = [sphere(0.7*s, 0, 0, 0, 12, 10)]
    head.append(cone(0.2*s, 0.5*s, 0, 0.2*s, 0.5*s, 8))
    head.append(ellipsoid(0.15*s, 0.4*s, 0.3*s, 0, 0.3*s, -0.1*s, 6, 4))
    head.extend(ball_joint(0.4*s, 10, 6))
    parts.append(Part(name="02_cabeca", description="Cabeça + bico", triangles=head, connect_to="01_tronco"))
    
    for pname, pdesc, side in [("03_asa_esq", "Asa ESQ", -1), ("04_asa_dir", "Asa DIR", 1)]:
        wing = [cylinder(0.08*s, 0.3*s, 0, 0, 0, 8)]
        wing.append(ellipsoid(0.3*s, 0.5*s, 0.8*s, 0, -0.3*s, 0.2*s, 8, 6))
        parts.append(Part(name=pname, description=pdesc, triangles=wing, connect_to="01_tronco"))
    
    for pname, pdesc, lx in [("05_pata_esq", "Perna ESQ", -0.5*s), ("06_pata_dir", "Perna DIR", 0.5*s)]:
        leg = [cylinder(0.08*s, 0.3*s, 0, 0, 0, 8)]
        leg.append(cylinder(0.12*s, 0.6*s, 0, -0.3*s, 0, 8))
        leg.append(ellipsoid(0.25*s, 0.08*s, 0.35*s, 0, -0.6*s, 0.15*s, 6, 4))
        parts.append(Part(name=pname, description=pdesc, triangles=leg, connect_to="01_tronco"))
    
    return AnimalModel("ave", "Ave", [], parts, "AVE: Monte cabeça, 2 asas e 2 pernas.")

def articulated_ovine(s, jd):
    parts = []
    trunk = [ellipsoid(2.0*s, 1.8*s, 3.0*s, 0, 2.5*s, 0, 16, 12)]
    for wx, wy, wz in [(-1.5*s, 3.0*s, 1.0*s),(1.5*s, 3.0*s, 1.0*s),(-1.5*s, 3.0*s, -1.0*s),(1.5*s, 3.0*s, -1.0*s),(0, 3.5*s, 2.0*s),(0, 3.5*s, -2.0*s),(-1.8*s, 2.5*s, 0),(1.8*s, 2.5*s, 0),(0, 3.2*s, 0)]:
        trunk.append(sphere(0.6*s, wx, wy, wz, 10, 8))
    trunk.extend(ball_socket(0.4*s, 0.25*s, 10))
    parts.append(Part(name="01_tronco", description="Corpo com lã", triangles=trunk))
    
    head = [ellipsoid(0.8*s, 0.9*s, 1.2*s, 0, 0, 0.3*s, 12, 10)]
    head.append(ellipsoid(0.5*s, 0.5*s, 0.6*s, 0, -0.3*s, 1.0*s, 10, 8))
    head.extend(ball_joint(0.4*s, 10, 6))
    parts.append(Part(name="02_cabeca", description="Cabeça", triangles=head, connect_to="01_tronco"))
    
    for pname, pdesc, lx, lz in [("03_pata_fe", "Pata frontal ESQ", -1.0*s, 1.5*s),("04_pata_fd", "Pata frontal DIR", 1.0*s, 1.5*s),("05_pata_te", "Pata traseira ESQ", -1.0*s, -1.5*s),("06_pata_td", "Pata traseira DIR", 1.0*s, -1.5*s)]:
        leg = [ball_socket(0.2*s, 0.15*s, 8)]
        leg.append(cylinder(0.22*s, 0.8*s, 0, 0.4*s, 0, 8))
        leg.append(cylinder(0.25*s, 0.15*s, 0, -0.05*s, 0, 8))
        parts.append(Part(name=pname, description=pdesc, triangles=leg, connect_to="01_tronco"))
    
    return AnimalModel("ovino", "Ovino", [], parts, "OVINO: Monte cabeça e 4 patas no corpo com lã.")

ARTICULATED_GENERATORS = {
    'bovino': ('Bovino Articulado', articulated_bovine),
    'equino': ('Equino Articulado', articulated_equine),
    'suino':  ('Suíno Articulado', articulated_porine),
    'ave':    ('Ave Articulado', articulated_ave),
    'ovino':  ('Ovino Articulado', articulated_ovine),
}

# ============================================================================
# API PÚBLICA PARA WEB
# ============================================================================

def gerar_solido(animal_key, escala_mm, out_dir):
    label, gen, default_scale = SOLID_GENERATORS[animal_key]
    s = escala_mm if escala_mm else default_scale
    tris = gen(s)
    fname = f"{animal_key}_solida_{int(s*10)}mm.stl"
    fpath = os.path.join(out_dir, fname)
    write_stl(tris, fpath)
    return fpath

def gerar_articulado(animal_key, escala_mm, joint_diam_mm, out_dir):
    label, gen = ARTICULATED_GENERATORS[animal_key]
    s = escala_mm if escala_mm else 8.0
    jd = joint_diam_mm
    model = gen(s, jd)
    piece_dir = os.path.join(out_dir, f"{animal_key}_articulado")
    os.makedirs(piece_dir, exist_ok=True)
    
    for part in model.parts:
        fname = f"{part.name}.stl"
        fpath = os.path.join(piece_dir, fname)
        write_stl(part.triangles, fpath)
    
    guide_path = os.path.join(piece_dir, "00_GUIA_MONTAGEM.txt")
    with open(guide_path, 'w', encoding='utf-8') as f:
        f.write(model.assembly_guide)
        f.write("\n\nPEÇAS:\n")
        for p in model.parts:
            f.write(f"- {p.name}: {p.description}\n")
    
    return piece_dir