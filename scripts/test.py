import frenpy
print(frenpy.compile_frenpy("test.frenpy"))
frenpy.load("test.frenpy")
data = frenpy.get_words_frenpy()
print(data)
