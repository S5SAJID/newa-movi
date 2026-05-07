from proglog import ProgressBarLogger


class CustomHaloLogger(ProgressBarLogger):
    def __init__(self, spinner):
        super().__init__()
        self.spinner = spinner

    def bars_callback(self, bar, attr, value, old_value=None):
        # MoviePy sometimes uses 't' or 'chunk'. This grabs whichever is active.
        try:
            bar_dict = self.bars.get(bar)
            if bar_dict:
                total = bar_dict.get('total')
                if total and total > 0:
                    percentage = (value / total) * 100
                    # Update the Halo text in place
                    self.spinner.text = f"Rendering... {percentage:.1f}%"
        except Exception:
            pass