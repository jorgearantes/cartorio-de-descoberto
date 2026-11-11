"""
Escritório (projeto Virgínia Cyrne) — maquete 3D procedural para Blender 5.x.

Reconstruído a partir das imagens da apresentação (139-ARQ-APRESENTAÇÃO ESCRITÓRIO).
Gera o tour em vídeo com abertura de portas/gavetas, stills e uma panorâmica 360°.

Uso (bpy como módulo Python):
  python escritorio.py --mode anim  --start 1 --end 1460 --out frames/
  python escritorio.py --mode still --out stills/
  python escritorio.py --mode pano  --out pano/
  python escritorio.py --mode blend --out escritorio.blend

Sistema de coordenadas (metros):
  x: 0 = parede da porta de entrada  ->  L = parede da janela/armário
  y: 0 = parede das bancadas          ->  W = parede do aparador
  z: 0 = piso                         ->  H = forro
"""
import argparse
import math
import os
import random
import sys

import bpy
import bmesh
from mathutils import Vector

L, W, H = 3.6, 2.9, 2.6
FPS = 24
rng = random.Random(7)


# ----------------------------------------------------------------------------
# utilidades
# ----------------------------------------------------------------------------
def srgb(hexstr, a=1.0):
    h = hexstr.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [(x / 12.92) if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return (lin[0], lin[1], lin[2], a)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def coll():
    return bpy.context.scene.collection


def principled(mat):
    nt = mat.node_tree
    for n in nt.nodes:
        if n.bl_idname == 'ShaderNodeBsdfPrincipled':
            return n
    raise RuntimeError('no principled')


def mat_basic(name, color, rough=0.5, metal=0.0, emit=None, estr=0.0, coat=0.0, spec=0.5):
    m = bpy.data.materials.new(name)
    b = principled(m)
    b.inputs['Base Color'].default_value = color
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    b.inputs['Specular IOR Level'].default_value = spec
    if coat:
        b.inputs['Coat Weight'].default_value = coat
    if emit:
        b.inputs['Emission Color'].default_value = emit
        b.inputs['Emission Strength'].default_value = estr
    return m


def mat_emit(name, color, strength):
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.bl_idname == 'ShaderNodeBsdfPrincipled':
            nt.nodes.remove(n)
    out = [n for n in nt.nodes if n.bl_idname == 'ShaderNodeOutputMaterial'][0]
    e = nt.nodes.new('ShaderNodeEmission')
    e.inputs['Color'].default_value = color
    e.inputs['Strength'].default_value = strength
    nt.links.new(e.outputs[0], out.inputs['Surface'])
    return m


def mat_wood(name, dark, light, rough=0.45, direction='X', mscale=(7, 7, 0.35),
             wscale=2.2, distortion=9.0, bump=0.06, planks=False, coat=0.0):
    """Madeira procedural (veio via Wave distorcido + variação por objeto)."""
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    N, Lk = nt.nodes, nt.links
    b = principled(m)
    b.inputs['Roughness'].default_value = rough
    if coat:
        b.inputs['Coat Weight'].default_value = coat
        b.inputs['Coat Roughness'].default_value = 0.15
    tc = N.new('ShaderNodeTexCoord')
    oi = N.new('ShaderNodeObjectInfo')
    off = N.new('ShaderNodeVectorMath'); off.operation = 'MULTIPLY_ADD'
    off.inputs[1].default_value = (1, 1, 1)
    sc = N.new('ShaderNodeVectorMath'); sc.operation = 'SCALE'
    sc.inputs['Scale'].default_value = 13.7
    Lk.new(oi.outputs['Random'], sc.inputs[0])
    Lk.new(tc.outputs['Object'], off.inputs[0])
    Lk.new(sc.outputs[0], off.inputs[2])
    mp = N.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = mscale
    Lk.new(off.outputs[0], mp.inputs['Vector'])
    wv = N.new('ShaderNodeTexWave')
    wv.wave_type = 'BANDS'
    wv.bands_direction = direction
    wv.inputs['Scale'].default_value = wscale
    wv.inputs['Distortion'].default_value = distortion
    wv.inputs['Detail'].default_value = 4.0
    wv.inputs['Detail Scale'].default_value = 1.2
    Lk.new(mp.outputs[0], wv.inputs['Vector'])
    nz = N.new('ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = 3.0
    nz.inputs['Detail'].default_value = 6.0
    Lk.new(mp.outputs[0], nz.inputs['Vector'])
    mix = N.new('ShaderNodeMix'); mix.data_type = 'FLOAT'
    mix.inputs['Factor'].default_value = 0.35
    Lk.new(wv.outputs['Fac'], mix.inputs['A'])
    Lk.new(nz.outputs['Fac'], mix.inputs['B'])
    cr = N.new('ShaderNodeValToRGB')
    cr.color_ramp.elements[0].position = 0.25
    cr.color_ramp.elements[0].color = dark
    cr.color_ramp.elements[1].position = 0.85
    cr.color_ramp.elements[1].color = light
    Lk.new(mix.outputs['Result'], cr.inputs['Fac'])
    # variação de tom por objeto/tábua
    hsv = N.new('ShaderNodeHueSaturation')
    vmap = N.new('ShaderNodeMapRange')
    vmap.inputs['To Min'].default_value = 0.88
    vmap.inputs['To Max'].default_value = 1.12
    Lk.new(oi.outputs['Random'], vmap.inputs['Value'])
    Lk.new(vmap.outputs['Result'], hsv.inputs['Value'])
    Lk.new(cr.outputs['Color'], hsv.inputs['Color'])
    color_out = hsv.outputs['Color']
    if planks:
        br = N.new('ShaderNodeTexBrick')
        br.offset = 0.5
        br.inputs['Scale'].default_value = 1.0
        br.inputs['Mortar Size'].default_value = 0.0012
        br.inputs['Brick Width'].default_value = 1.35
        br.inputs['Row Height'].default_value = 0.19
        br.inputs['Bias'].default_value = 0.0
        br.inputs['Color1'].default_value = (1.0, 1.0, 1.0, 1)
        br.inputs['Color2'].default_value = (0.78, 0.74, 0.70, 1)
        br.inputs['Mortar'].default_value = (0.12, 0.06, 0.03, 1)
        Lk.new(tc.outputs['Object'], br.inputs['Vector'])
        mul = N.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'
        mul.inputs['Factor'].default_value = 1.0
        Lk.new(color_out, mul.inputs['A'])
        Lk.new(br.outputs['Color'], mul.inputs['B'])
        color_out = mul.outputs['Result']
        bm = N.new('ShaderNodeBump')
        bm.inputs['Strength'].default_value = 0.4
        bm.inputs['Distance'].default_value = 0.002
        Lk.new(br.outputs['Fac'], bm.inputs['Height'])
        Lk.new(bm.outputs['Normal'], b.inputs['Normal'])
    else:
        bm = N.new('ShaderNodeBump')
        bm.inputs['Strength'].default_value = bump
        Lk.new(wv.outputs['Fac'], bm.inputs['Height'])
        Lk.new(bm.outputs['Normal'], b.inputs['Normal'])
    Lk.new(color_out, b.inputs['Base Color'])
    return m


def mat_leather(name, color):
    m = mat_basic(name, color, rough=0.55)
    nt = m.node_tree
    b = principled(m)
    nz = nt.nodes.new('ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = 180.0
    nz.inputs['Detail'].default_value = 4.0
    vz = nt.nodes.new('ShaderNodeTexVoronoi')
    vz.inputs['Scale'].default_value = 25.0
    bm = nt.nodes.new('ShaderNodeBump')
    bm.inputs['Strength'].default_value = 0.25
    nt.links.new(nz.outputs['Fac'], bm.inputs['Height'])
    nt.links.new(bm.outputs['Normal'], b.inputs['Normal'])
    # manchas de couro envelhecido
    cr = nt.nodes.new('ShaderNodeValToRGB')
    cr.color_ramp.elements[0].color = tuple(c * 0.7 for c in color[:3]) + (1,)
    cr.color_ramp.elements[1].color = tuple(min(1, c * 1.35) for c in color[:3]) + (1,)
    nt.links.new(vz.outputs['Distance'], cr.inputs['Fac'])
    nt.links.new(cr.outputs['Color'], b.inputs['Base Color'])
    return m


def mat_blind(name):
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.bl_idname == 'ShaderNodeBsdfPrincipled':
            nt.nodes.remove(n)
    out = [n for n in nt.nodes if n.bl_idname == 'ShaderNodeOutputMaterial'][0]
    d = nt.nodes.new('ShaderNodeBsdfDiffuse')
    d.inputs['Color'].default_value = (0.85, 0.83, 0.80, 1)
    t = nt.nodes.new('ShaderNodeBsdfTranslucent')
    t.inputs['Color'].default_value = (0.95, 0.92, 0.86, 1)
    mx = nt.nodes.new('ShaderNodeMixShader')
    mx.inputs['Fac'].default_value = 0.45
    nt.links.new(d.outputs[0], mx.inputs[1])
    nt.links.new(t.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs['Surface'])
    return m


def world_loc(ob):
    v = Vector(ob.location)
    p = ob.parent
    while p is not None:
        v += p.location
        p = p.parent
    return v


def _link(ob, parent):
    coll().objects.link(ob)
    if parent is not None:
        ob.parent = parent


def box(name, x0, x1, y0, y1, z0, z1, mat, pivot=None, bevel=0.0, seg=2, parent=None):
    if pivot is None:
        pivot = ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)
    pivot = Vector(pivot)
    c = Vector(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)) - pivot
    d = (abs(x1 - x0), abs(y1 - y0), abs(z1 - z0))
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x = c.x + v.co.x * d[0]
        v.co.y = c.y + v.co.y * d[1]
        v.co.z = c.z + v.co.z * d[2]
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    _link(ob, parent)
    ob.location = pivot - (world_loc(parent) if parent else Vector())
    if mat:
        ob.data.materials.append(mat)
    if bevel > 0:
        md = ob.modifiers.new('bev', 'BEVEL')
        md.width = bevel
        md.segments = seg
        md.limit_method = 'ANGLE'
        md.harden_normals = False
        for p in ob.data.polygons:
            p.use_smooth = seg > 1
    return ob


def multibox(name, boxes, mat, parent=None):
    """Várias caixas num único mesh (barato p/ render)."""
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    for (x0, x1, y0, y1, z0, z1) in boxes:
        r = bmesh.ops.create_cube(bm, size=1.0)
        for v in r['verts']:
            v.co.x = (x0 + x1) / 2 + v.co.x * abs(x1 - x0)
            v.co.y = (y0 + y1) / 2 + v.co.y * abs(y1 - y0)
            v.co.z = (z0 + z1) / 2 + v.co.z * abs(z1 - z0)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    _link(ob, parent)
    if parent is not None:
        ob.location = -world_loc(parent)
    ob.data.materials.append(mat)
    return ob


def cyl(name, x, y, z0, z1, r, mat, verts=24, parent=None, rot=None):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=verts, radius1=r, radius2=r, depth=(z1 - z0))
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    _link(ob, parent)
    ob.location = Vector((x, y, (z0 + z1) / 2)) - (world_loc(parent) if parent else Vector())
    if rot:
        ob.rotation_euler = rot
    ob.data.materials.append(mat)
    return ob


