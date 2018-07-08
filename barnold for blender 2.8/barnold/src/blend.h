#pragma once

#ifndef __BLEND_H__
#define __BLEND_H__

/* Blending routines
	<blender sources>/source/blender/render/intern/source/render_texture.c:1349
	<blender sources>/source/blender/blenkernel/intern/material.c:1516
	https://en.wikipedia.org/wiki/Blend_modes (without factor)
*/
namespace blend
{
	enum PARAMS
	{
		P_BLEND,
		P_COLOR_1,
		P_COLOR_2,
		P_FACTOR
	};

	enum MODES
	{
		MIX,
		ADD,
		MULT,
		SCREEN,
		OVERLAY,
		SUB,
		DIV,
		DIFF,
		DARK,
		LIGHT,
		DODGE,
		BURN,
		HUE,
		SAT,
		VAL,
		COLOR,
		SOFT,
		LINEAR
	};

	static const char* names[] =
	{
		"mix",
		"add",
		"multiply",
		"screen",
		"overlay",
		"subtract",
		"divide",
		"difference",
		"darken",
		"lighten",
		"dodge",
		"burn",
		"hue",
		"saturation",
		"value",
		"color",
		"soft",
		"linear",
		NULL
	};

	inline void to_hsv(const AtRGB &rgb, float &h, float &s, float &v)
	{
		float r, g, b, k, chroma;
		if (rgb.g < rgb.b)
		{
			g = rgb.b;
			b = rgb.g;
			k = -1.0f;
		}
		else
		{
			g = rgb.g;
			b = rgb.b;
			k = 0.0f;
		}
		if (rgb.r < g)
		{
			r = g;
			g = rgb.r;
			k = -2.0f / 6.0f - k;
			chroma = r - min(g, b);
		}
		else
		{
			r = rgb.r;
			chroma = r - b;
		}
		h = fabsf(k + (g - b) / (6.0f * chroma + 1e-20f));
		s = chroma / (r + 1e-20f);
		v = r;
	}

	inline void from_hsv(AtRGB &out, float h, float s, float v)
	{
		float r, g, b;
		r = fabsf(h * 6.0f - 3.0f) - 1.0f;
		g = 2.0f - fabsf(h * 6.0f - 2.0f);
		b = 2.0f - fabsf(h * 6.0f - 4.0f);
		CLAMP(r, 0.0f, 1.0f);
		CLAMP(g, 0.0f, 1.0f);
		CLAMP(b, 0.0f, 1.0f);
		out.r = ((r - 1.0f) * s + 1.0f) * v;
		out.g = ((g - 1.0f) * s + 1.0f) * v;
		out.b = ((b - 1.0f) * s + 1.0f) * v;
	}

	template <typename T>
	inline void mix(T &out, const T &a, const T &b, float f)
	{
		// (1 - f)*a + f*b
		out = a + (b - a) * f;
	}

	template <typename T>
	inline void add(T &out, const T &a, const T &b, float f)
	{
		// a + f*b
		out = a + b * f;
	}

	template <typename T>
	inline void multiply(T &out, const T &a, const T &b, float f)
	{
		// c1 * ((1 - f) + f*c2)
		out = a * ((b - 1.0f) * f + 1.0f);
	}

	template <typename T>
	inline void screen(T &out, const T &a, const T &b, float f)
	{
		// 1 - (1 - f + f*(1 - b)) * (1 - a)
		// 1 - (1 - b*f) * (1 - a)
		// 1 - (1 - a - b*f + a*b*f)
		// a + b*f - a*b*f
		out = a + (1.0f - a) * b * f;
	}

	template <typename T>
	inline void overlay(T &out, const T &a, const T &b, float f)
	{
		if (a < 0.5f)
			// a * ((1 - f) + 2*f*b)
			out = a * ((2.0f * b - 1.0f) * f + 1.0f);
		else
			// 1 - (1 - f + 2*f*(1 - b)) * (1 - a)
			// 1 - (1 + f*(2*(1 - b) - 1)) * (1 - a)
			// 1 - (1 + f*(1 - 2*b)) * (1 - a)
			// 1 - (1 + f - 2*b*f) * (1 - a)
			// 1 - (1 - a + f - a*f - 2*b*f + 2*a*b*f)
			// a - f + a*f + 2*b*f - 2*a*b*f;
			// a + (a + 2*b - 2*a*b - 1) * f
			out = a + (a + 2.0f * b * (1.0f - a) - 1.0f) * f;
	}

	template <typename T>
	inline void subtract(T &out, const T &a, const T &b, float f)
	{
		// a - f*b
		out = a - b * f;
	}

	template <typename T>
	inline void divide(T &out, const T &a, const T &b, float f)
	{
		if (b)
			// (1 - f) * a + f * a / b
			// (1 - f + f / b) * a
			// (1 + (1/b - 1) * f) * a
			out = a * ((1.0f / b - 1.0f) * f + 1.0f);
		else
			out = a;
	}

	template <typename T>
	inline void difference(T &out, const T &a, const T &b, float f)
	{
		// (1 - f) * a + f * fabsf(a - b)
		out = (1.0f - f) * a + f * fabsf(a - b);
	}

	template <typename T>
	inline void darken(T &out, const T &a, const T &b, float f)
	{
		out = min(a, b) * f + a * (1.0f - f);
	}

