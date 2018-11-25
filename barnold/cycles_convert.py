# ##### BEGIN MIT LICENSE BLOCK #####
#
# Copyright (c) 2015 - 2018 Pixar
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
#
# ##### END MIT LICENSE BLOCK #####
import bpy

converted_nodes = {}
report = None


def convert_cycles_node(nt, node, location=None):
    node_type = node.bl_idname
    if node.name in converted_nodes:
        return nt.nodes[converted_nodes[node.name]]

    elif node_type == 'ShaderNodeGroup':
        node_name = node.bl_idname
        rman_node = nt.nodes.new(node_name)
        if location:
            rman_node.location = location
        convert_node_group(nt, node, rman_node)
        converted_nodes[node.name] = rman_node.name
        return rman_node
    elif node_type in ['ShaderNodeRGBCurve', 'ShaderNodeVectorCurve']:
        node_name = node.bl_idname
        rman_node = nt.nodes.new(node_name)
        if location:
            rman_node.location = location
        convert_rgb_curve_node(nt, node, rman_node)
        converted_nodes[node.name] = rman_node.name
        return rman_node
    elif node_type in node_map.keys():
        rman_name, convert_func = node_map[node_type]
        node_name = rman_name + 'PatternNode'
        rman_node = nt.nodes.new(node_name)
        if location:
            rman_node.location = location
        convert_func(nt, node, rman_node)
        converted_nodes[node.name] = rman_node.name
        return rman_node
    elif node_type in ['ShaderNodeAddShader', 'ShaderNodeMixShader']:
        i = 0 if node.bl_idname == 'ShaderNodeAddShader' else 1
        node1 = node.inputs[
            0 + i].links[0].from_node if node.inputs[0 + i].is_linked else None
        node2 = node.inputs[
            1 + i].links[0].from_node if node.inputs[1 + i].is_linked else None

        mixer = nt.nodes.new('ArnoldNodeMixShader')
        if location:
            mixer.location = location
        # set the layer masks
        if node.bl_idname == 'ShaderNodeAddShader':
            mixer.layer1Mask = .5
        else:
            convert_cycles_input(nt, node.inputs['Fac'], mixer, 'layer1Mask')

        # make a new node for each
        convert_cycles_input(nt, node.inputs[0 + i], mixer, 'baselayer')
        convert_cycles_input(nt, node.inputs[1 + i], mixer, 'layer1')
        return mixer
    elif node_type in bsdf_map.keys():
        rman_name, convert_func = bsdf_map[node_type]
        node_name = 'ArnoldLayerPattern'
        rman_node = nt.nodes.new(node_name)
        rman_node.enableDiffuse = False
        rman_node.diffuseGain = 0
        if location:
            rman_node.location = location
        convert_func(nt, node, rman_node)
        converted_nodes[node.name] = rman_node.name
        return rman_node
    # else this is just copying the osl node!
    # TODO make this an RMAN osl node
    elif node_type != 'NodeUndefined':
        node_name = node.bl_idname
        rman_node = nt.nodes.new(node_name)
        if location:
            rman_node.location = location
        copy_cycles_node(nt, node, rman_node)
        converted_nodes[node.name] = rman_node.name
        return rman_node
    else:
        report({'ERROR'}, 'Error converting node %s of type %s.' %
               (node.name, node_type))
        return None


def convert_cycles_input(nt, socket, rman_node, param_name):
    if socket.is_linked:
        location = rman_node.location - \
            (socket.node.location - socket.links[0].from_node.location)
        node = convert_cycles_node(nt, socket.links[0].from_node, location)
        if node:
            # find the appropriate socket to hook up.
            input = rman_node.inputs[param_name]
            if socket.links[0].from_socket.name in node.outputs:
                nt.links.new(node.outputs[socket.links[
                             0].from_socket.name], input)
            else:
                from .nodes import is_same_type
                for output in node.outputs:
                    if is_same_type(input, output):
                        nt.links.new(output, input)
                        break
                else:
                    nt.links.new(node.outputs[0], input)

    elif hasattr(socket, 'default_value'):
        if hasattr(rman_node, 'renderman_node_type'):
            if type(getattr(rman_node, param_name)).__name__ == 'Color':
                setattr(rman_node, param_name, socket.default_value[:3])
            else:
                setattr(rman_node, param_name, socket.default_value)
        else:
            # this is a cycles node
            rman_node.inputs[param_name].default_value = socket.default_value

