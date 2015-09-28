#include "stdafx.h"

AI_SHADER_NODE_EXPORT_METHODS(BlendMethods);

enum BlendParams
{
	P_BLEND,
	P_COLOR_1,
	P_COLOR_2,
	P_FACTOR
};

enum BlendTypes
{
	BLEND_MIX,
	BLEND_ADD,
	BLEND_MUL,
	BLEND_SCREEN
};

static const char* BlendNames[] =
{
	"mix",
	"add",
	"multiply",
	"screen",
	NULL
};

node_parameters
{
	AiParameterENUM("blend", 0, BlendNames);
	AiParameterRGB("color1", 0, 0, 0);
	AiParameterRGB("color2", 1, 1, 1);
	AiParameterFlt("factor", 0.5f);
}

node_initialize
{
}

node_update
{
}

node_finish
{
}

shader_evaluate
{
	AtRGB c1 = AiShaderEvalParamRGB(P_COLOR_1);
	AtRGB c2 = AiShaderEvalParamRGB(P_COLOR_2);
	float f = AiShaderEvalParamFlt(P_FACTOR);
	BlendParams blend = static_cast<BlendParams>(AiShaderEvalParamEnum(P_BLEND));
#if 1
	// <blender sources>/source/blender/render/intern/source/render_texture.c:1349
	// <blender sources>/source/blender/blenkernel/intern/material.c:1516
	switch (blend)
	{
	case BLEND_MIX:
		sg->out.RGB = (c1 * (1.0f - f)) + (c2 * f);
		break;
	case BLEND_ADD:
		sg->out.RGB = c1 + (c2 * f);
		break;
	case BLEND_MUL:
		sg->out.RGB = c1 * ((c2 - 1) * f + 1.0f);
		break;
	case BLEND_SCREEN:
		sg->out.RGB = 1.0f - (1.0f - c1) * (1.0f - f * c2);
		break;
	}
#else
	// https://en.wikipedia.org/wiki/Blend_modes
	c1 *= 1.0f - f;
	c2 *= factor;
	switch (blend)
	{
	case BLEND_MIX:
		sg->out.RGB = c1 + c2;
		break;
	case BLEND_MUL:
		sg->out.RGB = c1 * c2;
		break;
	case BLEND_SCREEN:
		sg->out.RGB = 1.0f - (1.0f - c1) * (1.0f - c2);
		break;
	}
#endif
}

node_loader
{
	if (i > 0)
		return false;

	node->node_type = AI_NODE_SHADER;
	node->output_type = AI_TYPE_RGB;
	node->name = "BarnoldMixRGB";
	node->methods = BlendMethods;
	strcpy(node->version, AI_VERSION);
	return true;
}
