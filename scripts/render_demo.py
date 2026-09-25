#!/usr/bin/env python3
"""Render an illustrated README demo without recording the user's desktop.

Requires Pillow, DejaVu Sans, and Noto Sans CJK. The curious entry is a
snapshot from the pinned ECDICT dictionary. Run: python3 scripts/render_demo.py
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

DESTINATION = Path(__file__).resolve().parents[1] / "docs" / "assets"
REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
CJK = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"


def font(size, bold=False, chinese=False):
    return ImageFont.truetype(CJK if chinese else BOLD if bold else REGULAR, size)


def text(draw, xy, value, size=20, fill="#23334b", **kwargs):
    draw.text(xy, value, font=font(size, **kwargs), fill=fill, anchor="lt")


def smooth(value):
    value = max(0, min(1, value))
    return value * value * (3 - 2 * value)


def cursor(draw, x, y):
    points = [(x,y),(x,y+28),(x+7,y+22),(x+14,y+36),
              (x+20,y+33),(x+13,y+19),(x+24,y+19)]
    draw.polygon(points, fill="#17283f", outline="white", width=2)


def render(t):
    image = Image.new("RGB", (1040, 640), "#eef3f8")
    d = ImageDraw.Draw(image)
    d.rounded_rectangle((48,40,108,100),17,fill="#2160d5")
    text(d,(62,48),"点",35,fill="white",chinese=True)
    text(d,(125,42),"DianYi",34,bold=True)
    text(d,(125,85),"Double-click English. Read Chinese.",21,fill="#52637a")
    d.rounded_rectangle((826,53,990,91),19,fill="#dcece5")
    d.ellipse((843,68,851,76),fill="#258160")
    text(d,(862,64),"100% offline",16,fill="#24664e",bold=True)
    d.rounded_rectangle((48,171,992,548),22,fill="#dce4ee")
    d.rounded_rectangle((48,166,992,541),22,fill="white",outline="#d4deeb",width=1)
    text(d,(86,196),"YOUR EVERYDAY READING",14,fill="#6c7c90",bold=True)
    d.line((86,229,954,229),fill="#e5ebf2",width=1)

    word_x = 86 + d.textlength("Stay ",font=font(36))
    word_width = d.textlength("curious",font=font(36))
    target_x, target_y = word_x + word_width * .55, 281
    if 2.12 <= t < 6.45:
        d.rounded_rectangle((word_x-3,250,word_x+word_width+3,296),5,fill="#c8dcff")
    text(d,(86,255),"Stay curious every day.",36)
    text(d,(86,314),"Keep reading. A word is all it takes.",23,fill="#758297")
    if 2.48 <= t < 6.45:
        px, py = round(target_x+22),310
        d.rounded_rectangle((px+3,py+5,px+547,py+172),13,fill="#dde4ef")
        d.rounded_rectangle((px,py,px+544,py+167),13,fill="#f8faff",outline="#7e9dcb",width=2)
        text(d,(px+22,py+18),"curious",28,bold=True)
        text(d,(px+22,py+58),"/'kjuәriәs/",19,fill="#5e6f88")
        text(d,(px+22,py+104),"a. 好奇的, 求知的, 古怪的",26,chinese=True)

    if t < 1.05:
        cx,cy = 869,487
    elif t < 1.9:
        p=smooth((t-1.05)/.85);cx=869+(target_x-869)*p;cy=487+(target_y-487)*p
    elif t < 5.7:
        cx,cy=target_x,target_y
    else:
        p=smooth((t-5.7)/.65);cx=target_x+(869-target_x)*p;cy=target_y+(487-target_y)*p
    for click_time,x,y in ((1.96,target_x,target_y),(2.2,target_x,target_y),(6.4,869,487)):
        age=t-click_time
        if 0<=age<.24:
            radius=8+19*age/.24
            d.ellipse((x-radius,y-radius,x+radius,y+radius),outline="#3478e5",width=3)
    cursor(d,round(cx),round(cy))
    stage=0 if t<1.9 else 1 if t<2.48 else 2 if t<6.45 else 3
    labels=["Read English","Double-click a word","See Chinese","Click away to close"]
    for i,(x,label) in enumerate(zip((48,278,557,770),labels)):
        active=stage==i
        d.ellipse((x,569,x+27,596),fill="#2160d5" if active else "#dce4ee")
        text(d,(x+8,576),str(i+1),13,fill="white" if active else "#61738c",bold=True)
        text(d,(x+38,575),label,16,fill="#174aab" if active else "#61738c",bold=active)
    text(d,(48,616),"Illustrated demo · ECDICT meanings · Layout varies with display scaling",12,fill="#718197")
    return image


def main():
    DESTINATION.mkdir(parents=True,exist_ok=True)
    poster=render(3.6)
    poster.save(DESTINATION/"double-click-preview.png",optimize=True)
    palette=poster.quantize(colors=128,method=Image.Quantize.MEDIANCUT)
    frames=[render(i/12.5).quantize(palette=palette,dither=Image.Dither.NONE) for i in range(94)]
    path=DESTINATION/"double-click-demo.gif"
    frames[0].save(path,save_all=True,append_images=frames[1:],duration=80,
                   loop=0,optimize=True,disposal=1)
    with Image.open(path) as result:
        print(f"{path}: {result.n_frames} frames, {path.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