#########  other node conversion methods  ############


def convert_tex_image_node(nt, cycles_node, rman_node):
    if cycles_node.image:
        if cycles_node.image.packed_file:
            cycles_node.image.unpack()
        setattr(rman_node, 'filename', cycles_node.image.filepath)

    # can't link a vector to a manifold :(
    # if cycles_node.inputs['Vector'].is_linked:
    #    convert_cycles_input(nt, cycles_node.inputs['Vector'], rman_node, 'manifold')


def convert_tex_coord_node(nt, cycles_node, rman_node):
    return


def convert_mix_rgb_node(nt, cycles_node, rman_node):
    setattr(rman_node, 'clampOutput', cycles_node.use_clamp)
    convert_cycles_input(nt, cycles_node.inputs[
                         'Color1'], rman_node, 'bottomRGB')
    convert_cycles_input(nt, cycles_node.inputs['Color2'], rman_node, 'topRGB')
    convert_cycles_input(nt, cycles_node.inputs['Fac'], rman_node, 'topA')
    conversion = {'MIX': '10',
                  'ADD': '19',
                  'MULTIPLY': '18',
                  'SUBTRACT': '25',
                  'SCREEN': '23',
                  'DIVIDE': '7',
                  'DIFFERENCE': '5',
                  'DARKEN': '3',
                  'LIGHTEN': '12',
                  'OVERLAY': '20',
                  'DODGE': '15',
                  'BURN': '14',
                  'HUE': '11',
                  'SATURATION': '22',
                  'VALUE': '17',
                  'COLOR': '0',
                  'SOFT_LIGHT': '24',
                  'LINEAR_LIGHT': '16'}
    setattr(rman_node, 'operation', conversion[cycles_node.blend_type])


def convert_node_group(nt, cycles_node, rman_node):
    rman_nt = bpy.data.node_groups.new(rman_node.name, 'ShaderNodeTree')
    rman_node.node_tree = rman_nt
    cycles_nt = cycles_node.node_tree
    # save converted nodes to temp
    global converted_nodes
    temp_converted_nodes = converted_nodes
    converted_nodes = {}

    # create the output node
    cycles_output_node = next(
        (n for n in cycles_nt.nodes if n.bl_idname == 'NodeGroupOutput'), None)
    if cycles_output_node:
        rman_output_node = rman_nt.nodes.new('NodeGroupOutput')
        rman_output_node.location = cycles_output_node.location

        # tree outputs
        for tree_output in cycles_nt.outputs:
            out_type = tree_output.__class__.__name__.replace('Interface', '')
            rman_nt.outputs.new(out_type, tree_output.name)
    # create the input node
    cycles_input_node = next(
        (n for n in cycles_nt.nodes if n.bl_idname == 'NodeGroupInput'), None)
    if cycles_input_node:
        rman_input_node = rman_nt.nodes.new('NodeGroupInput')
        rman_input_node.location = cycles_input_node.location
        # tree outputs
        for tree_input in cycles_nt.inputs:
            input_type = tree_input.__class__.__name__.replace('Interface', '')
            rman_nt.inputs.new(input_type, tree_input.name)

        converted_nodes[cycles_input_node.name] = rman_input_node.name

    # now connect up outputs
    if cycles_output_node:
        for input in cycles_output_node.inputs:
            convert_cycles_input(rman_nt, input, rman_output_node, input.name)

    converted_nodes = temp_converted_nodes

    # rename nodes in node_group
    for node in rman_nt.nodes:
        node.name = rman_nt.name + '.' + node.name

    # convert the inputs to the group
    for input in cycles_node.inputs:
        convert_cycles_input(nt, input, rman_node, input.name)

    return


