#include "stdafx.h"

#include <stdio.h>

AI_SHADER_NODE_EXPORT_METHODS(methods);

enum BlendType
{
	BLEND_MIX,
	BLEND_MUL,
	BLEND_SCREEN
};

enum ShaderParams
{
	P_COLOR_1,
	P_COLOR_2,
	P_BLEND,
	P_FACTOR
};

node_parameters
{
	printf("node_parameters\n");

	AiParameterRGBA("color1", 0, 0, 0, 1);
	AiParameterRGBA("color2", 1, 1, 1, 1);
	AiParameterUInt("blend", 0);
	AiParameterFlt("factor", 0.5f);
}

node_initialize
{
	printf("node_initialize\n");
}

node_update
{
	printf("node_update\n");
}

node_finish
{
	printf("node_finish\n");
}

shader_evaluate
{
	AtRGBA c1 = AiShaderEvalParamRGBA(P_COLOR_1);
	AtRGBA c2 = AiShaderEvalParamRGBA(P_COLOR_2);
	int blend = AiShaderEvalParamUInt(P_BLEND);
	float factor = AiShaderEvalParamFlt(P_FACTOR);
	//printf("shader_evaluate %d %f\n", blend, factor);
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
	printf("node_loader\n");
	if (i > 0)
		return false;

	node->node_type = AI_NODE_SHADER;
	node->output_type = AI_TYPE_RGBA;
	node->name = "ba:blend";
	node->methods = methods;
	strcpy(node->version, AI_VERSION);
	return true;
}