def sphere(name, x, y, z, r, mat, parent=None, seg=24):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=r)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    _link(ob, parent)
    ob.location = Vector((x, y, z)) - (world_loc(parent) if parent else Vector())
    ob.data.materials.append(mat)
    return ob


def empty(name, loc, parent=None):
    ob = bpy.data.objects.new(name, None)
    _link(ob, parent)
    ob.location = Vector(loc) - (world_loc(parent) if parent else Vector())
    return ob


def area_light(name, loc, rot, sx, sy, energy, color, parent=None):
    ld = bpy.data.lights.new(name, 'AREA')
    ld.shape = 'RECTANGLE'
    ld.size = sx
    ld.size_y = sy
    ld.energy = energy
    ld.color = color[:3]
    ob = bpy.data.objects.new(name, ld)
    _link(ob, parent)
    ob.location = Vector(loc) - (world_loc(parent) if parent else Vector())
    ob.rotation_euler = rot
    ob.visible_camera = False
    return ob


def spot_light(name, loc, energy, color, size_deg=110, blend=0.6, radius=0.03):
    ld = bpy.data.lights.new(name, 'SPOT')
    ld.energy = energy
    ld.color = color[:3]
    ld.spot_size = math.radians(size_deg)
    ld.spot_blend = blend
    ld.shadow_soft_size = radius
    ob = bpy.data.objects.new(name, ld)
    coll().objects.link(ob)
    ob.location = loc
    ob.visible_camera = False
    return ob


def point_light(name, loc, energy, color, radius=0.05):
    ld = bpy.data.lights.new(name, 'POINT')
    ld.energy = energy
    ld.color = color[:3]
    ld.shadow_soft_size = radius
    ob = bpy.data.objects.new(name, ld)
    coll().objects.link(ob)
    ob.location = loc
    ob.visible_camera = False
    return ob


def key(ob, path, frame, value):
    setattr(ob, path, value) if not isinstance(value, (list, tuple)) else None
    if isinstance(value, (list, tuple)):
        getattr(ob, path)[:] = value
    ob.keyframe_insert(data_path=path, frame=frame)


def key_rotz(ob, frame, deg):
    ob.rotation_euler[2] = math.radians(deg)
    ob.keyframe_insert(data_path='rotation_euler', index=2, frame=frame)


def key_loc(ob, frame, loc):
    ob.location = loc
    ob.keyframe_insert(data_path='location', frame=frame)


def key_energy(lob, frame, e):
    lob.data.energy = e
    lob.data.keyframe_insert(data_path='energy', frame=frame)


# ----------------------------------------------------------------------------
# materiais
# ----------------------------------------------------------------------------
M = {}