def convert_bump_node(nt, cycles_node, rman_node):
    convert_cycles_input(nt, cycles_node.inputs[
                         'Strength'], rman_node, 'scale')
    convert_cycles_input(nt, cycles_node.inputs[
                         'Height'], rman_node, 'inputBump')
    convert_cycles_input(nt, cycles_node.inputs['Normal'], rman_node, 'inputN')
    return


def convert_normal_map_node(nt, cycles_node, rman_node):
    convert_cycles_input(nt, cycles_node.inputs[
                         'Strength'], rman_node, 'bumpScale')
    convert_cycles_input(nt, cycles_node.inputs[
                         'Color'], rman_node, 'inputRGB')
    return


def convert_rgb_node(nt, cycles_node, rman_node):
    rman_node.inputRGB = cycles_node.outputs[0].default_value[:3]
    return


def convert_node_value(nt, cycles_node, rman_node):
    rman_node.floatInput1 = cycles_node.outputs[0].default_value
    rman_node.expression = 'floatInput1'
    return


def convert_ramp_node(nt, cycles_node, rman_node):
    convert_cycles_input(nt, cycles_node.inputs['Fac'], rman_node, 'splineMap')
    actual_ramp = bpy.data.node_groups[rman_node.node_group].nodes[0]
    actual_ramp.color_ramp.interpolation = cycles_node.color_ramp.interpolation

    elms = actual_ramp.color_ramp.elements

    e = cycles_node.color_ramp.elements[0]
    elms[0].alpha = e.alpha
    elms[0].position = e.position
    elms[0].color = e.color

    e = cycles_node.color_ramp.elements[-1]
    elms[-1].alpha = e.alpha
    elms[-1].position = e.position
    elms[-1].color = e.color

    for e in cycles_node.color_ramp.elements[1:-1]:
        new_e = actual_ramp.color_ramp.elements.new(e.position)
        new_e.alpha = e.alpha
        new_e.color = e.color

    return

math_map = {
    'ADD': 'floatInput1 + floatInput2',
    'SUBTRACT': 'floatInput1 - floatInput2',
    'MULTIPLY': 'floatInput1 * floatInput2',
    'DIVIDE': 'floatInput1 / floatInput2',
    'SINE': 'sin(floatInput1)',
    'COSINE': 'cos(floatInput1)',
    'TANGENT': 'tan(floatInput1)',
    'ARCSINE': 'asin(floatInput1)',
    'ARCCOSINE': 'acos(floatInput1)',
    'ARCTANGENT': 'atan(floatInput1)',
    'POWER': 'floatInput1 ^ floatInput2',
    'LOGARITHM': 'log(floatInput1)',
    'MINIMUM': 'floatInput1 < floatInput2 ? floatInput1 : floatInput2',
    'MAXIMUM': 'floatInput1 > floatInput2 ? floatInput1 : floatInput2',
    'ROUND': 'round(floatInput1)',
    'LESS_THAN': 'floatInput1 < floatInput2',
    'GREATER_THAN': 'floatInput1 < floatInput2',
    'MODULO': 'floatInput1 % floatInput2',
    'ABSOLUTE': 'abs(floatInput1)',
}


def convert_math_node(nt, cycles_node, rman_node):
    convert_cycles_input(nt, cycles_node.inputs[0], rman_node, 'floatInput1')
    convert_cycles_input(nt, cycles_node.inputs[1], rman_node, 'floatInput2')

    op = cycles_node.operation
    clamp = cycles_node.use_clamp
    expr = math_map[op]
    if clamp:
        expr = 'clamp((%s), 0, 1)' % expr
    rman_node.expression = expr

    return

# this needs a special case to init the stuff


def convert_rgb_curve_node(nt, cycles_node, rman_node):
    for input in cycles_node.inputs:
        convert_cycles_input(nt, input, rman_node, input.name)

    rman_node.mapping.initialize()
    for i, mapping in cycles_node.mapping.curves.items():
        #    new_map = rman_node.mapping.curves.new()
        new_map = rman_node.mapping.curves[i]
        for p in mapping.points:
            new_map.points.new(p.location[0], p.location[1])
    return


