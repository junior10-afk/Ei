import os
import io
import ctypes
from ctypes import wintypes
from typing import Dict, Any, Optional
from PIL import Image
from tools.registry import tool_registry
from core.config import config

def _capture_screen_gdi() -> Optional[Image.Image]:
    """Capture d'écran Windows native ultra-rapide et stable via GDI/User32."""
    try:
        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32

        user32.SetProcessDPIAware()
        width = user32.GetSystemMetrics(0)
        height = user32.GetSystemMetrics(1)

        hdesktop = user32.GetDesktopWindow()
        desktop_dc = user32.GetWindowDC(hdesktop)
        if not desktop_dc:
            return None

        mem_dc = gdi32.CreateCompatibleDC(desktop_dc)
        bitmap = gdi32.CreateCompatibleBitmap(desktop_dc, width, height)
        gdi32.SelectObject(mem_dc, bitmap)

        # 0x00CC0020 = SRCCOPY
        gdi32.BitBlt(mem_dc, 0, 0, width, height, desktop_dc, 0, 0, 0x00CC0020)

        class BITMAPINFOHEADER(ctypes.Structure):
            _fields_ = [
                ('biSize', wintypes.DWORD),
                ('biWidth', wintypes.LONG),
                ('biHeight', wintypes.LONG),
                ('biPlanes', wintypes.WORD),
                ('biBitCount', wintypes.WORD),
                ('biCompression', wintypes.DWORD),
                ('biSizeImage', wintypes.DWORD),
                ('biXPelsPerMeter', wintypes.LONG),
                ('biYPelsPerMeter', wintypes.LONG),
                ('biClrUsed', wintypes.DWORD),
                ('biClrImportant', wintypes.DWORD)
            ]

        bmi = BITMAPINFOHEADER()
        bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.biWidth = width
        bmi.biHeight = -height  # top-down
        bmi.biPlanes = 1
        bmi.biBitCount = 32
        bmi.biCompression = 0

        buffer_len = width * height * 4
        buf = ctypes.create_string_buffer(buffer_len)
        lines = gdi32.GetDIBits(mem_dc, bitmap, 0, height, buf, ctypes.byref(bmi), 0)

        gdi32.DeleteObject(bitmap)
        gdi32.DeleteDC(mem_dc)
        user32.ReleaseDC(hdesktop, desktop_dc)

        if lines > 0:
            im = Image.frombuffer('RGBA', (width, height), buf, 'raw', 'BGRA', 0, 1)
            im = im.convert('RGB')
            im.thumbnail((1280, 720))
            return im
    except Exception as e:
        print(f"[Vision] Erreur capture GDI: {e}")
    return None

@tool_registry.register(
    name="take_screenshot_and_analyze",
    description="Capture l'écran du PC et l'analyse visuellement avec l'IA pour répondre à une question sur ce qui est affiché",
    parameters={"question": "str (ce qu'il faut analyser ou trouver sur l'écran, ex: 'Quelle erreur est affichée ?')"}
)
def take_screenshot_and_analyze(question: str = "") -> Dict[str, Any]:
    query = question.strip() if question else "Décris ce qui s'affiche à l'écran et les fenêtres ouvertes."
    
    img = _capture_screen_gdi()
    if not img:
        return {
            "speech": "Impossible de capturer l'écran actuellement.",
            "error": "Capture échouée",
            "analysis": ""
        }

    api_key = (config.gemini_api_key or os.getenv("GEMINI_API_KEY", "")).strip().strip('"\'')
    if not api_key:
        return {
            "speech": "L'analyse visuelle nécessite une clé Gemini API configurée.",
            "error": "Clé API manquante",
            "analysis": ""
        }

    try:
        from google import genai
        client = genai.Client(api_key=api_key)

        prompt_instruction = (
            f"Tu es l'assistant visuel de bureau. L'utilisateur te demande : « {query} ».\n"
            f"Analyse l'image de son écran Windows ci-jointe. Sois précis, lis les textes pertinents "
            f"et réponds de façon claire et structurée."
        )

        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[img, prompt_instruction]
        )

        if resp and resp.text:
            analysis_text = resp.text.strip()
            # Phrase courte pour la voix
            first_sentence = analysis_text.split(".")[0].strip() + "."
            return {
                "speech": f"J'ai analysé votre écran. {first_sentence[:120]}",
                "question": query,
                "analysis": analysis_text
            }
        else:
            return {
                "speech": "La capture a été prise mais l'analyse visuelle n'a rien renvoyé.",
                "analysis": ""
            }
    except Exception as e:
        return {
            "speech": "Une erreur est survenue lors de l'analyse visuelle de l'écran.",
            "error": str(e),
            "analysis": ""
        }
