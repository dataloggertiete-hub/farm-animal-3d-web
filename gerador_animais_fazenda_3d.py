#!/usr/bin/env python3
"""
Gerador de Animais de Fazenda em 3D para Impressão
===================================================
Modelos paramétricos para: Bovinos, Equinos, Suínos, Aves, Ovinos

Funcionalidades:
  - Escala ajustável via linha de comando
  - Modo sólido (uma peça) ou articulado (múltiplas peças com juntas)
  - Articulações baseadas na biomecânica real de cada espécie
  - Gera STL binários prontos para slicer
  - Inclui guia de montagem para modelos articulados

Uso:
  python gerador_animais_fazenda_3d.py
  python gerador_animais_fazenda_3d.py --animal bovino --scale 10 --articulated
  python gerador_animais_fazenda_3d.py --all --articulated --scale 8 --joint-diameter 3

Autor: Gerador Automático v2.0
"""

import math
import os
import sys
import struct
import json
import argparse
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict

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
    """Define uma articulação entre duas peças."""
    name: str
    type: str  # 'ball_socket', 'pin', 'hinge'
    position: Tuple[float, float, float]  # Posição no corpo da peça
    diameter: float
    length: float  # Comprimento do pino/bola
    rotation_axes: Tuple[bool, bool, bool]  # (X, Y, Z) - eixos permitidos
    description: str

@dataclass
class Part:
    """Uma peça individual do modelo articulado."""
    name: str
    description: str
    triangles: List[Triangle]
    joints: List[Joint] = field(default_factory=list)
    connect_to: str = ""  # Nome da peça à qual se conecta
    movement_range: str = ""  # Descrição do movimento

@dataclass
class AnimalModel:
    """Modelo completo de um animal (sólido ou articulado)."""
    name: str
    species: str
    solid_triangles: List[Triangle]
    parts: List[Part] = field(default_factory=list)
    assembly_guide: str = ""

# ============================================================================
# UTILITÁRIOS MATEMÁTICOS
# ============================================================================

def vec_normalize(x: float, y: float, z: float) -> Tuple[float, float, float]:
    length = math.sqrt(x*x + y*y + z*z)
    if length == 0:
        return (0.0, 0.0, 0.0)
    return (x/length, y/length, z/length)

def cross(ax, ay, az, bx, by, bz):
    return (ay*bz - az*by, az*bx - ax*bz, ax*by - ay*bx)

def tri_normal(v1: Vertex, v2: Vertex, v3: Vertex) -> Vertex:
    ax = v2.x - v1.x
    ay = v2.y - v1.y
    az = v2.z - v1.z
    bx = v3.x - v1.x
    by = v3.y - v1.y
    bz = v3.z - v1.z
    nx, ny, nz = cross(ax, ay, az, bx, by, bz)
    nx, ny, nz = vec_normalize(nx, ny, nz)
    return Vertex(nx, ny, nz)

# ============================================================================
# ESCREVEDOR STL
# ============================================================================

def flatten(triangles):
    """Achatar listas de listas de triângulos."""
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

def write_stl(triangles: List[Triangle], filepath: str):
    """Escreve STL binário."""
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
# PRIMITIVOS GEOMÉTRICOS
# ============================================================================

def box(w, h, d, cx=0, cy=0, cz=0):
    """Caixa centrada."""
    hw, hh, hd = w/2, h/2, d/2
    v = [
        Vertex(cx-hw, cy-hh, cz-hd), Vertex(cx+hw, cy-hh, cz-hd),
        Vertex(cx+hw, cy+hh, cz-hd), Vertex(cx-hw, cy+hh, cz-hd),
        Vertex(cx-hw, cy-hh, cz+hd), Vertex(cx+hw, cy-hh, cz+hd),
        Vertex(cx+hw, cy+hh, cz+hd), Vertex(cx-hw, cy+hh, cz+hd),
    ]
    faces = [
        (0,3,2, 0,2,1), (4,5,6, 4,6,7),
        (0,1,5, 0,5,4), (2,3,7, 2,7,6),
        (0,4,7, 0,7,3), (1,2,6, 1,6,5),
    ]
    tris = []
    for i in range(0, len(faces), 6):
        a, b, c = faces[i], faces[i+1], faces[i+2]
        d2, e2, f2 = faces[i+3], faces[i+4], faces[i+5]
        for idx3 in [(a,b,c), (d2,e2,f2)]:
            va, vb, vc = v[idx3[0]], v[idx3[1]], v[idx3[2]]
            tris.append(Triangle(tri_normal(va, vb, vc), va, vb, vc))
    return tris

def sphere(r, cx=0, cy=0, cz=0, seg=12, ring=8):
    """Esfera centrada."""
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
    """Elipsoide centrado."""
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
    """Cilindro vertical centrado em (cx,cy,cz)."""
    tris = []
    hh = h / 2
    for i in range(seg):
        a0 = 2*math.pi*i/seg
        a1 = 2*math.pi*(i+1)/seg
        x0 = r*math.cos(a0)+cx; z0 = r*math.sin(a0)+cz
        x1 = r*math.cos(a1)+cx; z1 = r*math.sin(a1)+cz
        mid = (a0+a1)/2
        n = vec_normalize(math.cos(mid), 0, math.sin(mid))
        normal = Vertex(*n)
        # Side
        tris.append(Triangle(normal, Vertex(x0,cy-hh,z0), Vertex(x1,cy-hh,z1), Vertex(x1,cy+hh,z1)))
        tris.append(Triangle(normal, Vertex(x0,cy-hh,z0), Vertex(x1,cy+hh,z1), Vertex(x0,cy+hh,z0)))
    # Top
    for i in range(seg):
        a0 = 2*math.pi*i/seg; a1 = 2*math.pi*(i+1)/seg
        tris.append(Triangle(Vertex(0,1,0),
            Vertex(cx,cy+hh,cz),
            Vertex(r*math.cos(a0)+cx, cy+hh, r*math.sin(a0)+cz),
            Vertex(r*math.cos(a1)+cx, cy+hh, r*math.sin(a1)+cz)))
    # Bottom
    for i in range(seg):
        a0 = 2*math.pi*i/seg; a1 = 2*math.pi*(i+1)/seg
        tris.append(Triangle(Vertex(0,-1,0),
            Vertex(cx,cy-hh,cz),
            Vertex(r*math.cos(a1)+cx, cy-hh, r*math.sin(a1)+cz),
            Vertex(r*math.cos(a0)+cx, cy-hh, r*math.sin(a0)+cz)))
    return tris