def build_materials():
    M['wall'] = mat_basic('Parede', srgb('#cfc3b5'), rough=0.9, spec=0.3)
    M['ceiling'] = mat_basic('Forro', srgb('#e2dbd1'), rough=0.9, spec=0.3)
    M['corr'] = mat_basic('Corredor', srgb('#d8d2c8'), rough=0.9, spec=0.3)
    M['white'] = mat_basic('Branco laca', srgb('#eeebe6'), rough=0.35)
    M['navy'] = mat_basic('Laca azul grafite', srgb('#39414d'), rough=0.55, spec=0.4)
    M['navy_top'] = mat_basic('Tampo grafite', srgb('#2f353e'), rough=0.5, spec=0.4)
    M['graphite'] = mat_basic('Grafite armario', srgb('#3a3d43'), rough=0.6, spec=0.4)
    M['groove'] = mat_basic('Frisos', srgb('#141619'), rough=0.8)
    M['inside'] = mat_basic('Interno MDF', srgb('#d9d2c6'), rough=0.6)
    M['cream'] = mat_basic('Laca off-white', srgb('#e6ddcb'), rough=0.35, spec=0.45)
    M['black'] = mat_basic('Preto fosco', srgb('#121314'), rough=0.45)
    M['screen'] = mat_basic('Tela', srgb('#0b0c0e'), rough=0.12, spec=0.6)
    M['chrome'] = mat_basic('Cromado', srgb('#d8d8d8'), rough=0.12, metal=1.0)
    M['inox'] = mat_basic('Inox escovado', srgb('#9a9a9a'), rough=0.3, metal=1.0)
    M['leather'] = mat_leather('Couro caramelo', srgb('#6a381f'))
    M['plastic_w'] = mat_basic('Plastico branco', srgb('#e8e8e4'), rough=0.4)
    M['plastic_g'] = mat_basic('Plastico cinza', srgb('#5a5d61'), rough=0.4)
    M['slat_back'] = mat_basic('Fundo ripado', srgb('#1d140e'), rough=0.9)
    M['oak'] = mat_wood('Carvalho ripado', srgb('#8f5726'), srgb('#b9823f'), rough=0.5,
                        mscale=(9, 9, 0.3), wscale=2.5, distortion=4.0, bump=0.01)
    M['floor'] = mat_wood('Piso vinilico', srgb('#8a5530'), srgb('#a96e3f'), rough=0.32,
                          direction='Y', mscale=(0.2, 2.5, 2.5), wscale=3.0, distortion=5.0, planks=True, coat=0.15)
    M['led'] = mat_emit('LED 2700K', (1.0, 0.74, 0.42, 1), 12.0)
    M['led_cool'] = mat_emit('LED 3000K', (1.0, 0.75, 0.48, 1), 22.0)
    M['sky'] = mat_emit('Exterior', (0.82, 0.90, 1.0, 1), 1.6)
    M['blind'] = mat_blind('Persiana')
    M['frame_art'] = mat_wood('Moldura', srgb('#6a3b1c'), srgb('#9a6034'), rough=0.5)
    M['art'] = mat_basic('Quadro', srgb('#8a8f7c'), rough=0.7)
    M['ceramic'] = mat_basic('Ceramica preta', srgb('#2a2a2a'), rough=0.8)
    M['vase'] = mat_basic('Vaso bege', srgb('#cfc6a8'), rough=0.6)
    M['paper'] = mat_basic('Papel', srgb('#f2f0ea'), rough=0.8)
    M['globe'] = mat_basic('Globo', srgb('#4b4f53'), rough=0.25, metal=0.6)
    M['brass'] = mat_basic('Latao', srgb('#b8862f'), rough=0.3, metal=1.0)
    M['box_kraft'] = mat_basic('Caixa arquivo', srgb('#b89a72'), rough=0.8)
    M['binder'] = mat_basic('Pasta AZ', srgb('#2d3a52'), rough=0.6)
    books = ['#ece7da', '#f4f1ea', '#d9cdb4', '#c2a77e', '#2f4a3a', '#25352c', '#1a1a1a',
             '#5b4636', '#b9b1a1', '#e1d6bf', '#3e5a4a', '#a8916b']
    M['books'] = [mat_basic('Livro%d' % i, srgb(c), rough=0.7) for i, c in enumerate(books)]


# ----------------------------------------------------------------------------
# arquitetura
# ----------------------------------------------------------------------------
DOOR_Y0, DOOR_Y1, DOOR_H = 1.1, 1.9, 2.1
WIN_Y0, WIN_Y1, WIN_Z0, WIN_Z1 = 1.95, 2.78, 1.0, 2.3
T = 0.15  # espessura de parede


def build_architecture():
    # piso (sala + corredor)
    box('Piso', -2.6, L, -0.15, W + 0.15, -0.05, 0.0, M['floor'])
    box('Forro', -2.6, L + T, -T, W + T, H, H + 0.1, M['ceiling'])
    # parede das bancadas (y=0) e do aparador (y=W)
    box('Parede bancadas', -T, L + T, -T, 0, 0, H, M['wall'])
    box('Parede aparador', -T, L + T, W, W + T, 0, H, M['wall'])
    # parede da porta (x=0) com vão
    box('Parede porta A', -T, 0, 0, DOOR_Y0, 0, H, M['wall'])
    box('Parede porta B', -T, 0, DOOR_Y1, W, 0, H, M['wall'])
    box('Parede porta C', -T, 0, DOOR_Y0, DOOR_Y1, DOOR_H, H, M['wall'])
    # parede do fundo (x=L) com janela
    box('Parede fundo A', L, L + T, 0, WIN_Y0, 0, H, M['wall'])
    box('Parede fundo B', L, L + T, WIN_Y1, W, 0, H, M['wall'])
    box('Parede fundo C', L, L + T, WIN_Y0, WIN_Y1, 0, WIN_Z0, M['wall'])
    box('Parede fundo D', L, L + T, WIN_Y0, WIN_Y1, WIN_Z1, H, M['wall'])
    # peitoril / exterior
    box('Peitoril', L - 0.02, L + T, WIN_Y0 - 0.03, WIN_Y1 + 0.03, WIN_Z0 - 0.02, WIN_Z0, M['white'])
    box('Exterior', L + 0.8, L + 0.85, WIN_Y0 - 1, WIN_Y1 + 1, WIN_Z0 - 1, WIN_Z1 + 1, M['sky'])
    # persiana horizontal
    slats = []
    z = WIN_Z1 - 0.06
    while z > WIN_Z0 + 0.01:
        slats.append((L + 0.03, L + 0.06, WIN_Y0 + 0.02, WIN_Y1 - 0.02, z - 0.0105, z + 0.0105))
        z -= 0.025
    multibox('Persiana', slats, M['blind'])
    box('Caixa persiana', L + 0.01, L + 0.07, WIN_Y0 + 0.01, WIN_Y1 - 0.01, WIN_Z1 - 0.06, WIN_Z1, M['white'])
    # rodapés brancos
    box('Rodape porta A', 0, 0.015, 0, DOOR_Y0 - 0.09, 0, 0.1, M['white'])
    box('Rodape porta B', 0, 0.015, DOOR_Y1 + 0.09, W, 0, 0.1, M['white'])
    box('Rodape fundo', L - 0.015, L, 1.72, WIN_Y1 + 0.12, 0, 0.1, M['white'])
    # corredor externo
    box('Corredor parede 1', -2.6, -T, 0.75, 0.9, 0, H, M['corr'])
    box('Corredor parede 2', -2.6, -T, 2.1, 2.25, 0, H, M['corr'])
    box('Corredor fundo', -2.75, -2.6, 0.75, 2.25, 0, H, M['corr'])
    # porta de entrada: batentes + guarnições
    for (y0, y1) in ((DOOR_Y0 - 0.08, DOOR_Y0), (DOOR_Y1, DOOR_Y1 + 0.08)):
        box('Guarnicao', -0.012 - T, 0.012, y0, y1, 0, DOOR_H, M['white'])
    box('Guarnicao topo', -0.012 - T, 0.012, DOOR_Y0 - 0.08, DOOR_Y1 + 0.08, DOOR_H, DOOR_H + 0.08, M['white'])
    hinge = empty('Porta entrada', (-0.05, DOOR_Y1 - 0.005, 0))
    box('Folha porta', -0.085, -0.05, DOOR_Y0 + 0.005, DOOR_Y1 - 0.005, 0.005, DOOR_H - 0.005,
        M['white'], parent=hinge, bevel=0.002)
    for sx in (1, -1):
        # macaneta dos dois lados
        x = 0.0 if sx == 1 else -0.135
        box('Roseta', x - 0.015 * (sx == 1) - 0.0, x + 0.015 * (sx != 1), DOOR_Y0 + 0.07, DOOR_Y0 + 0.12,
            1.02, 1.08, M['inox'], parent=hinge)
        box('Macaneta', x - 0.025 if sx == 1 else x, x if sx == 1 else x + 0.025, DOOR_Y0 + 0.08,
            DOOR_Y0 + 0.22, 1.04, 1.06, M['inox'], parent=hinge, bevel=0.004)
    for z in (0.25, 1.05, 1.85):
        box('Dobradica', -0.05, -0.04, DOOR_Y1 - 0.015, DOOR_Y1 - 0.0, z, z + 0.1, M['inox'], parent=hinge)
    return hinge


def slat_panel(name, x0, x1, wall_y, sign, z0, z1, depth=0.018, gap=0.007):
    """Painel ripado de madeira na parede (plano XZ). sign=+1 cresce p/ +y."""
    yb0, yb1 = sorted((wall_y, wall_y + sign * 0.004))
    box(name + ' fundo', x0, x1, yb0, yb1, z0, z1, M['slat_back'])
    widths = [0.09, 0.14, 0.19, 0.12, 0.21, 0.16, 0.10, 0.18]
    x = x0
    i = 0
    while x < x1 - 0.02:
        w = widths[(i * 3 + rng.randint(0, 7)) % len(widths)]
        xe = min(x + w, x1)
        ys = sorted((wall_y + sign * 0.004, wall_y + sign * depth))
        box('%s ripa %d' % (name, i), x, xe, ys[0], ys[1], z0, z1, M['oak'], bevel=0.0015, seg=1)
        x = xe + gap
        i += 1


