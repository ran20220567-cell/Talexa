PROMPT = """
You are given a presentation slide image.

Task:
Find the EXACT location of the text: "{focus}"

Rules:
- Return ONLY one point (x, y)
- The point must be at the CENTER of the text
- Coordinates MUST be normalized between 0 and 1
- (0,0) is top-left, (1,1) is bottom-right
- If multiple matches exist, choose the most prominent one

Respond ONLY like:
(0.45, 0.32)
"""
