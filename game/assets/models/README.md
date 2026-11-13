# Modelos

No hay dependencias de modelos descargados. `game/world/geometry.py`, `game/weapons/viewmodel.py` y `game/rendering.py` construyen las mallas originales.

Para sustituirlas por modelos propios, carga el modelo desde `base.loader.loadModel()` en esos módulos conservando las dimensiones, el eje Z hacia arriba, el avance local +Y y las posiciones de los hitboxes.
