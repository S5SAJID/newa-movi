from moviepy import TextClip, ColorClip, CompositeVideoClip

main_color = (0,220,0)
text_color = (
    main_color[0] + 255 if main_color[0] < 255 else 0,
    main_color[1] + 255 if main_color[1] < 255 else 0,
    main_color[2] + 255 if main_color[2] < 255 else 0,
)

print(text_color)

text = TextClip(text="""اچانک نہیں بچھڑا وہ مجھ سے مرشد
میں نے ہی چلغوزے مانگ لیے تھے
""", font_size=40, font="NotoNastaliqUrdu-Regular.ttf", color=text_color)
bg = ColorClip(color=main_color, size=(500,500))

video = CompositeVideoClip([bg, text])
video.save_frame("preview.png", t=1)
