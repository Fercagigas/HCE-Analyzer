# Script to write LaTeX architecture file
content = r"""% test content"""
with open("latex_files/arquitectura_chathce.tex", "w", encoding="utf-8") as f:
    f.write(content)
print("done")
