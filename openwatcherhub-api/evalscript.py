from pyjsparser import parse
import copy
import json
import math
import numpy as np


### BUILTINS

def unpack(clr):
    return [
        ((clr >> 16) & 0xff) / 255.0, 
        ((clr >> 8) & 0xff) / 255.0, 
        (clr & 0xff) / 255.0
    ]

class ColorMapVisualizer:
    def __init__(self, map):
        self.map = map

    @classmethod
    def createDefaultColorMap(cls):
        return ColorMapVisualizer([
            [-1.0, 0x000000],
            [-0.2, 0xff0000],
            [-0.1, 0x9a0000],
            [0.0, 0x660000],
            [0.1, 0xffff33],
            [0.2, 0xcccc33],
            [0.3, 0x666600],
            [0.4, 0x33ffff],
            [0.5, 0x33cccc],
            [0.6, 0x006666],
            [0.7, 0x33ff33],
            [0.8, 0x33cc33],
            [0.9, 0x006600]
        ])

    # TODO: vectorize
    def process(self, value):
        cur = self.map[0]
        for val in self.map:
            if value >= val[0]:
                cur = val
        return unpack(cur[1])

whiteGreen = [
  [1.000, 0x000000],
  [0.600, 0x006600],
  [0.300, 0x80B300],
  [0.000, 0xFFFFFF]
]

redTemperature = [
  [1.000, 0x000000],
  [0.525, 0xAE0000],
  [0.300, 0xFF6E00],
  [0.250, 0xFF8600],
  [0.000, 0xFFFFFF]
]

blueRed = [
  [1.000, 0x000080],
  [0.875, 0x0000FF],
  [0.625, 0x00FFFF],
  [0.375, 0xFFFF00],
  [0.125, 0xFF0000],
  [0.000, 0x800000]
]

class ColorGradientVisualizer:
    def __init__(self, pairs, minVal, maxVal):
        self.pairs = pairs
        self.minVal = minVal
        self.maxVal = maxVal
        self.denom = maxVal - minVal

    def process(self, val):
        if isinstance(val, np.ndarray):
            return self._process_vec(val)
        else:
            return self._process_val(val)

    def _process_vec(self, val):
        rescaled_val = 1 - ((val - self.minVal) / self.denom)
        # turn result into 3d array
        output = np.stack([rescaled_val, rescaled_val, rescaled_val])
        int_from = self.pairs[0]
        int_to = self.pairs[0]
        for pair in self.pairs:
            int_to = pair
            clr_from = unpack(int_from[1])
            clr_to = unpack(int_to[1])
            fraction = np.where(int_to[0] == int_from[0], 1, (int_from[0] - rescaled_val) / (int_from[0] - int_to[0]) )
            output = np.where((rescaled_val > pair[0]) & (rescaled_val <= int_from[0]), [
                (clr_to[0] - clr_from[0]) * fraction + clr_from[0],
                (clr_to[1] - clr_from[1]) * fraction + clr_from[1],
                (clr_to[2] - clr_from[2]) * fraction + clr_from[2],
            ], output)
            int_from = pair
        return output

    def _process_val(self, val):
        rescaled_val = 1 - ((val - self.minVal) / self.denom)
        int_from = self.pairs[0]
        int_to = self.pairs[0]
        for pair in self.pairs:
            if rescaled_val <= pair[0]:
                int_from = pair
                int_to = pair
            else:
                int_to = pair
                break
        fraction = 1 if int_to[0] == int_from[0] else (int_from[0] - rescaled_val) / (int_from[0] - int_to[0])
        clr_from = unpack(int_from[1])
        clr_to = unpack(int_to[1])
        return [
            (clr_to[0] - clr_from[0]) * fraction + clr_from[0],
            (clr_to[1] - clr_from[1]) * fraction + clr_from[1],
            (clr_to[2] - clr_from[2]) * fraction + clr_from[2],
        ]
    
    @classmethod
    def createWhiteGreen(cls, minVal, maxVal):
        return ColorGradientVisualizer(whiteGreen, minVal, maxVal)
    
    @classmethod
    def createBlueRed(cls, minVal, maxVal):
        return ColorGradientVisualizer(blueRed, minVal, maxVal)
    
    @classmethod
    def createRedTemperature(cls, minVal, maxVal):
        return ColorGradientVisualizer(redTemperature, minVal, maxVal)

