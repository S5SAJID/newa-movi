from video.quotes.blur_quotes import create_blur_quote_video

for status in create_blur_quote_video(render_video=False, watermark_text_string="@s5sajid", video_fps=12, bg_clip_query="lofi aesthetic clips"):
    print(status)