def build_desk_wall():
    """Bancada dupla, prateleiras, painel ripado, sanca escura."""
    X1 = 2.5
    slat_panel('Ripado bancada', 0.0, X1, 0.0, +1, 0.0, 2.3)
    box('Sanca escura', 0.0, X1, 0.0, 0.36, 2.3, H, M['graphite'])
    box('Rodape bancada', 0.0, X1, 0.018, 0.035, 0.0, 0.09, M['white'])
    # tampo com borda arredondada
    box('Tampo bancada', 0.0, X1, 0.0, 0.62, 0.735, 0.775, M['cream'], bevel=0.018, seg=4)
    # prateleiras flutuantes + LED
    for i, z in enumerate((1.43, 1.83)):
        box('Prateleira %d' % i, 0.0, X1, 0.018, 0.30, z, z + 0.04, M['cream'], bevel=0.004)
        box('LED prateleira %d' % i, 0.03, X1 - 0.03, 0.03, 0.045, z - 0.004, z, M['led'])
        area_light('Luz prateleira %d' % i, (X1 / 2, 0.05, z - 0.01), (math.radians(20), 0, 0),
                   X1 - 0.1, 0.02, 40, (1.0, 0.74, 0.46))
    # LED sob a sanca (ilumina prateleira de cima)
    area_light('Luz sanca', (X1 / 2, 0.06, 2.29), (math.radians(15), 0, 0), X1 - 0.1, 0.02, 40, (1.0, 0.74, 0.46))
    box('LED sanca', 0.03, X1 - 0.03, 0.04, 0.055, 2.296, 2.3, M['led'])
    # monitores
    for wc in (0.735, 1.775):
        for k, dx in enumerate((-0.43, 0.0, 0.43)):
            ang = (18 if dx < 0 else -18 if dx > 0 else 0)
            build_monitor('Monitor', wc + dx, 0.26, ang * 0.45)
    # gaveteiros (3) com 4 gavetas cada
    drawers = {}
    for p, (px0, px1) in enumerate(((0.02, 0.44), (1.05, 1.47), (2.06, 2.48))):
        drawers[p] = build_pedestal(p, px0, px1)
    # suportes de teclado (2) deslizantes
    trays = []
    for t, wc in enumerate((0.735, 1.775)):
        tr = empty('Suporte teclado %d' % t, (wc, 0.1, 0.67))
        box('Bandeja', wc - 0.29, wc + 0.29, 0.1, 0.52, 0.655, 0.672, M['cream'], parent=tr, bevel=0.004)
        box('Teclado', wc - 0.22, wc + 0.2, 0.25, 0.39, 0.672, 0.69, M['black'], parent=tr, bevel=0.004)
        box('Mouse', wc + 0.23, wc + 0.27, 0.28, 0.34, 0.672, 0.69, M['black'], parent=tr, bevel=0.008)
        for sx in (-0.3, 0.29):
            box('Corredica', wc + sx, wc + sx + 0.012, 0.08, 0.52, 0.672, 0.735, M['inox'])
        trays.append(tr)
    # decoração nas prateleiras
    shelf_props()
    return drawers, trays


def build_monitor(name, x, y, ang):
    root = empty(name, (x, y, 0.775))
    root.rotation_euler[2] = math.radians(ang)
    box(name + ' base', x - 0.11, x + 0.11, y - 0.06, y + 0.08, 0.775, 0.787, M['black'], parent=root, bevel=0.004)
    box(name + ' haste', x - 0.022, x + 0.022, y - 0.02, y + 0.005, 0.787, 0.98, M['black'], parent=root)
    box(name + ' tela', x - 0.19, x + 0.19, y + 0.005, y + 0.03, 0.89, 1.135, M['screen'], parent=root, bevel=0.003)
    box(name + ' costas', x - 0.17, x + 0.17, y - 0.012, y + 0.006, 0.92, 1.1, M['black'], parent=root, bevel=0.01)


def build_pedestal(p, x0, x1):
    y0, y1 = 0.06, 0.56
    box('Gaveteiro %d corpo' % p, x0, x1, y0, y1 - 0.02, 0.06, 0.735, M['navy'])
    box('Gaveteiro %d rodape' % p, x0 + 0.02, x1 - 0.02, y0, y1 - 0.06, 0.0, 0.06, M['navy'])
    hs = [0.18, 0.16, 0.16, 0.16]
    z = 0.733
    out = []
    for d, h in enumerate(hs):
        z_top = z
        z_bot = z - h
        e = empty('Gaveta %d.%d' % (p, d), ((x0 + x1) / 2, y1, z_bot))
        box('Frente', x0 + 0.002, x1 - 0.002, y1 - 0.02, y1, z_bot + 0.002, z_top - 0.024, M['navy'], parent=e, bevel=0.0015)
        box('Puxador cava', x0 + 0.002, x1 - 0.002, y1 - 0.02, y1 - 0.006, z_top - 0.024, z_top - 0.003, M['groove'], parent=e)
        box('Frente topo', x0 + 0.002, x1 - 0.002, y1 - 0.006, y1, z_top - 0.024, z_top - 0.004, M['navy'], parent=e)
        # caixa interna
        bx0, bx1 = x0 + 0.03, x1 - 0.03
        box('Fundo gaveta', bx0, bx1, y0 + 0.04, y1 - 0.02, z_bot + 0.02, z_bot + 0.03, M['inside'], parent=e)
        box('Lado A', bx0, bx0 + 0.012, y0 + 0.04, y1 - 0.02, z_bot + 0.02, z_top - 0.05, M['inside'], parent=e)
        box('Lado B', bx1 - 0.012, bx1, y0 + 0.04, y1 - 0.02, z_bot + 0.02, z_top - 0.05, M['inside'], parent=e)
        box('Traseira', bx0, bx1, y0 + 0.04, y0 + 0.052, z_bot + 0.02, z_top - 0.05, M['inside'], parent=e)
        # conteúdo
        if d == 0:
            for k in range(5):
                cx = bx0 + 0.04 + k * 0.065
                box('Caneta', cx, cx + 0.012, y1 - 0.38, y1 - 0.24, z_bot + 0.03, z_bot + 0.042,
                    M['books'][(k * 5) % 12], parent=e, bevel=0.004)
            box('Bloco', bx0 + 0.05, bx0 + 0.2, y1 - 0.2, y1 - 0.07, z_bot + 0.03, z_bot + 0.045, M['paper'], parent=e)
        else:
            nfold = 6 if d == 3 else 3
            for k in range(nfold):
                yy = y0 + 0.08 + k * 0.055
                box('Pasta', bx0 + 0.02, bx1 - 0.02, yy, yy + 0.012, z_bot + 0.03, z_top - 0.07,
                    M['books'][(k * 7 + d) % 12], parent=e)
        out.append(e)
        z = z_bot
    return out


