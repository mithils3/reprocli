#!/usr/bin/env python3
"""Convert CFF OpenType to TrueType outlines (Chromium's PDF writer embeds CFF as Type 3)."""
import sys
from fontTools.ttLib import TTFont, newTable
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.ttGlyphPen import TTGlyphPen

def convert(src, dst, max_err=1.0):
    f = TTFont(src)
    assert f.sfntVersion == "OTTO" and "CFF " in f
    gs = f.getGlyphSet()
    order = f.getGlyphOrder()
    glyf = newTable("glyf"); glyf.glyphOrder = order; glyf.glyphs = {}
    for name in order:
        tp = TTGlyphPen(gs)
        gs[name].draw(Cu2QuPen(tp, max_err, reverse_direction=True))
        glyf.glyphs[name] = tp.glyph()
    f["glyf"] = glyf
    f["loca"] = newTable("loca")
    hmtx = f["hmtx"]
    for name, g in glyf.glyphs.items():
        g.recalcBounds(glyf)
        hmtx[name] = (hmtx[name][0], getattr(g, "xMin", 0))
    maxp = newTable("maxp"); maxp.tableVersion = 0x00010000
    for k in ("maxZones", "maxTwilightPoints", "maxStorage", "maxFunctionDefs", "maxInstructionDefs",
              "maxStackElements", "maxSizeOfInstructions", "maxComponentElements", "maxComponentDepth",
              "maxPoints", "maxContours", "maxCompositePoints", "maxCompositeContours"):
        setattr(maxp, k, 0)
    maxp.maxZones = 1
    f["maxp"] = maxp
    post = f["post"]; post.formatType = 2.0; post.extraNames = []; post.mapping = {}; post.glyphOrder = order
    del f["CFF "]
    for t in ("VORG",):
        if t in f: del f[t]
    f.sfntVersion = "\x00\x01\x00\x00"
    f.save(dst)

if __name__ == "__main__":
    for src, dst in zip(sys.argv[1::2], sys.argv[2::2]):
        convert(src, dst); print("wrote", dst)