	template <typename T>
	inline void lighten(T &out, const T &a, const T &b, float f)
	{
		T t = f * b;
		out = (t > a) ? t : a;
	}

	template <typename T>
	inline void dodge(T &out, const T &a, const T &b, float f)
	{
		if (a)
		{
			T t = 1.0f - f * b;
			if (t <= 0.0f)
				out = 1.0f;
			else
			{
				t = a / t;
				if (t > 1.0f)
					out = 1.0f;
				else
					out = t;
			}
		}
		else
			out = a;
	}

	template <typename T>
	inline void burn(T &out, const T &a, const T &b, float f)
	{
		// 1 - f + f * b;
		T t = (b - 1.0f) * f + 1.0f;
		if (t <= 0.0f)
			out = 0.0f;
		else
		{
			t = 1.0f - (1.0f - a) / t;
			if (t < 0.0f)
				out = 0.0f;
			else if (t > 1.0f)
				out = 1.0f;
			else
				out = t;
		}
	}

	inline void hue(AtRGB &out, const AtRGB &a, const AtRGB &b, float f)
	{
		float cH, cS, cV;
		to_hsv(b, cH, cS, cV);
		if (cS != 0)
		{
			AtRGB t;
			float rH, rS, rV;
			to_hsv(a, rH, rS, rV);
			from_hsv(t, cH, rS, rV);
			out = (1.0f - f) * a + f * t;
		}
		else
			out = a;
	}

	inline void saturation(AtRGB &out, const AtRGB &a, const AtRGB &b, float f)
	{
		float rH, rS, rV;
		to_hsv(a, rH, rS, rV);
		if (rS != 0.0f)
		{
			float cH, cS, cV;
			to_hsv(b, cH, cS, cV);
			from_hsv(out, rH, ((1.0f - f) * rS + f * cS), rV);
		}
		else
			out = a;
	}

	inline void value(AtRGB &out, const AtRGB &a, const AtRGB &b, float f)
	{
		float rH, rS, rV, cH, cS, cV;
		to_hsv(a, rH, rS, rV);
		to_hsv(b, cH, cS, cV);
		from_hsv(out, rH, rS, ((1.0f - f) * rV * f * cV));
	}

	inline void color(AtRGB &out, const AtRGB &a, const AtRGB &b, float f)
	{
		float cH, cS, cV;
		to_hsv(b, cH, cS, cV);
		if (cS != 0.0f)
		{
			AtRGB t;
			float rH, rS, rV;
			to_hsv(b, rH, rS, rV);
			from_hsv(t, cH, cS, rV);
			out = (1.0f - f) * a + f * t;
		}
		out = a;
	}

	template <typename T>
	inline void soft(T &out, const T &a, const T &b, float f)
	{
		T t = 1.0f - (1.0f - a) * (1.0f - b);
		out = (1.0f - f) * a + f * (((1.0f - a) * b * a) + (a * t));
	}

	template <typename T>
	inline void linear(T &out, const T &a, const T &b, float f)
	{
		if (b > 0.5f)
			out = a + f * (2.0f * (b - 0.5f));
		else
			out = a + f * (2.0f * (b - 1.0f));
	}

	inline void blend(AtRGB &out, const AtRGB &a, const AtRGB &b, float f, MODES mode)
	{
		switch (mode)
		{
		case MIX:
			mix(out, a, b, f);
			break;
		case ADD:
			add(out, a, b, f);
			break;
		case MULT:
			multiply(out, a, b, f);
			break;
		case SCREEN:
			screen(out, a, b, f);
			break;
		case OVERLAY:
			overlay(out.r, a.r, b.r, f);
			overlay(out.g, a.g, b.g, f);
			overlay(out.b, a.b, b.b, f);
			break;
		case SUB:
			subtract(out, a, b, f);
			break;
		case DIV:
			divide(out.r, a.r, b.r, f);
			divide(out.g, a.g, b.g, f);
			divide(out.b, a.b, b.b, f);
			break;
		case DARK:
			darken(out.r, a.r, b.r, f);
			darken(out.g, a.g, b.g, f);
			darken(out.b, a.b, b.b, f);
			break;
		case LIGHT:
			lighten(out.r, a.r, b.r, f);
			lighten(out.g, a.g, b.g, f);
			lighten(out.b, a.b, b.b, f);
			break;
		case DODGE:
			dodge(out.r, a.r, b.r, f);
			dodge(out.g, a.g, b.g, f);
			dodge(out.b, a.b, b.b, f);
			break;
		case BURN:
			burn(out.r, a.r, b.r, f);
			burn(out.g, a.g, b.g, f);
			burn(out.b, a.b, b.b, f);
			break;
		case HUE:
			hue(out, a, b, f);
			break;
		case SAT:
			saturation(out, a, b, f);
			break;
		case VAL:
			value(out, a, b, f);
			break;
		case COLOR:
			color(out, a, b, f);
			break;
		case SOFT:
			soft(out, a, b, f);
			break;
		case LINEAR:
			linear(out.r, a.r, b.r, f);
			linear(out.g, a.g, b.g, f);
			linear(out.b, a.b, b.b, f);
			break;
		}
	}
}

#endif // __BLEND_H__