SCRIPT_ENV = {
    "ColorGradientVisualizer": ColorGradientVisualizer,
    "ColorMapVisualizer": ColorMapVisualizer,
    "Math": math,
    "Vec": np,
}

class ParseCtx:
    indent = 0
    block = False


def compile(script: str):
    prg = parse(script)
    #print(json.dumps(prg, indent=2))

    py_src = parse_ast(prg, ParseCtx())
    #print(py_src)

    try:
        module_env = {**SCRIPT_ENV}
        exec(py_src, module_env)
        return module_env
    except:
        raise

def parse_ast(ast, parent_ctx: ParseCtx) -> str:
    ctx = copy.deepcopy(parent_ctx)
    pad = " " * ctx.indent
    match ast:
        case {"type": "Program"}:
            return "" + "\n".join(parse_ast(elem, ctx) for elem in ast["body"])
        case {"type": "FunctionDeclaration"}:
            ctx.indent = 4
            return pad + f"def {parse_ast(ast['id'], ctx)}({', '.join(parse_ast(p, ctx) for p in ast['params'])}):\n" + parse_ast(ast['body'], ctx) + "\n\n"
        case {"type": "BlockStatement"}:
            ctx.block = True
            return "\n".join(parse_ast(elem, ctx) for elem in ast["body"])
        case {"type": "ReturnStatement"}:
            return pad + "return " + parse_ast(ast["argument"], ctx)
        case {"type": "ObjectExpression"}:
            ctx.indent += 2
            return "{" + ", ".join(parse_ast(elem, ctx) for elem in ast["properties"]) + "}"
        case {"type": "Property"}:
            return f"\"{parse_ast(ast['key'], ctx)}\": " + parse_ast(ast['value'], ctx)
        case {"type": "ArrayExpression"}:
            return "[" + ", ".join(parse_ast(elem, ctx) for elem  in ast['elements']) + "]"
        case {"type": "Literal"}:
            return ast["raw"]
        case {"type": "Identifier"}:
            return ast["name"]
        case {"type": "VariableDeclaration"}:
            vars = {}
            for decl in ast["declarations"]:
                vars[parse_ast(decl['id'], ctx)] = parse_ast(decl["init"], ctx)
            keys = []
            exprs = []
            for (key, expr) in vars.items():
                keys.append(key)
                exprs.append(expr)
            return pad + ", ".join(keys) + " = " + ", ".join(exprs)
        case {"type": "MemberExpression"}:
            if ast["computed"]:
                return parse_ast(ast["object"], ctx) + "[" + parse_ast(ast["property"], ctx) + "]"
            else:
                return parse_ast(ast["object"], ctx) + "." + parse_ast(ast["property"], ctx)
        case {"type": "CallExpression"}:
            return parse_ast(ast["callee"], ctx) + "(" + ", ".join(parse_ast(arg, ctx) for arg in ast['arguments']) + ")"
        case {"type": "UnaryExpression"}:
            return ast["operator"] + parse_ast(ast['argument'], ctx)
        case {"type": "BinaryExpression"}:
            return "(" + parse_ast(ast["left"], ctx) + f" {ast['operator']} " + parse_ast(ast["right"], ctx) + ")"
        case {"type": "EmptyStatement"}:
            return ""
        case {"type": "ExpressionStatement"}:
            return pad + parse_ast(ast["expression"], ctx)
        case {"type": "AssignmentExpression"}:
            return parse_ast(ast["left"], ctx) + " = " + parse_ast(ast["right"], ctx)
        case {"type": "ConditionalExpression"}:
            return parse_ast(ast["consequent"], ctx) + " if " + parse_ast(ast["test"], ctx) + " else " + parse_ast(ast["alternate"], ctx)
        case _:
            return "UNDEFINED"
        

if __name__ == "__main__":
    #print(unpack(0xffff00))

    mapper = ColorMapVisualizer.createDefaultColorMap()
    #print(mapper.process(0.4))

    print("greenwhite")

    viz = ColorGradientVisualizer.createWhiteGreen(0, 1)
    print(viz.process(0))
    print(viz.process(0.3))
    print(viz.process(0.5))
    print(viz.process(0.8))
    print(viz.process(1))

    print("red temp")
    viz = ColorGradientVisualizer.createRedTemperature(0, 1)
    print(viz.process(0.0))
    print(viz.process(0.3))
    print(viz.process(0.5))
    print(viz.process(0.8))
    print(viz.process(1.0))
    
