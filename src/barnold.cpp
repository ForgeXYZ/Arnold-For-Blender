#include "stdafx.h"

#include <stdio.h>

AI_SHADER_NODE_EXPORT_METHODS(methods);

enum BlendType
{
	BLEND_MIX,
	BLEND_MUL,
	BLEND_SCREEN
};

enum BlendParams
{
	P_COLOR_1,
	P_COLOR_2,
	P_BLEND,
	P_FACTOR
};

static const char* BlendNames[] =
{
	"blend",
	"multiply",
	"screen",
	NULL
};

node_parameters
{
	AiParameterRGBA("color1", 0, 0, 0, 1);
	AiParameterRGBA("color2", 1, 1, 1, 1);
	AiParameterENUM("blend", 0, BlendNames);
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
	AtRGBA c1 = AiShaderEvalParamRGBA(P_COLOR_1);
	AtRGBA c2 = AiShaderEvalParamRGBA(P_COLOR_2);
	int blend = AiShaderEvalParamUInt(P_BLEND);
	float factor = AiShaderEvalParamFlt(P_FACTOR);
	switch (blend)
	{
	case BLEND_MIX:
		sg->out.RGBA = (c1 * factor) + (c2 * (1.0f - factor));
		break;
	case BLEND_MUL:
		sg->out.RGBA = (c1 * factor + (1.0f - factor)) * c2;
		break;
	case BLEND_SCREEN:
		sg->out.RGBA = 1.0f - (1.0f - c1 * factor) * (1.0f - c2);
		break;
	}
}

node_loader
{
	if (i > 0)
		return false;

	node->node_type = AI_NODE_SHADER;
	node->output_type = AI_TYPE_RGBA;
	node->name = "barnold:blend";
	node->methods = methods;
	strcpy(node->version, AI_VERSION);
	return true;
}