def shelf_props():
    def books_run(x, z, y0, n, lean=False):
        bxs = {}
        for i in range(n):
            w = rng.uniform(0.018, 0.045)
            h = rng.uniform(0.17, 0.27)
            dpt = rng.uniform(0.14, 0.2)
            mi = rng.randrange(len(M['books']))
            bxs.setdefault(mi, []).append((x, x + w, y0, y0 + dpt, z, z + h))
            x += w + 0.001
        for mi, b in bxs.items():
            multibox('Livros', b, M['books'][mi])
        return x

    # prateleira de cima (z=1.87)
    z1, z2 = 1.87, 1.47
    books_run(0.05, z1, 0.06, 9)
    books_run(0.75, z1, 0.06, 13)
    books_run(2.0, z1, 0.06, 14)
    # quadro
    fr = box('Quadro moldura', 1.45, 1.75, 0.07, 0.10, z1, z1 + 0.36, M['frame_art'], bevel=0.003)
    fr.rotation_euler[0] = math.radians(-8)
    box('Quadro tela', 1.48, 1.72, 0.10, 0.104, z1 + 0.04, z1 + 0.32, M['art'])
    cyl('Vaso preto', 1.92, 0.15, z1, z1 + 0.12, 0.045, M['ceramic'])
    cyl('Vela', 0.62, 0.14, z1, z1 + 0.09, 0.035, M['vase'])
    # prateleira de baixo (z=1.47)
    books_run(0.38, z2, 0.07, 2)
    books_run(1.9, z2, 0.06, 16)
    cyl('Vaso bege', 2.3, 0.16, z2, z2 + 0.12, 0.05, M['vase'])
    # globo
    cyl('Globo base', 0.18, 0.15, z2, z2 + 0.012, 0.05, M['brass'])
    cyl('Globo haste', 0.18, 0.15, z2, z2 + 0.06, 0.006, M['brass'])
    sphere('Globo', 0.18, 0.15, z2 + 0.15, 0.085, M['globe'])


def build_chair(name, x, y, rot_deg):
    root = empty(name, (x, y, 0))
    root.rotation_euler[2] = math.radians(rot_deg)
    for k in range(5):
        a = k * 2 * math.pi / 5
        leg = box(name + ' perna', x, x + 0.32, y - 0.018, y + 0.018, 0.06, 0.085, M['chrome'],
                  pivot=(x, y, 0.07), parent=root, bevel=0.008)
        leg.rotation_euler[2] = a
        sphere(name + ' rodizio', x + 0.3 * math.cos(a), y + 0.3 * math.sin(a), 0.03, 0.03, M['black'],
               parent=root, seg=12)
    cyl(name + ' cubo', x, y, 0.05, 0.1, 0.045, M['chrome'], parent=root)
    cyl(name + ' pistao', x, y, 0.1, 0.42, 0.024, M['chrome'], parent=root)
    box(name + ' mecanismo', x - 0.12, x + 0.12, y - 0.12, y + 0.12, 0.40, 0.44, M['black'], parent=root)
    box(name + ' assento', x - 0.25, x + 0.25, y - 0.25, y + 0.22, 0.44, 0.53, M['leather'], parent=root,
        bevel=0.035, seg=4)
    back = box(name + ' encosto', x - 0.24, x + 0.24, y + 0.17, y + 0.25, 0.5, 1.05, M['leather'],
               pivot=(x, y + 0.2, 0.5), parent=root, bevel=0.035, seg=4)
    back.rotation_euler[0] = math.radians(-10)
    for sx in (-1, 1):
        box(name + ' braco', x + sx * 0.25 - 0.035, x + sx * 0.25 + 0.035, y - 0.05, y + 0.22, 0.5, 0.66,
            M['leather'], parent=root, bevel=0.03, seg=3)
    return root


def build_sideboard():
    """Aparador baixo (6 portas) na parede y=W + painel ripado + LED + ar-condicionado."""
    x0, x1 = 0.02, L - 0.02
    yf = W - 0.55
    dw = (x1 - x0) / 6
    I = M['inside']
    box('Aparador lateral A', x0, x0 + 0.018, yf, W, 0.1, 0.86, M['navy'])
    box('Aparador lateral B', x1 - 0.018, x1, yf, W, 0.1, 0.86, M['navy'])
    box('Aparador fundo', x0, x1, W - 0.018, W, 0.1, 0.86, I)
    box('Aparador base', x0, x1, yf, W, 0.1, 0.118, I)
    box('Aparador teto', x0, x1, yf, W, 0.842, 0.86, I)
    for k in (2, 4):
        xx = x0 + k * dw
        box('Aparador divisoria', xx - 0.009, xx + 0.009, yf, W, 0.118, 0.842, I)
    box('Aparador rodape', x0 + 0.02, x1 - 0.02, yf + 0.06, W, 0.0, 0.1, M['navy'])
    box('Aparador tampo', x0, x1, yf - 0.025, W, 0.86, 0.89, M['navy_top'], bevel=0.003)
    box('Aparador prateleira', x0 + 0.02, x1 - 0.02, yf + 0.03, W - 0.02, 0.47, 0.488, I)
    # remove a "tampa" frontal interna: corpo é oco para as portas centrais
    doors = []
    n = 6
    for i in range(n):
        dx0 = x0 + i * dw + 0.002
        dx1 = x0 + (i + 1) * dw - 0.002
        left = (i % 2 == 0)
        hx = dx0 if left else dx1
        e = empty('Porta aparador %d' % i, (hx, yf - 0.02, 0.1))
        box('Porta', dx0, dx1, yf - 0.02, yf, 0.105, 0.835, M['navy'], parent=e, bevel=0.0015)
        box('Puxador cava', dx0, dx1, yf - 0.02, yf - 0.006, 0.835, 0.858, M['groove'], parent=e)
        box('Porta topo', dx0, dx1, yf - 0.006, yf, 0.835, 0.858, M['navy'], parent=e)
        doors.append(e)
    # conteúdo do nicho central (portas 2 e 3)
    cx0 = x0 + 2 * dw
    k = 0
    for xx in [cx0 + 0.05 + j * 0.075 for j in range(7)]:
        box('Pasta AZ', xx, xx + 0.07, W - 0.35, W - 0.05, 0.49, 0.80, M['binder'] if k % 3 else M['box_kraft'],
            bevel=0.003)
        k += 1
    for j in range(5):
        box('Resma', cx0 + 0.05, cx0 + 0.27, W - 0.35, W - 0.05, 0.12 + j * 0.055, 0.17 + j * 0.055, M['paper'])
    box('Caixa', cx0 + 0.6, cx0 + 1.0, W - 0.42, W - 0.06, 0.12, 0.40, M['box_kraft'], bevel=0.004)
    # painel ripado + LED rasante
    slat_panel('Ripado aparador', 0.0, L, W, -1, 0.89, H)
    box('LED aparador', 0.02, L - 0.02, W - 0.035, W - 0.02, 0.89, 0.896, M['led'])
    area_light('Luz aparador', (L / 2, W - 0.06, 0.9), (math.radians(-12), 0, 0), L - 0.1, 0.02, 70,
               (1.0, 0.74, 0.46))
    # ar-condicionado
    box('Split', 1.4, 2.25, W - 0.22, W - 0.02, 2.2, 2.5, M['plastic_w'], bevel=0.03, seg=3)
    box('Split aleta', 1.45, 2.2, W - 0.225, W - 0.2, 2.22, 2.25, M['plastic_g'])
    # impressoras
    box('Multifuncional', 2.95, 3.42, W - 0.48, W - 0.08, 0.89, 1.2, M['plastic_w'], bevel=0.01)
    box('Multifuncional scanner', 2.95, 3.42, W - 0.48, W - 0.08, 1.2, 1.28, M['plastic_w'], bevel=0.01)
    box('Multifuncional bandeja', 3.0, 3.37, W - 0.5, W - 0.47, 0.93, 1.1, M['plastic_g'])
    box('Impressora', 0.35, 0.8, W - 0.42, W - 0.1, 0.89, 1.05, M['black'], bevel=0.008)
    for j in range(4):
        box('Tanque', 0.6 + j * 0.035, 0.625 + j * 0.035, W - 0.43, W - 0.41, 0.9, 0.97, M['plastic_w'])
    return doors