def copy_cycles_node(nt, cycles_node, rman_node):
    #print("copying %s node" % cycles_node.bl_idname)
    # TODO copy props
    for input in cycles_node.inputs:
        convert_cycles_input(nt, input, rman_node, input.name)
    return

#########  BSDF conversion methods  ############


def convert_diffuse_bsdf(nt, node, rman_node):
    inputs = node.inputs
    setattr(rman_node, 'enableDiffuse', True)
    setattr(rman_node, 'diffuseGain', 1.0)
    convert_cycles_input(nt, inputs['Color'], rman_node, "diffuseColor")
    convert_cycles_input(nt, inputs['Roughness'],
                         rman_node, "diffuseRoughness")
    convert_cycles_input(nt, inputs['Normal'], rman_node, "diffuseBumpNormal")


def convert_glossy_bsdf(nt, node, rman_node):
    inputs = node.inputs
    lobe_name = "Specular" if rman_node.plugin_name == 'ArnoldLayer' else "PrimarySpecular"
    setattr(rman_node, 'enable' + lobe_name, True)
    if rman_node.plugin_name == 'ArnoldLayer':
        setattr(rman_node, 'specularGain', 1.0)
    # if spec_lobe == 'specular':
    #    setattr(rman_node, spec_lobe + 'FresnelMode', '1')
    convert_cycles_input(
        nt, inputs['Color'], rman_node, "specularEdgeColor")
    convert_cycles_input(
        nt, inputs['Color'], rman_node, "specularFaceColor")
    convert_cycles_input(
        nt, inputs['Roughness'], rman_node, "specularRoughness")
    convert_cycles_input(
        nt, inputs['Normal'], rman_node, "specularBumpNormal")

    if type(node).__class__ == 'ShaderNodeBsdfAnisotropic':
        convert_cycles_input(
            nt, inputs['Anisotropy'], rman_node, "specularAnisotropy")


def convert_glass_bsdf(nt, node, rman_node):
    inputs = node.inputs
    enable_param_name = 'enableRR' if \
        rman_node.plugin_name == 'ArnoldLayer' else 'enableGlass'
    setattr(rman_node, enable_param_name, True)
    param_prefix = 'rrR' if rman_node.plugin_name == 'ArnoldLayer' else \
        'r'
    setattr(rman_node, param_prefix + 'efractionGain', 1.0)
    setattr(rman_node, param_prefix + 'eflectionGain', 1.0)
    convert_cycles_input(nt, inputs['Color'],
                         rman_node, param_prefix + 'efractionColor')
    param_prefix = 'rr' if rman_node.plugin_name == 'ArnoldLayer' else \
        'glass'
    convert_cycles_input(nt, inputs['Roughness'],
                         rman_node, param_prefix + 'Roughness')
    convert_cycles_input(nt, inputs['IOR'],
                         rman_node, param_prefix + 'Ior')


def convert_refraction_bsdf(nt, node, rman_node):
    inputs = node.inputs
    enable_param_name = 'enableRR' if \
        rman_node.plugin_name == 'ArnoldLayer' else 'enableGlass'
    setattr(rman_node, enable_param_name, True)
    param_prefix = 'rrR' if rman_node.plugin_name == 'ArnoldLayer' else \
        'r'
    setattr(rman_node, param_prefix + 'efractionGain', 1.0)
    convert_cycles_input(nt, inputs['Color'],
                         rman_node, param_prefix + 'efractionColor')
    param_prefix = 'rr' if rman_node.plugin_name == 'ArnoldLayer' else \
        'glass'
    convert_cycles_input(nt, inputs['Roughness'],
                         rman_node, param_prefix + 'Roughness')
    convert_cycles_input(nt, inputs['IOR'],
                         rman_node, param_prefix + 'Ior')


