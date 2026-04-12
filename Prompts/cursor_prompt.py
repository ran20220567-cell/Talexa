PROMPT = """
You are given a presentation slide image.

Task:
Find the EXACT location of the text: "{focus}"

Rules:
- Return ONLY one point (x, y)
- The point must be at the CENTER of the text
- Coordinates must match the image resolution
- If multiple matches exist, choose the most prominent one
- If unsure, choose the closest visible match

Image size: {w}x{h}

Respond ONLY like:
(x, y)
"""