def build_wardrobe():
    """Armário em L no canto (x=L, y=0)."""
    XF = 3.0    # face frontal do corpo principal (voltada p/ -x)
    YF = 0.6    # face frontal da perna do L (voltada p/ +y)
    XL = 2.5    # início da perna do L
    YM = 1.7    # fim do corpo principal
    TOP = 2.55
    G = M['graphite']
    # carcaça
    box('Armario lateral L', XL, XL + 0.02, 0.0, YF, 0.0, H, G)               # lateral voltada p/ bancada
    box('Armario lateral', XF, L, YM - 0.02, YM, 0.0, H, G)                    # lateral junto à janela
    box('Armario rodape A', XF + 0.04, L, YF, YM, 0, 0.1, G)
    box('Armario rodape B2', XL + 0.02, L, 0.0, YF - 0.04, 0, 0.1, G)
    box('Armario base A', XF, L, YF, YM - 0.02, 0.1, 0.12, M['inside'])
    box('Armario base B', XL + 0.02, L, 0.0, YF, 0.1, 0.12, M['inside'])
    box('Armario topo', XL + 0.02, L, 0.0, YM - 0.02, TOP - 0.02, TOP, M['inside'])
    box('Armario requadro A', XF - 0.02, XF, YF, YM, TOP, H, G)
    box('Armario requadro B', XL, XF, YF - 0.02, YF, TOP, H, G)
    box('Armario fundo A', L - 0.02, L, YF, YM, 0.12, TOP, M['inside'])
    box('Armario fundo B', XL + 0.02, L, 0.0, 0.02, 0.12, TOP, M['inside'])
    # divisória central do corpo principal
    ymid = (YF + YM) / 2
    box('Divisoria', XF + 0.02, L - 0.02, ymid - 0.009, ymid + 0.009, 0.12, TOP - 0.02, M['inside'])
    # lado esquerdo do corpo (perto do canto): prateleiras com caixas arquivo
    for z in (0.5, 0.88, 1.26, 1.64, 2.02):
        box('Prateleira A', XF + 0.02, L - 0.02, YF, ymid - 0.009, z, z + 0.02, M['inside'])
    for zi, z in enumerate((0.12, 0.5, 0.88, 1.26, 1.64, 2.02)):
        for j in range(3):
            yy = YF + 0.03 + j * 0.155
            if yy + 0.14 < ymid - 0.01 and not (zi == 5 and j == 2):
                box('Caixa arquivo', XF + 0.08, L - 0.05, yy, yy + 0.14, z + 0.02, z + 0.3,
                    M['box_kraft'] if (zi + j) % 2 else M['binder'], bevel=0.003)
    # lado direito: prateleira alta + cabideiro + gaveteiro interno
    box('Prateleira B', XF + 0.02, L - 0.02, ymid + 0.009, YM - 0.02, 2.0, 2.02, M['inside'])
    rl = YM - 0.02 - ymid
    cyl('Cabideiro', XF + 0.3, ymid + 0.009 + rl / 2, 1.9 - rl / 2, 1.9 + rl / 2, 0.012, M['chrome'],
        rot=(math.radians(90), 0, 0))
    for z in (1.05, 1.5):
        box('Prateleira B2', XF + 0.02, L - 0.02, ymid + 0.009, YM - 0.02, z, z + 0.02, M['inside'])
        for j in range(3):
            yy = ymid + 0.04 + j * 0.16
            box('Caixa B', XF + 0.08, L - 0.05, yy, yy + 0.14, z + 0.02, z + 0.3,
                M['box_kraft'] if j % 2 else M['binder'], bevel=0.003)
    for j in range(5):
        yy = ymid + 0.05 + j * 0.1
        box('Pasta suspensa', XF + 0.1, L - 0.08, yy, yy + 0.02, 1.62, 1.92, M['books'][(j * 5) % 12])
    for j in range(3):
        e = box('Gaveta interna', XF + 0.03, L - 0.03, ymid + 0.012, YM - 0.022, 0.13 + j * 0.2,
                0.31 + j * 0.2, M['inside'], bevel=0.003)
    for j in range(3):
        yy = ymid + 0.04 + j * 0.16
        box('Caixa topo', XF + 0.08, L - 0.05, yy, yy + 0.14, 2.02, 2.3, M['box_kraft'], bevel=0.003)
    # perna do L: prateleiras profundas (vão de XL até L)
    for z in (0.55, 1.0, 1.45, 1.9):
        box('Prateleira L', XL + 0.02, L - 0.02, 0.02, YF - 0.02, z, z + 0.02, M['inside'])
    for zi, z in enumerate((0.12, 0.55, 1.0, 1.45, 1.9)):
        for j in range(5):
            xx = XL + 0.05 + j * 0.085
            if xx + 0.075 < XF - 0.01:
                box('Pasta L', xx, xx + 0.075, 0.08, 0.4, z + 0.02, z + 0.33,
                    M['binder'] if (j + zi) % 3 else M['box_kraft'], bevel=0.003)
        box('Resma L', XL + 0.05, XL + 0.35, 0.42, 0.56, z + 0.02, z + 0.08, M['paper'])

    # portas frisadas: tiras com frisos de 6 mm (aparência do projeto)
    def frisada(parent, a0, a1, axis, plane, sgn, z0, z1, nstrips):
        w = (a1 - a0) / nstrips
        t0, t1 = sorted((plane, plane + sgn * 0.022))
        b0, b1 = sorted((plane, plane + sgn * 0.016))
        if axis == 'y':
            box('Porta miolo', b0, b1, a0, a1, z0, z1, M['groove'], parent=parent)
        else:
            box('Porta miolo', a0, a1, b0, b1, z0, z1, M['groove'], parent=parent)
        for s in range(nstrips):
            s0 = a0 + s * w + (0.003 if s else 0)
            s1 = a0 + (s + 1) * w - (0.003 if s < nstrips - 1 else 0)
            if axis == 'y':
                box('Friso', t0, t1, s0, s1, z0, z1, G, parent=parent, bevel=0.0012, seg=1)
            else:
                box('Friso', s0, s1, t0, t1, z0, z1, G, parent=parent, bevel=0.0012, seg=1)

    z0, z1 = 0.105, TOP - 0.005
    # duas portas maiores: abrem do meio, cada uma para um lado (dobradiças nas extremidades)
    dA = empty('Porta armario A', (XF, YF + 0.002, 0))           # dobradiça junto ao canto
    frisada(dA, YF + 0.002, ymid - 0.002, 'y', XF, -1, z0, z1, 4)
    dB = empty('Porta armario B', (XF, YM - 0.002, 0))           # dobradiça junto à janela
    frisada(dB, ymid + 0.002, YM - 0.002, 'y', XF, -1, z0, z1, 4)
    # porta da perna do L: dobradiça à direita (lado da bancada) -> abre da esquerda p/ a direita
    dL = empty('Porta armario L', (XL + 0.022, YF, 0))
    frisada(dL, XL + 0.022, XF - 0.024, 'x', YF, +1, z0, z1, 3)
    # luz interna (acende ao abrir)
    lA = area_light('Luz armario A', (XF + 0.25, (YF + ymid) / 2, TOP - 0.04), (0, 0, 0), 0.45, 0.5, 0.0,
                    (1.0, 0.8, 0.6))
    lB = area_light('Luz armario B', (XF + 0.25, (ymid + YM) / 2, TOP - 0.04), (0, 0, 0), 0.45, 0.5, 0.0,
                    (1.0, 0.8, 0.6))
    lL = area_light('Luz armario L', ((XL + XF) / 2 + 0.1, 0.3, TOP - 0.04), (0, 0, 0), 0.5, 0.5, 0.0,
                    (1.0, 0.8, 0.6))
    return dA, dB, dL, (lA, lB, lL)


