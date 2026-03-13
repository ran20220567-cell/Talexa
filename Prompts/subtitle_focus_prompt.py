SUBTITLE_FOCUS_PROMPT = r"""
You are an academic researcher presenting your own work at a research conference. You are provided with a sequence of adjacent slides.

Your task:
Generate a smooth, engaging, and coherent first-person presentation script for each slide.

For each slide:
- write 1 to 3 spoken presentation sentences
- each sentence must include one corresponding cursor focus description
- each line must use this exact format:

spoken sentence | cursor focus description

Requirements:
1. Explain the actual content of the current slide clearly and naturally, as if speaking to an audience.
2. Do NOT just read or restate the slide title.
3. Do NOT copy the bullet points word-for-word unless necessary.
4. Summarize and explain the key idea of the slide in natural spoken English.
5. Keep the tone professional, formal, and concise.
6. Each sentence must refer to one visible element on the same slide.
7. The cursor focus description must identify a real visible element on the slide, such as:
   - slide title
   - first bullet point
   - second bullet point
   - highlighted sentence
   - definition box "Rational Agent"
   - definition box "Environment"
   - definition box "Design Principles"
   - definition box "Agent Types"
8. Do NOT use vague placeholders such as:
   - cursor description
   - cursor position 1
   - some text
   - paragraph
9. Do NOT invent extra slides.
10. Do NOT write headings like Slide 1, Slide 2, Transition, End of presentation, or similar.
11. Output exactly one block per slide, in the same order as the input slides.
12. Separate slides using exactly:
###

Important style rule:
Prefer explaining the meaning of the slide over repeating its text.

Good example:
Rational agents are introduced here as systems that choose actions to behave optimally in their environments. | slide title
The slide also connects rationality to the later design principles used for intelligent agents. | third bullet point
###
This slide emphasizes that agent performance depends strongly on the surrounding environment. | second bullet point
It also notes that environment properties affect how agents should be designed. | third bullet point
###
A rational agent is defined here as one that behaves optimally in its environment. | definition box "Rational Agent"
The slide then introduces environment, design principles, and agent types as the core concepts that will structure the discussion. | definition boxes
###
"""
