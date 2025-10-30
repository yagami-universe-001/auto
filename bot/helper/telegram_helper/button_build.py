from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup


class ButtonMaker:
    def __init__(self):
        self.buttons = []
        self.header_buttons = []
        self.body_buttons = []
        self.file_buttons = []
        self.footer_buttons = []
        self.main_buttons = []

    def url(self, text, url, position=None):
        button = InlineKeyboardButton(text=text, url=url)
        if position == "header":
            self.header_buttons.append(button)
        elif position == "footer":
            self.footer_buttons.append(button)
        elif position == 'extra':
            self.buttons.append(button)
        else:
            self.main_buttons.append(button)

    def callback(self, text, callback_data, position=None):
        button = InlineKeyboardButton(text=text, callback_data=callback_data)
        if position == "header":
            self.header_buttons.append(button)
        elif position == "footer":
            self.footer_buttons.append(button)
        elif position == "files":
            self.file_buttons.append(button)
        elif position == "body":
            self.body_buttons.append(button)
        elif position == 'extra':
            self.buttons.append(button)
        else:
            self.main_buttons.append(button)

    def add_button(self, text, callback_data=None, url=None):
        """Add a single button."""
        if url != None:
            self.buttons.append([InlineKeyboardButton(text, url=url)])
        elif callback_data != None:
            self.buttons.append([InlineKeyboardButton(text, callback_data=callback_data)])
    
    def add_row(self, buttons_list):
        row = []
        for text, callback_data_or_url in buttons_list:
            if callback_data_or_url.startswith('http://') or callback_data_or_url.startswith('https://'):
                # If the callback_data_or_url is a URL, create a button with a URL
                button = InlineKeyboardButton(text=text, url=callback_data_or_url)
            else:
                # Otherwise, treat it as callback data
                button = InlineKeyboardButton(text=text, callback_data=callback_data_or_url)
            row.append(button)
        self.buttons.append(row)


    def build_one_button_per_row(self):
        """Create InlineKeyboardMarkup with one button per row."""
        keyboard = [[button] for button in self.buttons]  # Place each button in its own list
        return InlineKeyboardMarkup(keyboard)
    
    def build(self):
        """Return InlineKeyboardMarkup with all buttons."""
        return InlineKeyboardMarkup(self.buttons)

    def column(self, main_columns=1, header_columns=8, footer_columns=8, extra_columns=1):
        keyboard = [
            self.main_buttons[i : i + main_columns]
            for i in range(0, len(self.main_buttons), main_columns)
        ]

        if self.header_buttons:
            if len(self.header_buttons) > header_columns:
                header_chunks = [
                    self.header_buttons[i : i + header_columns]
                    for i in range(0, len(self.header_buttons), header_columns)
                ]
                keyboard = header_chunks + keyboard
            else:
                keyboard.insert(0, self.header_buttons)
        
        # Handle extra buttons based on extra_columns
        if self.buttons:
            if len(self.buttons) > extra_columns:
                extra_chunks = [
                    self.buttons[i : i + extra_columns]
                    for i in range(0, len(self.buttons), extra_columns)
                ]
                keyboard += extra_chunks
            else:
                keyboard.append(self.buttons)

        if self.footer_buttons:
            if len(self.footer_buttons) > footer_columns:
                footer_chunks = [
                    self.footer_buttons[i : i + footer_columns]
                    for i in range(0, len(self.footer_buttons), footer_columns)
                ]
                keyboard += footer_chunks
            else:
                keyboard.append(self.footer_buttons)

        # Return as InlineKeyboardMarkup
        return InlineKeyboardMarkup(keyboard)
    
    def build_filter_menu(self):
        keyboard = []

        # First row
        if self.header_buttons:
            keyboard.append(self.header_buttons)

        # Second row
        if self.body_buttons:
            keyboard.append(self.body_buttons)

        # File buttons
        if self.file_buttons:
            keyboard.extend([self.file_buttons[i:i + 1] for i in range(0, len(self.file_buttons))])

        if self.buttons:
            keyboard.append(self.buttons)

        # Footer row
        if self.footer_buttons:
            keyboard.append(self.footer_buttons)

        return InlineKeyboardMarkup(keyboard)