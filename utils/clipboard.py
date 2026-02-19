try:
    import pyperclip
except ImportError:
    pyperclip = None

def copy_text(text):
    if pyperclip:
        pyperclip.copy(text)
        return True
    return False
