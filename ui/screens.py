"""
screens.py — Mode selection screen shown at application startup.
"""

import tkinter as tk

from ui.theme import (COLORS, _IS_MACOS,
                      UI_SMALL, UI_BOLD, UI_LABEL, MONO_TTL)


class ModeScreen(tk.Frame):
    """
    Lets the user choose between single-file and folder mode.
    Calls on_choose('file') or on_choose('folder') when a card is clicked.
    """

    def __init__(self, master, on_choose):
        super().__init__(master, bg=COLORS['bg'])
        self._on_choose = on_choose
        self._build()

    def _build(self):
        tk.Frame(self, bg=COLORS['bg']).pack(expand=True, fill=tk.BOTH)

        tk.Label(self, text='SHRINKIFY',
                 bg=COLORS['bg'], fg=COLORS['accent'], font=MONO_TTL
                 ).pack(pady=(0, 4))
        tk.Label(self, text='Media Optimization Tool',
                 bg=COLORS['bg'], fg=COLORS['text_muted'], font=UI_SMALL
                 ).pack(pady=(0, 40))

        row = tk.Frame(self, bg=COLORS['bg'])
        row.pack()
        self._make_card(row, '📄', 'Single File',
                        'Convert or analyze\none media file.', 'file'
                        ).pack(side=tk.LEFT, padx=16)
        self._make_card(row, '📁', 'Folder',
                        'Scan an entire folder\n(and subfolders).', 'folder'
                        ).pack(side=tk.LEFT, padx=16)

        tk.Frame(self, bg=COLORS['bg']).pack(expand=True, fill=tk.BOTH)

    def _make_card(self, parent, icon: str, title: str,
                   desc: str, mode: str) -> tk.Frame:
        W = 200 if _IS_MACOS else 180
        H = 200 if _IS_MACOS else 185

        card = tk.Frame(parent, bg=COLORS['surface'],
                        width=W, height=H, cursor='hand2')
        card.pack_propagate(False)
        tk.Frame(card, bg=COLORS['accent'], height=2).pack(fill=tk.X)

        inner = tk.Frame(card, bg=COLORS['surface'])
        inner.pack(expand=True, fill=tk.BOTH, padx=20, pady=20)

        tk.Label(inner, text=icon,
                 bg=COLORS['surface'], fg=COLORS['accent'],
                 font=('TkDefaultFont', 28)).pack(pady=(0, 8))
        tk.Label(inner, text=title,
                 bg=COLORS['surface'], fg=COLORS['text'], font=UI_BOLD).pack()
        tk.Label(inner, text=desc,
                 bg=COLORS['surface'], fg=COLORS['text_muted'], font=UI_LABEL,
                 justify=tk.CENTER, wraplength=W - 32).pack(pady=(6, 0))

        all_widgets = [card, inner] + inner.winfo_children()

        def on_enter(_):
            for w in all_widgets:
                try: w.config(bg=COLORS['surface2'])
                except Exception: pass

        def on_leave(_):
            for w in all_widgets:
                try: w.config(bg=COLORS['surface'])
                except Exception: pass

        def on_click(_):
            self._on_choose(mode)

        for w in all_widgets:
            w.bind('<Enter>', on_enter)
            w.bind('<Leave>', on_leave)
            w.bind('<Button-1>', on_click)

        return card