def cone(r, h, cx=0, cy=0, cz=0, seg=12):
    """Cone vertical (base em cy-h/2, ápice em cy+h/2)."""
    tris = []
    hh = h/2
    apex_y = cy + hh
    base_y = cy - hh
    for i in range(seg):
        a0 = 2*math.pi*i/seg; a1 = 2*math.pi*(i+1)/seg
        x0 = r*math.cos(a0)+cx; z0 = r*math.sin(a0)+cz
        x1 = r*math.cos(a1)+cx; z1 = r*math.sin(a1)+cz
        mid = (a0+a1)/2
        n = vec_normalize(math.cos(mid), r/h, math.sin(mid))
        tris.append(Triangle(Vertex(*n),
            Vertex(cx, apex_y, cz),
            Vertex(x1, base_y, z1),
            Vertex(x0, base_y, z0)))
    # Base
    for i in range(seg):
        a0 = 2*math.pi*i/seg; a1 = 2*math.pi*(i+1)/seg
        tris.append(Triangle(Vertex(0,-1,0),
            Vertex(cx,base_y,cz),
            Vertex(r*math.cos(a0)+cx, base_y, r*math.sin(a0)+cz),
            Vertex(r*math.cos(a1)+cx, base_y, r*math.sin(a1)+cz)))
    return tris

# ============================================================================
# COMPONENTES DE JUNTA (ARTICULAÇÃO)
# ============================================================================

def ball_joint(r, seg=10, ring=6):
    """Bola esférica para junta esfera-soquete."""
    return sphere(r, seg=seg, ring=ring)

