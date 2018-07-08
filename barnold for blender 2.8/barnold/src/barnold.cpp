#include "stdafx.h"
#include "blend.h"

AI_SHADER_NODE_EXPORT_METHODS(BlendMethods);

node_parameters
{
	AiParameterENUM("blend", 0, blend::names);
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
	blend::MODES mode = static_cast<blend::MODES>(AiShaderEvalParamEnum(blend::P_BLEND));
	AtRGB c1 = AiShaderEvalParamRGB(blend::P_COLOR_1);
	AtRGB c2 = AiShaderEvalParamRGB(blend::P_COLOR_2);
	float f = AiShaderEvalParamFlt(blend::P_FACTOR);
	blend::blend(sg->out.RGB, c1, c2, f, mode);
}

node_loader
{
	if (i > 0)
		return false;

	node->node_type = AI_NODE_SHADER;
	node->output_type = AI_TYPE_RGB;
	node->name = "BArnoldMixRGB";
	node->methods = BlendMethods;
	strcpy(node->version, AI_VERSION);
	return true;
}
