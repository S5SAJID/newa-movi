from video.quotes.blur_quotes import create_blur_quote_video

for status in create_blur_quote_video(render_video=False, watermark_text_string="@s5sajid", subclip=(1,5), video_fps=5):
    print(status)