def ball_socket(r, depth, seg=10):
    """Soquete (cavidade) para junta esfera-soquete."""
    tris = []
    # Base plana
    for i in range(seg):
        a0 = 2*math.pi*i/seg; a1 = 2*math.pi*(i+1)/seg
        tris.append(Triangle(Vertex(0,-1,0),
            Vertex(0,0,0),
            Vertex(r*math.cos(a0), -depth, r*math.sin(a0)),
            Vertex(r*math.cos(a1), -depth, r*math.sin(a1))))
    # Parede interna (hemisfério invertido)
    for i in range(ring//2):
        lat0 = math.pi * (i / ring)
        lat1 = math.pi * ((i + 1) / ring)
        for j in range(seg):
            lon0 = 2*math.pi*j/seg
            lon1 = 2*math.pi*(j+1)/seg
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
                # Inverter normal para apontar para dentro
                tris.append(Triangle(Vertex(-n.x,-n.y,-n.z), va, vb, vc))
    return tris

def pin_connector(diameter, length, seg=8):
    """Pino de conexão cilíndrico."""
    r = diameter / 2
    tris = cylinder(r, length, seg=seg)
    # Adicionar chanfro na ponta
    for i in range(seg):
        a0 = 2*math.pi*i/seg; a1 = 2*math.pi*(i+1)/seg
        tris.append(Triangle(Vertex(0,1,0),
            Vertex(0, length/2, 0),
            Vertex(r*0.5*math.cos(a0), length/2, r*0.5*math.sin(a0)),
            Vertex(r*0.5*math.cos(a1), length/2, r*0.5*math.sin(a1))))
    return tris

def hinge_pin(diameter, length, seg=8):
    """Pino de dobradiça para juntas de rotação limitada."""
    r = diameter / 2
    tris = cylinder(r, length, seg=seg)
    # Rolhas nas pontas
    tris.append(cone(r*1.2, 0.3, 0, length/2 + 0.15, 0, seg))
    tris.append(cone(r*1.2, 0.3, 0, -length/2 - 0.15, 0, seg))
    return tris

def socket_hole(radius, length, seg=8):
    """Canal interno para encaixe de pino."""
    return cylinder(radius * 0.95, length, seg=seg)

# ============================================================================
# BIOMECÂNICA DOS ANIMAIS
# ============================================================================

BIOMECHANICS = {
    'bovino': {
        'head_neck': {'type': 'ball_socket', 'pitch': (-30, 45), 'yaw': (-40, 40), 'roll': (-15, 15)},
        'front_leg': {'type': 'hinge', 'pitch': (-45, 30), 'description': 'Articulação do joelho/cotovelo bovino'},
        'hind_leg': {'type': 'hinge', 'pitch': (-50, 35), 'description': 'Articulação do jarrete'},
        'tail': {'type': 'pin', 'pitch': (-20, 60), 'yaw': (-30, 30)},
        'vertebrae': {'type': 'pin', 'pitch': (-10, 10), 'yaw': (-5, 5), 'description': 'Coluna vertebral flexível'},
    },
    'equino': {
        'head_neck': {'type': 'ball_socket', 'pitch': (-30, 50), 'yaw': (-45, 45), 'roll': (-20, 20)},
        'front_leg': {'type': 'hinge', 'pitch': (-55, 40), 'description': 'Articulação do jarrete anterior (equino)'},
        'hind_leg': {'type': 'hinge', 'pitch': (-60, 45), 'description': 'Articulação do jarrete posterior'},
        'knee': {'type': 'hinge', 'pitch': (-60, 10), 'description': 'Joelho (coto) do equino'},
        'tail': {'type': 'pin', 'pitch': (-10, 50), 'yaw': (-35, 35)},
        'vertebrae': {'type': 'pin', 'pitch': (-15, 15), 'yaw': (-5, 5)},
    },
    'suino': {
        'head_neck': {'type': 'ball_socket', 'pitch': (-40, 30), 'yaw': (-50, 50), 'roll': (-10, 10)},
        'front_leg': {'type': 'hinge', 'pitch': (-35, 25)},
        'hind_leg': {'type': 'hinge', 'pitch': (-40, 30)},
        'tail': {'type': 'pin', 'pitch': (-30, 80), 'yaw': (-40, 40), 'description': 'Rabo espiralado'},
    },
    'ave': {
        'head_neck': {'type': 'ball_socket', 'pitch': (-50, 30), 'yaw': (-60, 60), 'roll': (-30, 30)},
        'wing': {'type': 'hinge', 'pitch': (-20, 80), 'yaw': (-10, 10), 'description': 'Asa - batimento'},
        'leg': {'type': 'hinge', 'pitch': (-40, 20), 'description': 'Perna com articulação tipo cambota (reverse ankle)'},
        'tail': {'type': 'pin', 'pitch': (-10, 30)},
    },
    'ovino': {
        'head_neck': {'type': 'ball_socket', 'pitch': (-35, 40), 'yaw': (-45, 45), 'roll': (-15, 15)},
        'front_leg': {'type': 'hinge', 'pitch': (-45, 30)},
        'hind_leg': {'type': 'hinge', 'pitch': (-50, 35)},
        'tail': {'type': 'pin', 'pitch': (-15, 40), 'yaw': (-20, 20)},
    },
}

# ============================================================================
# GERADORES DE ANIMAIS (SÓLIDOS)
# ============================================================================

def gen_bovine(s):
    m = []
    # Corpo
    m.append(ellipsoid(2.0*s, 1.8*s, 3.5*s, 0, 2.5*s, 0, 16, 12))
    # Pescoço
    m.append(cylinder(0.9*s, 2.0*s, 0, 4.0*s, 0.5*s, 12))
    # Cabeça
    m.append(ellipsoid(1.0*s, 0.9*s, 1.5*s, 0, 5.2*s, 1.2*s, 12, 10))
    # Focinho
    m.append(ellipsoid(0.7*s, 0.6*s, 0.8*s, 0, 4.8*s, 2.2*s, 10, 8))
    # Chifres
    m.append(cone(0.2*s, 0.8*s, -0.5*s, 5.5*s, 1.0*s, 8))
    m.append(cone(0.2*s, 0.8*s, 0.5*s, 5.5*s, 1.0*s, 8))
    # Orelhas
    m.append(ellipsoid(0.3*s, 0.4*s, 0.5*s, -0.7*s, 5.3*s, 0.8*s, 8, 6))
    m.append(ellipsoid(0.3*s, 0.4*s, 0.5*s, 0.7*s, 5.3*s, 0.8*s, 8, 6))
    # Patas
    for lx, lz in [(-1.2*s, 2.0*s),(1.2*s, 2.0*s),(-1.2*s,-2.0*s),(1.2*s,-2.0*s)]:
        m.append(cylinder(0.4*s, 2.5*s, lx, 0.8*s, lz, 10))
        m.append(cylinder(0.45*s, 0.3*s, lx, 0.15*s, lz, 10))
    # Rabo
    m.append(cylinder(0.15*s, 2.0*s, 0, 3.0*s, -3.5*s, 8))
    m.append(ellipsoid(0.3*s, 0.3*s, 0.5*s, 0, 2.0*s, -4.2*s, 8, 6))
    # Úbere
    m.append(ellipsoid(0.8*s, 0.6*s, 1.0*s, 0, 0.8*s, -1.0*s, 10, 8))
    return m

def gen_equine(s):
    m = []
    m.append(ellipsoid(1.8*s, 1.6*s, 4.0*s, 0, 3.0*s, 0, 16, 12))
    m.append(cylinder(0.7*s, 2.5*s, 0, 4.5*s, 0.8*s, 12))
    m.append(ellipsoid(0.8*s, 0.7*s, 1.8*s, 0, 5.8*s, 1.5*s, 12, 10))
    m.append(ellipsoid(0.5*s, 0.5*s, 1.0*s, 0, 5.5*s, 2.5*s, 10, 8))
    # Orelhas pontudas
    m.append(cone(0.15*s, 0.5*s, -0.4*s, 6.2*s, 1.2*s, 8))
    m.append(cone(0.15*s, 0.5*s, 0.4*s, 6.2*s, 1.2*s, 8))
    # Patas longas
    for lx, lz in [(-1.0*s, 2.2*s),(1.0*s, 2.2*s),(-1.0*s,-2.2*s),(1.0*s,-2.2*s)]:
        m.append(cylinder(0.3*s, 3.0*s, lx, 0.8*s, lz, 10))
        m.append(cylinder(0.35*s, 0.25*s, lx, 0.15*s, lz, 10))
    # Rabo
    m.append(cylinder(0.12*s, 2.5*s, 0, 3.2*s, -3.8*s, 8))
    m.append(ellipsoid(0.4*s, 0.8*s, 0.3*s, 0, 1.5*s, -4.8*s, 8, 6))
    # Crina
    m.append(ellipsoid(0.3*s, 0.8*s, 1.5*s, 0.8*s, 4.5*s, 0.5*s, 8, 10))
    return m

def gen_porine(s):
    m = []
    m.append(ellipsoid(2.2*s, 1.5*s, 2.8*s, 0, 2.0*s, 0, 16, 12))
    m.append(ellipsoid(1.2*s, 1.0*s, 1.3*s, 0, 2.5*s, 1.8*s, 12, 10))
    m.append(cylinder(0.6*s, 0.5*s, 0, 2.3*s, 2.8*s, 12))
    m.append(ellipsoid(0.5*s, 0.3*s, 0.2*s, 0, 2.3*s, 3.1*s, 10, 8))
    # Orelhas
    m.append(ellipsoid(0.4*s, 0.5*s, 0.2*s, -0.7*s, 3.0*s, 1.2*s, 8, 6))
    m.append(ellipsoid(0.4*s, 0.5*s, 0.2*s, 0.7*s, 3.0*s, 1.2*s, 8, 6))
    # Patas curtas
    for lx, lz in [(-1.3*s, 1.5*s),(1.3*s, 1.5*s),(-1.3*s,-1.5*s),(1.3*s,-1.5*s)]:
        m.append(cylinder(0.35*s, 1.2*s, lx, 0.5*s, lz, 10))
        m.append(cylinder(0.4*s, 0.2*s, lx, 0.1*s, lz, 10))
    # Rabo
    m.append(cylinder(0.1*s, 0.8*s, 0, 2.5*s, -2.5*s, 8))
    return m

def gen_ave(s):
    m = []
    m.append(ellipsoid(1.5*s, 1.3*s, 2.0*s, 0, 2.0*s, 0, 16, 12))
    m.append(sphere(0.7*s, 0, 3.2*s, 0.5*s, 12, 10))
    m.append(cone(0.2*s, 0.5*s, 0, 3.5*s, 1.0*s, 8))
    # Crista
    m.append(ellipsoid(0.15*s, 0.4*s, 0.3*s, 0, 3.6*s, 0.3*s, 6, 4))
    m.append(ellipsoid(0.15*s, 0.35*s, 0.3*s, 0, 3.5*s, 0.6*s, 6, 4))
    # Barbela
    m.append(ellipsoid(0.2*s, 0.25*s, 0.15*s, 0, 3.0*s, 1.0*s, 6, 4))
    # Asas
    m.append(ellipsoid(0.3*s, 0.5*s, 0.8*s, -1.3*s, 2.0*s, 0.5*s, 8, 6))
    m.append(ellipsoid(0.3*s, 0.5*s, 0.8*s, 1.3*s, 2.0*s, 0.5*s, 8, 6))
    # Patas
    for lx in [-0.5*s, 0.5*s]:
        m.append(cylinder(0.15*s, 1.0*s, lx, 0.5*s, 0.5*s, 8))
        m.append(ellipsoid(0.3*s, 0.1*s, 0.4*s, lx, 0.05*s, 0.8*s, 6, 4))
    # Rabo
    m.append(ellipsoid(0.4*s, 0.3*s, 0.8*s, 0, 2.5*s, -1.8*s, 8, 6))
    return m

def gen_ovine(s):
    m = []
    m.append(ellipsoid(2.0*s, 1.8*s, 3.0*s, 0, 2.5*s, 0, 16, 12))
    # Lã
    for wx, wy, wz in [
        (-1.5*s, 3.0*s, 1.0*s),(1.5*s, 3.0*s, 1.0*s),
        (-1.5*s, 3.0*s, -1.0*s),(1.5*s, 3.0*s, -1.0*s),
        (0, 3.5*s, 2.0*s),(0, 3.5*s, -2.0*s),
        (-1.8*s, 2.5*s, 0),(1.8*s, 2.5*s, 0),(0, 3.2*s, 0),
    ]:
        m.append(sphere(0.6*s, wx, wy, wz, 10, 8))
    m.append(ellipsoid(0.8*s, 0.9*s, 1.2*s, 0, 2.8*s, 1.5*s, 12, 10))
    m.append(ellipsoid(0.5*s, 0.5*s, 0.6*s, 0, 2.5*s, 2.2*s, 10, 8))
    # Orelhas
    m.append(ellipsoid(0.25*s, 0.4*s, 0.15*s, -0.5*s, 2.9*s, 1.3*s, 8, 6))
    m.append(ellipsoid(0.25*s, 0.4*s, 0.15*s, 0.5*s, 2.9*s, 1.3*s, 8, 6))
    # Patas
    for lx, lz in [(-1.0*s, 1.5*s),(1.0*s, 1.5*s),(-1.0*s,-1.5*s),(1.0*s,-1.5*s)]:
        m.append(cylinder(0.25*s, 1.5*s, lx, 0.6*s, lz, 8))
        m.append(cylinder(0.3*s, 0.2*s, lx, 0.1*s, lz, 8))
    # Rabo
    m.append(ellipsoid(0.3*s, 0.3*s, 0.4*s, 0, 2.2*s, -2.5*s, 6, 4))
    return m

# ============================================================================
# GERADORES ARTICULADOS
# ============================================================================

def articulated_bovine(s, jd):
    """Bovino articulado com 8 peças e juntas reais."""
    parts = []
    biomech = BIOMECHANICS['bovino']

    # PEÇA 1: Tronco Principal
    trunk = []
    trunk.append(ellipsoid(2.0*s, 1.8*s, 3.5*s, 0, 2.5*s, 0, 16, 12))
    # Úbere
    trunk.append(ellipsoid(0.8*s, 0.6*s, 1.0*s, 0, 0.8*s, -1.0*s, 10, 8))
    # Soquete do pescoço
    neck_socket = ball_socket(0.5*s, 0.3*s, 10)
    trunk.extend(neck_socket)
    # Canal para rabo
    trunk.extend(cylinder(0.2*s, 0.5*s, 0, 2.5*s, -3.2*s, 8))
    parts.append(Part(
        name="01_tronco",
        description="Corpo principal + úbere",
        triangles=trunk,
        joints=[
            Joint("pescoço", "ball_socket", (0, 4.0*s, 0.5*s),
                  jd, jd*0.8, (True,True,True),
                  f"Pitch: {biomech['head_neck']['pitch'][0]}° a {biomech['head_neck']['pitch'][1]}° | Yaw: ±{biomech['head_neck']['yaw'][1]}°"),
            Joint("rabo", "pin", (0, 2.5*s, -3.2*s),
                  jd*0.6, jd*0.8, (True,False,False),
                  f"Pitch: {biomech['tail']['pitch'][0]}° a {biomech['tail']['pitch'][1]}°"),
        ] + [
            Joint(f"pata_{side}", "hinge", (lx, 1.8*s, lz),
                  jd*0.8, jd, (False,True,False),
                  f"Pitch: {biomech['front_leg' if lz > 0 else 'hind_leg']['pitch'][0]}° a {biomech['front_leg' if lz > 0 else 'hind_leg']['pitch'][1]}°")
            for side, (lx, lz) in [("fe", -1.2*s, 2.0*s),("fd", 1.2*s, 2.0*s),
                                   ("te", -1.2*s, -2.0*s),("td", 1.2*s, -2.0*s)]
        ]
    ))

    # PEÇA 2: Cabeça
    head = []
    head.append(ellipsoid(1.0*s, 0.9*s, 1.5*s, 0, 0*s, 0.7*s, 12, 10))
    head.append(ellipsoid(0.7*s, 0.6*s, 0.8*s, 0, -0.4*s, 1.7*s, 10, 8))
    head.append(cone(0.2*s, 0.8*s, -0.5*s, 0.3*s, 0.5*s, 8))
    head.append(cone(0.2*s, 0.8*s, 0.5*s, 0.3*s, 0.5*s, 8))
    head.append(ellipsoid(0.3*s, 0.4*s, 0.5*s, -0.7*s, 0.1*s, 0.3*s, 8, 6))
    head.append(ellipsoid(0.3*s, 0.4*s, 0.5*s, 0.7*s, 0.1*s, 0.3*s, 8, 6))
    # Bola de articulação
    head.extend(ball_joint(0.5*s, 10, 6))
    parts.append(Part(
        name="02_cabeca",
        description="Cabeça + chifres + orelhas",
        triangles=head,
        connect_to="01_tronco",
        joints=[Joint("pescoço", "ball_socket", (0, -0.5*s, 0),
                      jd, jd*0.8, (True,True,True),
                      "Bola: encaixa no tronco")],
        movement_range="Inclina (pastar/levantar), gira lateralmente"
    ))

    # PEÇAS 3-6: Patas
    leg_config = [
        ("03_pata_frente_esq", "Pata frontal esquerda", -1.2*s, 2.0*s, "front_leg"),
        ("04_pata_frente_dir", "Pata frontal direita", 1.2*s, 2.0*s, "front_leg"),
        ("05_pata_tras_esq", "Pata traseira esquerda", -1.2*s, -2.0*s, "hind_leg"),
        ("06_pata_tras_dir", "Pata traseira direita", 1.2*s, -2.0*s, "hind_leg"),
    ]
    for pname, pdesc, lx, lz, ltype in leg_config:
        leg = []
        # Articulação proximal (soquete)
        leg.extend(ball_socket(0.3*s, 0.2*s, 8))
        # Canela
        leg.append(cylinder(0.35*s, 1.5*s, 0, 0.7*s, 0, 10))
        # Articulação do joelho (pino)
        leg.extend(cylinder(0.15*s, 0.3*s, 0, 1.4*s, 0, 8))
        # Canela inferior
        leg.append(cylinder(0.3*s, 0.8*s, 0, 0.2*s, 0, 10))
        # Casco
        leg.append(cylinder(0.4*s, 0.25*s, 0, -0.2*s, 0, 10))
        parts.append(Part(
            name=pname,
            description=pdesc,
            triangles=leg,
            connect_to="01_tronco",
            joints=[Joint("articulacao", "hinge", (0, 1.8*s, 0),
                          jd*0.6, jd*0.5, (False,True,False),
                          biomech[ltype].get('description', 'Articulação da pata'))],
            movement_range=f"Flexão/Extensão: {biomech[ltype]['pitch'][0]}° a {biomech[ltype]['pitch'][1]}°"
        ))

    # PEÇA 7: Rabo
    tail = []
    tail.extend(cylinder(0.12*s, 2.0*s, 0, 0, 0, 8))
    tail.extend(ellipsoid(0.3*s, 0.3*s, 0.5*s, 0, -1.0*s, -0.2*s, 8, 6))
    # Pino de articulação
    tail.extend(cylinder(0.1*s, 0.4*s, 0, 0.3*s, 0, 8))
    parts.append(Part(
        name="07_rabo",
        description="Rabo com tufo",
        triangles=tail,
        connect_to="01_tronco",
        joints=[Joint("base", "pin", (0, 0.3*s, 0),
                      jd*0.4, jd*0.3, (True,False,False),
                      "Pino de articulação do rabo")],
        movement_range=f"Balanceio: pitch {biomech['tail']['pitch'][0]}°-{biomech['tail']['pitch'][1]}°, yaw ±{biomech['tail']['yaw'][1]}°"
    ))

    guide = """
═══ MONTAGEM - BOVINO ARTICULADO ═══
Peças: 7 (1 tronco + 1 cabeça + 4 patas + 1 rabo)

1. Imprima o TRONCO com 20% preenchimento (base estrutural)
2. Imprima as 4 PATAS com 30% preenchimento (suportam peso)
3. Imprima a CABEÇA e o RABO com 15% preenchimento

Montagem:
  - Encaixe a CABEÇA no soquete do pescoço (bola → soquete)
  - Insira as 4 PATAS nos canais laterais do tronco
  - Conecte o RABO na base posterior
  - Gire cada junta para verificar o movimento

Movimentos simulados:
  🐄 Cabeça: pastar (inclina para baixo ±45°), alerta (ergue ±30°)
  🐄 Patas: andar (flexão -45° a 30°), parado (extensão)
  🐄 Rabo: abate moscas (balance lateral ±30°)

Dica: Use PLA flexível para juntas ou deixe folga de 0.2mm
═════════════════════════════════════
"""
    return AnimalModel("bovino", "Bovino Articulado", [], parts, guide)

def articulated_equine(s, jd):
    """Equino articulado com 9 peças (inclui joelho)."""
    parts = []
    biomech = BIOMECHANICS['equine']

    # Tronco
    trunk = []
    trunk.append(ellipsoid(1.8*s, 1.6*s, 4.0*s, 0, 3.0*s, 0, 16, 12))
    trunk.extend(ball_socket(0.45*s, 0.3*s, 10))
    parts.append(Part(
        name="01_tronco",
        description="Corpo do equino",
        triangles=trunk,
        joints=[
            Joint("pescoço", "ball_socket", (0, 4.5*s, 0.8*s), jd, jd*0.8, (True,True,True), biomech['head_neck'].get('description','')),
            Joint("rabo", "pin", (0, 2.5*s, -3.8*s), jd*0.5, jd*0.6, (True,False,False), biomech['tail'].get('description','')),
        ] + [
            Joint(f"pata_{side}", "hinge", (lx, 1.5*s, lz), jd*0.7, jd*0.5, (False,True,False), biomech.get('front_leg' if lz > 0 else 'hind_leg',{}).get('description',''))
            for side, (lx, lz) in [("fe", -1.0*s, 2.2*s),("fd", 1.0*s, 2.2*s),
                                   ("te", -1.0*s, -2.2*s),("td", 1.0*s, -2.2*s)]
        ]
    ))

    # Cabeça
    head = []
    head.append(ellipsoid(0.8*s, 0.7*s, 1.8*s, 0, 0, 0.8*s, 12, 10))
    head.append(ellipsoid(0.5*s, 0.5*s, 1.0*s, 0, -0.3*s, 1.8*s, 10, 8))
    head.append(cone(0.15*s, 0.5*s, -0.4*s, 0.2*s, 0.6*s, 8))
    head.append(cone(0.15*s, 0.5*s, 0.4*s, 0.2*s, 0.6*s, 8))
    head.extend(ball_joint(0.45*s, 10, 6))
    parts.append(Part(name="02_cabeca", description="Cabeça + orelhas pontudas", triangles=head,
        connect_to="01_tronco", movement_range="Pastar (flexão), alerta (erguida), lateral"))

    # Patas com articulação de joelho (equino tem articulações visíveis)
    for idx, (pname, pdesc, lx, lz, ltype) in enumerate([
        ("03_pata_fe", "Pata frontal esquerda (com joelho)", -1.0*s, 2.2*s, "front_leg"),
        ("04_pata_fd", "Pata frontal direita (com joelho)", 1.0*s, 2.2*s, "front_leg"),
        ("05_pata_te", "Pata traseira esquerda (com jarrete)", -1.0*s, -2.2*s, "hind_leg"),
        ("06_pata_td", "Pata traseira direita (com jarrete)", 1.0*s, -2.2*s, "hind_leg"),
    ], start=3):
        leg = []
        # Fêmur (art. proximal)
        leg.extend(ball_socket(0.25*s, 0.2*s, 8))
        leg.append(cylinder(0.25*s, 1.0*s, 0, 0.6*s, 0, 10))
        # Joelho (articulação intermediária)
        leg.extend(cylinder(0.12*s, 0.25*s, 0, 1.1*s, 0, 8))
        # Canhão
        leg.append(cylinder(0.22*s, 0.8*s, 0, 0.3*s, 0, 10))
        # Cascudo + Casco
        leg.append(cylinder(0.2*s, 0.5*s, 0, -0.3*s, 0, 10))
        leg.append(cylinder(0.3*s, 0.2*s, 0, -0.6*s, 0, 10))
        parts.append(Part(name=pname, description=pdesc, triangles=leg,
            connect_to="01_tronco", movement_range=f"Flexão: {biomech[ltype]['pitch'][0]}° a {biomech[ltype]['pitch'][1]}°"))

    # Crina (separada para mobilidade)
    mane = [ellipsoid(0.3*s, 0.8*s, 1.5*s, 0.6*s, 0.2*s, 0.2*s, 8, 10)]
    parts.append(Part(name="07_crina", description="Crina (pequena, decorativa)", triangles=mane,
        connect_to="01_tronco", movement_range="Voa com vento"))

    # Rabo
    tail = [cylinder(0.1*s, 2.5*s, 0, 0, 0, 8)]
    tail.extend(ellipsoid(0.4*s, 0.8*s, 0.3*s, 0, -1.2*s, 0, 8, 6))
    tail.extend(cylinder(0.08*s, 0.3*s, 0, 0.3*s, 0, 8))
    parts.append(Part(name="08_rabo", description="Rabo longo", triangles=tail,
        connect_to="01_tronco", movement_range=f"Balanceio: ±{biomech['tail']['yaw'][1]}°"))

    guide = """
═══ MONTAGEM - EQUINO ARTICULADO ═══
Peças: 8 (1 tronco + 1 cabeça + 4 patas com joelho + 1 crina + 1 rabo)

Características biomecânicas:
  🐴 Equinos têm articulações de joelho visíveis
  🐴 O pescoço é longo e muito flexível
  🐴 O rabo é alongado e balança ao trotar
  🐴 As patas têm 3 articulações visíveis

Montagem:
  1. Tronco (20% fill) + Patas (30% fill)
  2. Cabeça no soquete do pescoço
  3. Crina e rabo como acabamento
  4. Testar flexão de cada pata

Dica: O equino pode ser posicionado em "trote" ou "parado"
═════════════════════════════════════
"""
    return AnimalModel("equino", "Equino Articulado", [], parts, guide)

def articulated_porine(s, jd):
    """Suíno articulado com 6 peças."""
    parts = []
    biomech = BIOMECHANICS['suino']

    # Tronco
    trunk = [ellipsoid(2.2*s, 1.5*s, 2.8*s, 0, 2.0*s, 0, 16, 12)]
    trunk.extend(ball_socket(0.5*s, 0.3*s, 10))
    trunk.extend(cylinder(0.1*s, 0.4*s, 0, 1.8*s, -2.2*s, 8))
    parts.append(Part(name="01_tronco", description="Corpo do porco", triangles=trunk,
        joints=[
            Joint("cabeca", "ball_socket", (0, 2.5*s, 1.5*s), jd, jd*0.7, (True,True,True), ""),
            Joint("rabo", "pin", (0, 1.8*s, -2.2*s), jd*0.3, jd*0.3, (True,False,False), ""),
        ] + [
            Joint(f"pata_{side}", "hinge", (lx, 1.0*s, lz), jd*0.6, jd*0.5, (False,True,False), "")
            for side, (lx, lz) in [("fe", -1.3*s, 1.5*s),("fd", 1.3*s, 1.5*s),
                                   ("te", -1.3*s, -1.5*s),("td", 1.3*s, -1.5*s)]
        ]
    ))

    # Cabeça
    head = []
    head.append(ellipsoid(1.2*s, 1.0*s, 1.3*s, 0, 0, 0.3*s, 12, 10))
    head.append(cylinder(0.6*s, 0.5*s, 0, -0.2*s, 1.3*s, 12))
    head.append(ellipsoid(0.5*s, 0.3*s, 0.2*s, 0, -0.2*s, 1.6*s, 10, 8))
    head.append(ellipsoid(0.4*s, 0.5*s, 0.2*s, -0.5*s, 0.2*s, 0.2*s, 8, 6))
    head.append(ellipsoid(0.4*s, 0.5*s, 0.2*s, 0.5*s, 0.2*s, 0.2*s, 8, 6))
    head.extend(ball_joint(0.5*s, 10, 6))
    parts.append(Part(name="02_cabeca", description="Cabeça + focinho + orelhas", triangles=head,
        connect_to="01_tronco", movement_range="Procura comida no solo (inclinação forte)"))

    # Patas curtas
    for pname, pdesc, lx, lz, ltype in [
        ("03_pata_fe", "Pata frontal esquerda", -1.3*s, 1.5*s, "front_leg"),
        ("04_pata_fd", "Pata frontal direita", 1.3*s, 1.5*s, "front_leg"),
        ("05_pata_te", "Pata traseira esquerda", -1.3*s, -1.5*s, "hind_leg"),
        ("06_pata_td", "Pata traseira direita", 1.3*s, -1.5*s, "hind_leg"),
    ]:
        leg = []
        leg.extend(ball_socket(0.25*s, 0.15*s, 8))
        leg.append(cylinder(0.3*s, 0.7*s, 0, 0.3*s, 0, 10))
        leg.append(cylinder(0.35*s, 0.15*s, 0, -0.1*s, 0, 10))
        parts.append(Part(name=pname, description=pdesc, triangles=leg,
            connect_to="01_tronco", movement_range=f"Flexão: {biomech[ltype]['pitch'][0]}° a {biomech[ltype]['pitch'][1]}°"))

    guide = """
═══ MONTAGEM - SUÍNO ARTICULADO ═══
Peças: 5 (1 tronco + 1 cabeça + 4 patas curtas)

Características:
  🐷 Focinho largo (procura comida)
  🐷 Rabo espiralado (sólido, decorativo)
  🐷 Patas curtas e robustas
  🐷 Cabeça muito móvel (busca no solo)

Montagem: cabeça → tronco, patas → tronco
═════════════════════════════════════
"""
    return AnimalModel("suino", "Suíno Articulado", [], parts, guide)

def articulated_ave(s, jd):
    """Ave (galinha) articulado com 7 peças."""
    parts = []
    biomech = BIOMECHANICS['ave']

    # Tronco
    trunk = [ellipsoid(1.5*s, 1.3*s, 2.0*s, 0, 2.0*s, 0, 16, 12)]
    trunk.extend(ball_socket(0.4*s, 0.25*s, 10))
    parts.append(Part(name="01_tronco", description="Corpo da galinha", triangles=trunk,
        joints=[
            Joint("cabeca", "ball_socket", (0, 3.0*s, 0.3*s), jd*0.7, jd*0.5, (True,True,True), ""),
            Joint("asa_esq", "hinge", (-1.1*s, 2.0*s, 0.3*s), jd*0.5, jd*0.4, (False,True,False), biomech['wing'].get('description','')),
            Joint("asa_dir", "hinge", (1.1*s, 2.0*s, 0.3*s), jd*0.5, jd*0.4, (False,True,False), biomech['wing'].get('description','')),
        ] + [
            Joint(f"pata_{side}", "hinge", (lx, 1.0*s, 0.3*s), jd*0.4, jd*0.3, (False,True,False), biomech['leg'].get('description',''))
            for side, lx in [("esq", -0.5*s), ("dir", 0.5*s)]
        ]
    ))

    # Cabeça
    head = []
    head.append(sphere(0.7*s, 0, 0, 0, 12, 10))
    head.append(cone(0.2*s, 0.5*s, 0, 0.2*s, 0.5*s, 8))
    head.append(ellipsoid(0.15*s, 0.4*s, 0.3*s, 0, 0.3*s, -0.1*s, 6, 4))
    head.append(ellipsoid(0.2*s, 0.25*s, 0.15*s, 0, -0.2*s, 0.3*s, 6, 4))
    head.extend(ball_joint(0.4*s, 10, 6))
    parts.append(Part(name="02_cabeca", description="Cabeça + bico + crista + barbela", triangles=head,
        connect_to="01_tronco", movement_range="Pesquisa sôlo (inclinada), alerta (erguida)"))

    # Asas
    for pname, pdesc, side in [
        ("03_asa_esquerda", "Asa esquerda", -1),
        ("04_asa_direita", "Asa direita", 1),
    ]:
        wing = []
        wing.extend(cylinder(0.08*s, 0.3*s, 0, 0, 0, 8))  # Pino
        wing.append(ellipsoid(0.3*s, 0.5*s, 0.8*s, 0, -0.3*s, 0.2*s, 8, 6))
        # Primárias
        wing.append(ellipsoid(0.1*s, 0.15*s, 0.6*s, 0, -0.6*s, 0.5*s, 6, 4))
        parts.append(Part(name=pname, description=pdesc, triangles=wing,
            connect_to="01_tronco",
            movement_range=f"Batimento: {biomech['wing']['pitch'][0]}° a {biomech['wing']['pitch'][1]}°"))

    # Patas
    for pname, pdesc, lx in [
        ("05_pata_esq", "Perna esquerda (cambota)", -0.5*s),
        ("06_pata_dir", "Perna direita (cambota)", 0.5*s),
    ]:
        leg = []
        leg.extend(cylinder(0.08*s, 0.3*s, 0, 0, 0, 8))
        leg.append(cylinder(0.12*s, 0.6*s, 0, -0.3*s, 0, 8))
        leg.append(ellipsoid(0.25*s, 0.08*s, 0.35*s, 0, -0.6*s, 0.15*s, 6, 4))
        parts.append(Part(name=pname, description=pdesc, triangles=leg,
            connect_to="01_tronco",
            movement_range="Passo curto, cambota (articulação inversa)"))

    # Rabo
    tail = [ellipsoid(0.4*s, 0.3*s, 0.8*s, 0, 0, -0.4*s, 8, 6)]
    parts.append(Part(name="07_rabo", description="Penas do rabo", triangles=tail,
        connect_to="01_tronco", movement_range="Estático, equilíbrio"))

    guide = """
═══ MONTAGEM - AVE (GALINHA) ARTICULADA ═══
Peças: 7 (1 tronco + 1 cabeça + 2 asas + 2 pernas + 1 rabo)

Características:
  🐔 Asas articuladas (batimento limitado)
  🐔 Pernas com cambota (articulação invertida)
  🐔 Cabeça muito móvel (pesquisa no solo)
  🐔 Crista e barbela na cabeça

Poses possíveis:
  • Empoleirada (pernas recolhidas, asas junto)
  • Empoleirada (asas abertas, cabeça alerta)
  • Empoleirada (pescoço esticado, patas abertas)

═════════════════════════════════════
"""
    return AnimalModel("ave", "Ave (Galinha) Articulado", [], parts, guide)

def articulated_ovine(s, jd):
    """Ovino (ovelha) articulado com 7 peças."""
    parts = []
    biomech = BIOMECHANICS['ovine']

    # Tronco com lã
    trunk = [ellipsoid(2.0*s, 1.8*s, 3.0*s, 0, 2.5*s, 0, 16, 12)]
    for wx, wy, wz in [
        (-1.5*s, 3.0*s, 1.0*s),(1.5*s, 3.0*s, 1.0*s),
        (-1.5*s, 3.0*s, -1.0*s),(1.5*s, 3.0*s, -1.0*s),
        (0, 3.5*s, 2.0*s),(0, 3.5*s, -2.0*s),
        (-1.8*s, 2.5*s, 0),(1.8*s, 2.5*s, 0),(0, 3.2*s, 0),
    ]:
        trunk.append(sphere(0.6*s, wx, wy, wz, 10, 8))
    trunk.extend(ball_socket(0.4*s, 0.25*s, 10))
    trunk.extend(cylinder(0.15*s, 0.4*s, 0, 2.0*s, -2.2*s, 8))
    parts.append(Part(name="01_tronco", description="Corpo com lã", triangles=trunk,
        joints=[
            Joint("cabeca", "ball_socket", (0, 2.8*s, 1.2*s), jd*0.7, jd*0.5, (True,True,True), ""),
            Joint("rabo", "pin", (0, 2.0*s, -2.2*s), jd*0.3, jd*0.3, (True,False,False), ""),
        ] + [
            Joint(f"pata_{side}", "hinge", (lx, 1.1*s, lz), jd*0.5, jd*0.4, (False,True,False), "")
            for side, (lx, lz) in [("fe", -1.0*s, 1.5*s),("fd", 1.0*s, 1.5*s),
                                   ("te", -1.0*s, -1.5*s),("td", 1.0*s, -1.5*s)]
        ]
    ))

    # Cabeça
    head = []
    head.append(ellipsoid(0.8*s, 0.9*s, 1.2*s, 0, 0, 0.3*s, 12, 10))
    head.append(ellipsoid(0.5*s, 0.5*s, 0.6*s, 0, -0.3*s, 1.0*s, 10, 8))
    head.append(ellipsoid(0.25*s, 0.4*s, 0.15*s, -0.4*s, 0.1*s, 0.2*s, 8, 6))
    head.append(ellipsoid(0.25*s, 0.4*s, 0.15*s, 0.4*s, 0.1*s, 0.2*s, 8, 6))
    head.extend(ball_joint(0.4*s, 10, 6))
    parts.append(Part(name="02_cabeca", description="Cabeça + orelhas caídas", triangles=head,
        connect_to="01_tronco", movement_range="Pastar (inclina), alerta (erguida)"))

    # Patas
    for pname, pdesc, lx, lz, ltype in [
        ("03_pata_fe", "Pata frontal esquerda", -1.0*s, 1.5*s, "front_leg"),
        ("04_pata_fd", "Pata frontal direita", 1.0*s, 1.5*s, "front_leg"),
        ("05_pata_te", "Pata traseira esquerda", -1.0*s, -1.5*s, "hind_leg"),
        ("06_pata_td", "Pata traseira direita", 1.0*s, -1.5*s, "hind_leg"),
    ]:
        leg = []
        leg.extend(ball_socket(0.2*s, 0.15*s, 8))
        leg.append(cylinder(0.22*s, 0.8*s, 0, 0.4*s, 0, 8))
        leg.append(cylinder(0.25*s, 0.15*s, 0, -0.05*s, 0, 8))
        parts.append(Part(name=pname, description=pdesc, triangles=leg,
            connect_to="01_tronco", movement_range=f"Flexão: {biomech[ltype]['pitch'][0]}° a {biomech[ltype]['pitch'][1]}°"))

    # Rabo
    tail = [ellipsoid(0.3*s, 0.3*s, 0.4*s, 0, 0, 0, 6, 4)]
    tail.extend(cylinder(0.08*s, 0.2*s, 0, 0.1*s, 0, 8))
    parts.append(Part(name="07_rabo", description="Rabo curto", triangles=tail,
        connect_to="01_tronco", movement_range="Balanceio leve"))

    guide = """
═══ MONTAGEM - OVINO (ovelha) ARTICULADO ═══
Peças: 7 (1 tronco + 1 cabeça + 4 patas + 1 rabo)

Características:
  🐑 Corpo coberto de "lã" (tufos esféricos)
  🐑 Orelhas caídas
  🐑 Patas finas
  🐑 Rabo curto

═════════════════════════════════════
"""
    return AnimalModel("ovino", "Ovino Articulado", [], parts, guide)

# ============================================================================
# INTERFAÇÃO E EXECUÇÃO
# ============================================================================

SOLID_GENERATORS = {
    'bovino': ('Bovino (Vaca/Touro)', gen_bovine, 8.0),
    'equino': ('Equino (Cavalo)', gen_equine, 8.0),
    'suino':  ('Suíno (Porco)', gen_porine, 10.0),
    'ave':    ('Ave (Galinha)', gen_ave, 12.0),
    'ovino':  ('Ovino (Ovelha)', gen_ovine, 9.0),
}

ARTICULATED_GENERATORS = {
    'bovino': ('Bovino Articulado', articulated_bovine),
    'equino': ('Equino Articulado', articulated_equine),
    'suino':  ('Suíno Articulado', articulated_porine),
    'ave':    ('Ave Articulado', articulated_ave),
    'ovino':  ('Ovino Articulado', articulated_ovine),
}

SPECIES_LABELS = {
    'bovino': '🐄 BOVINO',
    'equino': '🐴 EQUINO',
    'suino':  '🐷 SUÍNO',
    'ave':    '🐔 AVE',
    'ovino':  '🐑 OVINO',
}

def print_header():
    print("\n" + "=" * 64)
    print("  GERADOR DE ANIMAIS DE FAZENDA 3D PARA IMPRESSÃO")
    print("  v2.0 — Modelos Sólidos e Articulado")
    print("=" * 64)
    print("\nEspécies disponíveis:")
    for k, v in SPECIES_LABELS.items():
        print(f"  {v:25s} ({k})")
    print("\nTipos de modelo:")
    print("  🧱 Sólido        — Peça única, sem montagem")
    print("  🧩 Articulado    — Múltiplas peças com juntas móveis")
    print("-" * 64)

def generate_solid(animal_key, scale, output_dir):
    """Gera modelo sólido (uma peça)."""
    label, gen, default_scale = SOLID_GENERATORS[animal_key]
    s = scale if scale else default_scale
    tris = gen(s)
    fname = f"{animal_key}_solida_{int(s*10)}mm.stl"
    fpath = os.path.join(output_dir, fname)
    write_stl(tris, fpath)
    return fname, len(tris)

def generate_articulated(animal_key, scale, joint_diameter, output_dir):
    """Gera modelo articulado (múltiplas peças)."""
    label, gen = ARTICULATED_GENERATORS[animal_key]
    s = scale if scale else 8.0
    jd = joint_diameter
    model = gen(s, jd)

    piece_dir = os.path.join(output_dir, f"{animal_key}_articulado")
    os.makedirs(piece_dir, exist_ok=True)

    files = []
    for part in model.parts:
        fname = f"{part.name}.stl"
        fpath = os.path.join(piece_dir, fname)
        write_stl(part.triangles, fpath)
        files.append((fname, len(part.triangles)))

    # Guia de montagem
    guide_path = os.path.join(piece_dir, "00_GUIA_MONTAGEM.txt")
    with open(guide_path, 'w', encoding='utf-8') as f:
        f.write(model.assembly_guide)
        f.write("\n\n═══ DETALHES DAS PEÇAS ═══\n")
        for p in model.parts:
            f.write(f"\n📦 {p.name}: {p.description}\n")
            f.write(f"   Triângulos: {len(p.triangles)}\n")
            if p.connect_to:
                f.write(f"   Conecta em: {p.connect_to}\n")
            if p.movement_range:
                f.write(f"   Movimento: {p.movement_range}\n")
            if p.joints:
                for j in p.joints:
                    f.write(f"   • Junta '{j.name}' ({j.type}): {j.description}\n")
        f.write("\n═════════════════════════════════════\n")

    return piece_dir, files

def main():
    parser = argparse.ArgumentParser(
        description='Gerador de Animais de Fazenda 3D para Impressão',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python gerador_animais_fazenda_3d.py --all
  python gerador_animais_fazenda_3d.py --animal bovino --scale 12
  python gerador_animais_fazenda_3d.py --all --articulated --scale 8 --joint-diameter 3
  python gerador_animais_fazenda_3d.py --animal equino --articulated --scale 10
        """
    )
    parser.add_argument('--all', action='store_true', help='Gera todas as espécies')
    parser.add_argument('--animal', type=str, choices=['bovino','equino','suino','ave','ovino'],
                        help='Espécie específica')
    parser.add_argument('--scale', type=float, default=None, help='Escala em mm (padrão por espécie)')
    parser.add_argument('--articulated', action='store_true', help='Modo articulado (múltiplas peças)')
    parser.add_argument('--joint-diameter', type=float, default=3.0, help='Diâmetro das juntas em mm (padrão: 3mm)')
    parser.add_argument('--output', type=str, default=None, help='Diretório de saída')

    args = parser.parse_args()

    if not args.all and not args.animal:
        print_header()
        print("\n⚠️  Use --all para gerar todas as espécies ou --animal <nome> para uma específica.")
        print("\nModo interativo — selecione uma opção:\n")
        options = ['1','2','3','4','5','6','7','8']
        print("  [1] Bovino - Sólido")
        print("  [2] Equino - Sólido")
        print("  [3] Suíno  - Sólido")
        print("  [4] Ave    - Sólido")
        print("  [5] Ovino  - Sólido")
        print("  [6] Bovino - Articulado")
        print("  [7] Todas  - Articulado")
        print("  [8] Todas  - Sólido")
        print()
        choice = input("Opção [1-8]: ").strip()

        solid_map = {'1': 'bovino', '2': 'equino', '3': 'suino', '4': 'ave', '5': 'ovino'}
        if choice in solid_map:
            args.animal = solid_map[choice]
            args.articulated = False
        elif choice == '6':
            args.animal = 'bovino'
            args.articulated = True
        elif choice == '7':
            args.all = True
            args.articulated = True
        elif choice == '8':
            args.all = True
            args.articulated = False
        else:
            print("Opção inválida. Gerando bovino sólido.")
            args.animal = 'bovino'

    print_header()

    output_dir = args.output or os.path.join(os.path.dirname(os.path.abspath(__file__)), "animais_3d")
    os.makedirs(output_dir, exist_ok=True)

    animals = list(SOLID_GENERATORS.keys()) if args.all else [args.animal]
    scale = args.scale
    articulated = args.articulated
    jd = args.joint_diameter

    print(f"\n📁 Saída: {output_dir}")
    print(f"📐 Escala: {scale if scale else '(padrão por espécie)'}")
    print(f"🧩 Modo: {'ARTICULADO' if articulated else 'Sólido'}")
    if articulated:
        print(f"🔩 Diâmetro das juntas: {jd}mm")
    print()

    for akey in animals:
        label = SPECIES_LABELS[akey]
        print(f"▶ Gerando {label}...")

        if articulated:
            pdir, files = generate_articulated(akey, scale, jd, output_dir)
            for fname, ntris in files:
                print(f"    📦 {fname:35s} {ntris:6d} triângulos")
            print(f"    📋 Guia de montagem em: {pdir}/00_GUIA_MONTAGEM.txt")
        else:
            fname, ntris = generate_solid(akey, scale, output_dir)
            print(f"    📦 {fname:35s} {ntris:6d} triângulos")

        print()

    print("=" * 64)
    print("  ✅ CONCLUÍDO!")
    print(f"  📁 Arquivos em: {output_dir}")
    print("=" * 64)
    print("\n  DICAS PARA IMPRESSÃO:")
    print("  • Material: PLA ou PETG")
    print("  • Preenchimento: 15-20% (sólido) / 30% (peças estruturais)")
    print("  • Camada: 0.2mm")
    print("  • Sem suportes (projetado para impressão plana)")
    print("  • Para articulados: teste folga com 1 peça antes de imprimir tudo")
    print("=" * 64)

if __name__ == '__main__':
    main()