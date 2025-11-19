import re

import pytest

from iglesia.clean_text import extract_clean_text

# Ejemplo de texto original (simulado)
TEXTO_EJEMPLO = """DISCURSO DEL SANTO PADRE LEÓN XIV A LAS HERMANAS...
Salita del Aula Pablo VI Miércoles, 15 de octubre 2025
[ Multimedia ]
____________________________________
Ave María Purísima:
¡Buenos días a todas! Han venido a Roma en este Año Santo para vivir un momento de encuentro con el Señor, que veo que las ha llenado de júbilo. Santo Tomás de Villanueva, comentando los soliloquios de san Agustín, ilustra el origen de esta dicha: «No sois tú [Señor] una cosa y otra cosa tu recompensa, sino que tú mismo eres la recompensa inconmensurable» ( Obras Completas , II, 89).
Para encontrar al Señor en la vida que tan gustosamente hemos abrazado, debemos, como peregrinos, recorrer un camino. Es cierto que hay muchos, pero todos se reducen a dos: «Misericordia y verdad» ( Sal 24,10). Por estas dos vías, caminemos hacia el Señor, sirviendo como Marta en las obras de misericordia o descansando como María a los pies de Jesús para contemplar la verdad ( Lc 10,38-41) (cf. íbid ., VIII/2-3, 77).
Queridas hermanas, invoquemos la protección maternal de Nuestra Madre del Buen Consejo y la intercesión de santo Tomás de Villanueva.
Saludo a los peregrinos de lengua española.
"""


# Test básico
def test_extract_clean_text():
    x = extract_clean_text(TEXTO_EJEMPLO)
    pass


def inc(x):
    return x + 1


def test_answer():
    assert inc(3) == 4
