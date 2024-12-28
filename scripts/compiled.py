# importations :
import os
import time
# configuration de frenpy : 


# test de la fonction :
print("--- version de frenpy ---")
print("version actuelle : 3")
print("-----------------------")
time.sleep(3)
print("Bonjour, ce texte est un exemple")
# test interaction
question = input("es-tu riche ?")
if "oui" in question :
    print("tu es riche !")
if "non" in question:
    print("tu n'es pas riche !")