def build_ceiling_lights():
    warm = (1.0, 0.72, 0.45)
    # perfil de LED embutido no forro em L
    box('Perfil LED 1', 0.3, 2.75, 0.62, 0.64, H - 0.003, H, M['led_cool'])
    box('Perfil LED 2', 2.73, 2.75, 0.62, 1.8, H - 0.003, H, M['led_cool'])
    area_light('Luz perfil 1', (1.525, 0.63, H - 0.01), (0, 0, 0), 2.45, 0.03, 60, warm)
    area_light('Luz perfil 2', (2.74, 1.21, H - 0.01), (0, 0, 0), 0.03, 1.18, 30, warm)
    # spots embutidos
    for (x, y) in ((1.0, 1.75), (2.15, 1.75), (3.15, 2.25), (0.6, 2.3)):
        cyl('Spot aro', x, y, H - 0.006, H, 0.045, M['inox'], verts=20)
        cyl('Spot lente', x, y, H - 0.008, H - 0.006, 0.03, M['led_cool'], verts=16)
        spot_light('Spot', (x, y, H - 0.02), 30, warm, size_deg=100, blend=0.8)
    # corredor
    point_light('Luz corredor', (-1.4, 1.5, H - 0.15), 60, (1.0, 0.85, 0.7), radius=0.15)
    # luz natural da janela
    area_light('Luz janela', (L - 0.05, (WIN_Y0 + WIN_Y1) / 2, (WIN_Z0 + WIN_Z1) / 2),
               (0, math.radians(-90), 0), WIN_Z1 - WIN_Z0, WIN_Y1 - WIN_Y0, 70, (0.85, 0.92, 1.0))
    # preenchimento global suave (simula rebatimento)
    area_light('Fill', (1.8, 1.45, H - 0.05), (0, 0, 0), 2.6, 2.0, 20, (1.0, 0.85, 0.7))


# ----------------------------------------------------------------------------
# câmera
# ----------------------------------------------------------------------------
def look_rot(pos, tgt):
    d = Vector(tgt) - Vector(pos)
    yaw = math.atan2(d.y, d.x) - math.pi / 2
    pitch = math.pi / 2 + math.atan2(d.z, math.hypot(d.x, d.y))
    return pitch, yaw


def build_camera(lens=18):
    cd = bpy.data.cameras.new('Camera')
    cd.lens = lens
    cd.sensor_width = 36
    cd.clip_start = 0.05
    cam = bpy.data.objects.new('Camera', cd)
    coll().objects.link(cam)
    bpy.context.scene.camera = cam
    return cam


def animate_camera(cam, keys):
    """keys: lista (frame, pos, tgt). Yaw é 'desenrolado' p/ giro contínuo."""
    prev = None
    for f, pos, tgt in keys:
        pitch, yaw = look_rot(pos, tgt)
        if prev is not None:
            while yaw - prev > math.pi:
                yaw -= 2 * math.pi
            while yaw - prev < -math.pi:
                yaw += 2 * math.pi
        prev = yaw
        cam.location = pos
        cam.rotation_euler = (pitch, 0, yaw)
        cam.keyframe_insert('location', frame=f)
        cam.keyframe_insert('rotation_euler', frame=f)


def set_view(cam, pos, tgt):
    pitch, yaw = look_rot(pos, tgt)
    cam.location = pos
    cam.rotation_euler = (pitch, 0, yaw)


# ----------------------------------------------------------------------------
# cena completa + roteiro
# ----------------------------------------------------------------------------
def build_scene():
    reset()
    build_materials()
    entry = build_architecture()
    drawers, trays = build_desk_wall()
    chair1 = build_chair('Cadeira 1', 0.735, 1.0, 0)
    chair2 = build_chair('Cadeira 2', 1.775, 1.05, -8)
    sb_doors = build_sideboard()
    dA, dB, dL, wl = build_wardrobe()
    build_ceiling_lights()
    world = bpy.data.worlds.new('World')
    bpy.context.scene.world = world
    bg = world.node_tree.nodes.get('Background')
    if bg:
        bg.inputs['Color'].default_value = (0.02, 0.02, 0.025, 1)
        bg.inputs['Strength'].default_value = 1.0
    return dict(entry=entry, drawers=drawers, trays=trays, chair1=chair1, chair2=chair2,
                sb_doors=sb_doors, dA=dA, dB=dB, dL=dL, wlights=wl)


def sec(s):
    return int(round(s * FPS)) + 1


def choreograph(S, cam):
    """Roteiro do tour (24 fps, ~61 s)."""
    ent, dA, dB, dL = S['entry'], S['dA'], S['dB'], S['dL']
    lA, lB, lL = S['wlights']
    # --- porta de entrada
    key_rotz(ent, sec(0.0), 0)
    key_rotz(ent, sec(1.0), 0)
    key_rotz(ent, sec(2.6), 92)
    key_rotz(ent, sec(5.4), 92)
    key_rotz(ent, sec(7.0), 0)
    # --- armário: portas centrais (abrem do meio para os lados)
    key_rotz(dA, sec(18.0), 0); key_rotz(dB, sec(18.0), 0)
    key_rotz(dA, sec(20.2), 92); key_rotz(dB, sec(20.2), -95)
    key_rotz(dA, sec(24.6), 92); key_rotz(dB, sec(24.6), -95)
    key_rotz(dA, sec(26.4), 0); key_rotz(dB, sec(26.4), 0)
    for lt in (lA, lB):
        key_energy(lt, sec(18.0), 0); key_energy(lt, sec(18.8), 45)
        key_energy(lt, sec(25.6), 45); key_energy(lt, sec(26.4), 0)
    # --- perna do L: dobradiça à direita, abre da esquerda p/ a direita
    key_rotz(dL, sec(28.2), 0)
    key_rotz(dL, sec(30.2), 100)
    key_rotz(dL, sec(33.2), 100)
    key_rotz(dL, sec(35.0), 0)
    key_energy(lL, sec(28.2), 0); key_energy(lL, sec(29.0), 60)
    key_energy(lL, sec(34.2), 60); key_energy(lL, sec(35.0), 0)
    # --- gaveteiro central: 4 gavetas em sequência
    ped = S['drawers'][1]
    for i, d in enumerate(ped):
        x, y, z = tuple(d.location)
        t0 = 37.2 + i * 1.15
        key_loc(d, sec(t0), (x, y, z))
        key_loc(d, sec(t0 + 0.8), (x, y + 0.36, z))
        key_loc(d, sec(t0 + 1.5), (x, y + 0.36, z))
        key_loc(d, sec(t0 + 2.3), (x, y, z))
    # --- cadeira 2 recua, suporte de teclado desliza
    c2 = S['chair2']
    key_loc(c2, sec(42.4), tuple(c2.location)); key_rotz(c2, sec(42.4), -8)
    key_loc(c2, sec(44.0), (2.12, 1.38, 0)); key_rotz(c2, sec(44.0), 25)
    key_loc(c2, sec(47.8), (2.12, 1.38, 0)); key_rotz(c2, sec(47.8), 25)
    key_loc(c2, sec(49.4), (1.775, 1.05, 0)); key_rotz(c2, sec(49.4), -8)
    tr = S['trays'][1]
    tx, ty, tz = tuple(tr.location)
    key_loc(tr, sec(44.4), (tx, ty, tz))
    key_loc(tr, sec(45.4), (tx, ty + 0.26, tz))
    key_loc(tr, sec(46.8), (tx, ty + 0.26, tz))
    key_loc(tr, sec(47.8), (tx, ty, tz))
    # --- aparador: par central abre
    d2, d3 = S['sb_doors'][2], S['sb_doors'][3]
    key_rotz(d2, sec(50.0), 0); key_rotz(d3, sec(50.0), 0)
    key_rotz(d2, sec(51.8), -100); key_rotz(d3, sec(51.8), 100)
    key_rotz(d2, sec(54.4), -100); key_rotz(d3, sec(54.4), 100)
    key_rotz(d2, sec(56.0), 0); key_rotz(d3, sec(56.0), 0)

    # --- câmera
    E = 1.58
    keys = [
        (sec(0.0), (-1.9, 1.5, E), (2.0, 1.5, 1.35)),
        (sec(1.4), (-1.75, 1.5, E), (2.0, 1.5, 1.35)),
        (sec(4.4), (0.45, 1.45, E), (3.6, 1.2, 1.3)),
        (sec(5.6), (1.25, 1.45, E), (3.6, 1.2, 1.25)),
    ]
    # giro 360° no centro da sala
    c = Vector((1.55, 1.45, E))
    t0, dur = 6.0, 10.5
    steps = 16
    for k in range(steps + 1):
        a = 2 * math.pi * k / steps
        keys.append((sec(t0 + dur * k / steps), tuple(c), (c.x + 2 * math.cos(a), c.y + 2 * math.sin(a), E - 0.08)))
    keys += [
        # armário principal
        (sec(17.6), (1.35, 1.2, 1.5), (3.3, 1.15, 1.3)),
        (sec(20.4), (1.4, 1.2, 1.5), (3.3, 1.15, 1.3)),
        (sec(24.0), (1.75, 1.2, 1.5), (3.5, 1.15, 1.25)),
        (sec(26.4), (2.3, 1.75, 1.55), (2.75, 0.3, 1.25)),
        # perna do L (câmera do lado do canto, porta abre para a direita)
        (sec(28.0), (2.8, 1.75, 1.5), (2.7, 0.2, 1.1)),
        (sec(32.0), (2.78, 1.45, 1.45), (2.7, 0.1, 1.0)),
        (sec(35.2), (1.6, 1.6, 1.35), (1.3, 0.3, 0.6)),
        # gaveteiro central
        (sec(37.0), (1.26, 1.2, 1.45), (1.26, 0.55, 0.3)),
        (sec(41.6), (1.26, 1.15, 1.42), (1.26, 0.55, 0.3)),
        # suporte de teclado
        (sec(44.0), (1.55, 1.85, 1.3), (1.78, 0.35, 0.62)),
        (sec(47.6), (1.6, 1.85, 1.3), (1.78, 0.35, 0.62)),
        # aparador
        (sec(49.6), (1.8, 1.45, 1.45), (1.8, 2.8, 0.55)),
        (sec(54.8), (1.8, 1.55, 1.35), (1.8, 2.8, 0.5)),
        # plano final
        (sec(58.0), (0.35, 1.75, 1.62), (3.6, 0.9, 1.2)),
        (sec(61.0), (0.3, 1.8, 1.62), (3.6, 0.9, 1.2)),
    ]
    animate_camera(cam, keys)
    return sec(61.0)