def convert_transparent_bsdf(nt, node, rman_node):
    inputs = node.inputs
    enable_param_name = 'enableRR' if \
        rman_node.plugin_name == 'ArnoldLayer' else 'enableGlass'
    setattr(rman_node, enable_param_name, True)
    param_prefix = 'rrR' if rman_node.plugin_name == 'ArnoldLayer' else \
        'r'
    setattr(rman_node, param_prefix + 'efractionGain', 1.0)
    convert_cycles_input(nt, inputs['Color'],
                         rman_node, param_prefix + 'efractionColor')
    param_prefix = 'rr' if rman_node.plugin_name == 'ArnoldLayer' else \
        'glass'
    setattr(rman_node, param_prefix + 'Roughness', 0.0)
    setattr(rman_node, param_prefix + 'Ior', 1.0)


def convert_translucent_bsdf(nt, node, rman_node):
    inputs = node.inputs
    enable = 'enableSinglescatter' if rman_node.plugin_name == 'ArnoldLayer' else \
        'enableSingleScatter'
    setattr(rman_node, enable, True)
    setattr(rman_node, 'singlescatterGain', 1.0)
    setattr(rman_node, 'singlescatterMfpColor', [1.0, 1.0, 1.0])
    convert_cycles_input(nt, inputs['Color'], rman_node, "singlescatterColor")


def convert_sss_bsdf(nt, node, rman_node):
    inputs = node.inputs
    setattr(rman_node, 'enableSubsurface', True)
    convert_cycles_input(nt, inputs['Color'], rman_node, "subsurfaceColor")
    convert_cycles_input(nt, inputs['Radius'],
                         rman_node, "subsurfaceDmfpColor")
    convert_cycles_input(nt, inputs['Scale'], rman_node, "subsurfaceDmfp")


def convert_velvet_bsdf(nt, node, rman_node):
    inputs = node.inputs
    setattr(rman_node, 'enableFuzz', True)
    setattr(rman_node, 'fuzzGain', 1.0)
    convert_cycles_input(nt, inputs['Color'], rman_node, "fuzzColor")
    convert_cycles_input(
        nt, inputs['Normal'], rman_node, "fuzzBumpNormal")


bsdf_map = {
    'ShaderNodeBsdfDiffuse': ('diffuse', convert_diffuse_bsdf),
    'ShaderNodeBsdfGlossy': ('specular', convert_glossy_bsdf),
    'ShaderNodeBsdfAnisotropic': ('specular', convert_glossy_bsdf),
    'ShaderNodeBsdfGlass': ('glass', convert_glass_bsdf),
    'ShaderNodeBsdfRefraction': ('glass', convert_refraction_bsdf),
    'ShaderNodeBsdfTransparent': ('glass', convert_transparent_bsdf),
    'ShaderNodeBsdfTranslucent': ('singlescatter', convert_translucent_bsdf),
    'ShaderNodeBsdfVelvet': ('fuzz', convert_velvet_bsdf),
    'ShaderNodeSubsurfaceScattering': ('subsurface', convert_sss_bsdf),
    'ShaderNodeBsdfHair': (None, None),
    'ShaderNodeEmission': (None, None),
    'ShaderNodeGroup': (None, None)
}

# we only convert the important shaders, all others are copied from cycles osl
node_map = {
    'ShaderNodeTexImage': ('ArnoldTexture', convert_tex_image_node),
    'ShaderNodeMixRGB': ('ArnoldBlend', convert_mix_rgb_node),
    'ShaderNodeNormalMap': ('ArnoldNormalMap', convert_normal_map_node),
    'ShaderNodeGroup': ('ArnoldNodeGroup', convert_node_group),
    'ShaderNodeBump': ('ArnoldBump', convert_bump_node),
    'ShaderNodeValToRGB': ('ArnoldRamp', convert_ramp_node),
    'ShaderNodeMath': ('ArnoldSeExpr', convert_math_node),
    'ShaderNodeRGB': ('ArnoldHSL', convert_rgb_node),
    'ShaderNodeValue': ('ArnoldSeExpr', convert_node_value),
    #'ShaderNodeRGBCurve': ('copy', copy_cycles_node),
}