STILLS = {
    # nome: (pos, tgt, lens, estado)
    '01_vista_geral': ((0.3, 1.8, 1.6), (3.6, 0.9, 1.25), 18, {}),
    '02_bancada': ((1.35, 2.75, 1.45), (1.25, 0.0, 1.0), 18, {}),
    '03_aparador': ((1.8, 0.25, 1.35), (1.8, 2.9, 1.1), 18, {}),
    '04_porta_entrada': ((2.9, 1.85, 1.55), (0.0, 1.35, 1.2), 18, {}),
    '05_armario_aberto': ((1.35, 1.2, 1.5), (3.3, 1.1, 1.25), 18, {'dA': 92, 'dB': -95, 'wl': [0, 1]}),
    '06_armario_L_aberto': ((2.78, 1.5, 1.45), (2.7, 0.1, 1.0), 18, {'dL': 100, 'wl': [2]}),
    '07_gavetas': ((1.26, 1.15, 1.42), (1.26, 0.55, 0.3), 18, {'drawers': True}),
    '08_aparador_aberto': ((1.6, 1.4, 1.4), (1.8, 2.8, 0.55), 18, {'sb': True}),
}


def apply_state(S, st):
    for k in ('dA', 'dB', 'dL'):
        S[k].rotation_euler[2] = math.radians(st.get(k, 0))
    for i, lt in enumerate(S['wlights']):
        lt.data.energy = 50 if i in st.get('wl', []) else 0
    for i, d in enumerate(S['drawers'][1]):
        d.location.y = 0.56 + ([0.36, 0.0, 0.22, 0.0][i] if st.get('drawers') else 0)
    sbd = S['sb_doors']
    sbd[2].rotation_euler[2] = math.radians(-100 if st.get('sb') else 0)
    sbd[3].rotation_euler[2] = math.radians(100 if st.get('sb') else 0)


# ----------------------------------------------------------------------------
# render
# ----------------------------------------------------------------------------
def setup_render(res, samples, out, fmt='PNG'):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = samples
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = 0.03
    sc.cycles.use_denoising = True
    sc.cycles.denoiser = 'OPENIMAGEDENOISE'
    try:
        sc.cycles.denoising_input_passes = 'RGB_ALBEDO_NORMAL'
        sc.cycles.denoising_prefilter = 'ACCURATE'
    except Exception:
        pass
    sc.cycles.max_bounces = 4
    sc.cycles.diffuse_bounces = int(os.environ.get('DIFF_BOUNCES', 3))
    if os.environ.get('FAST_GI'):
        sc.cycles.use_fast_gi = True
        sc.cycles.ao_bounces_render = 1
        sc.world.light_settings.distance = 1.5
    sc.cycles.glossy_bounces = 2
    sc.cycles.transmission_bounces = 2
    sc.cycles.transparent_max_bounces = 4
    sc.cycles.caustics_reflective = False
    sc.cycles.caustics_refractive = False
    sc.cycles.blur_glossy = 1.0
    sc.cycles.sample_clamp_indirect = 8.0
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.fps = FPS
    sc.render.image_settings.file_format = fmt
    if fmt == 'JPEG':
        sc.render.image_settings.quality = 92
    sc.render.filepath = out
    sc.view_settings.view_transform = os.environ.get('VT', 'AgX')
    try:
        sc.view_settings.look = os.environ.get('LOOK', 'AgX - Punchy')
    except Exception:
        pass
    sc.view_settings.exposure = 0.0
    sc.render.use_persistent_data = True


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument('--mode', default='anim')
    ap.add_argument('--start', type=int, default=1)
    ap.add_argument('--end', type=int, default=0)
    ap.add_argument('--step', type=int, default=1)
    ap.add_argument('--res', type=int, nargs=2, default=(1280, 720))
    ap.add_argument('--samples', type=int, default=24)
    ap.add_argument('--exposure', type=float, default=0.0)
    ap.add_argument('--only', default='')
    ap.add_argument('--out', default='out/')
    a = ap.parse_args(argv)

    S = build_scene()
    cam = build_camera(18)
    last = choreograph(S, cam)
    sc = bpy.context.scene
    sc.frame_start, sc.frame_end = 1, last
    setup_render(tuple(a.res), a.samples, a.out)
    sc.view_settings.exposure = a.exposure

    if a.mode == 'blend':
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(a.out))
        return
    if a.mode == 'anim':
        end = a.end or last
        os.makedirs(a.out, exist_ok=True)
        for f in range(a.start, end + 1, a.step):
            path = os.path.join(a.out, 'f%04d.png' % f)
            if os.path.exists(path):
                continue
            sc.frame_set(f)
            sc.render.filepath = path
            bpy.ops.render.render(write_still=True)
            print('FRAME', f, flush=True)
        return
    # stills / pano: sem animação
    sc.frame_set(1)
    for ob in list(bpy.data.objects):
        ob.animation_data_clear()
    for ld in bpy.data.lights:
        ld.animation_data_clear()
    os.makedirs(a.out, exist_ok=True)
    if a.mode == 'still':
        for name, (pos, tgt, lens, st) in STILLS.items():
            if a.only and a.only not in name:
                continue
            apply_state(S, st)
            # porta de entrada fechada nas imagens internas
            S['entry'].rotation_euler[2] = 0
            cam.data.lens = lens
            set_view(cam, pos, tgt)
            sc.render.filepath = os.path.join(a.out, name + '.png')
            bpy.ops.render.render(write_still=True)
            print('STILL', name, flush=True)
    elif a.mode == 'pano':
        apply_state(S, {})
        S['entry'].rotation_euler[2] = 0
        cam.data.type = 'PANO'
        cam.data.panorama_type = 'EQUIRECTANGULAR'
        cam.location = (1.6, 1.45, 1.5)
        cam.rotation_euler = (math.radians(90), 0, math.radians(-90))
        sc.render.filepath = os.path.join(a.out, 'panorama_360.png')
        bpy.ops.render.render(write_still=True)


if __name__ == '__main__':
    main()
