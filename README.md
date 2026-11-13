# NOCTURNE · Protocolo Umbral

Prototipo FPS 3D original en **Python y Panda3D**, ambientado en el distrito nocturno de Vesper. Sobrevive a oleadas de criaturas, combina armas y poderes, y conserva tu mejor puntuación. Escenario, armas, criaturas y sonidos se generan con código; no requiere descargar modelos, texturas o música.

## Jugar en Windows

Haz doble clic en **`Jugar.cmd`**. El lanzador utiliza el entorno `.venv` del proyecto, lo crea si falta e instala la dependencia si es necesario. La primera instalación necesita conexión a Internet; el juego funciona sin conexión después. Requiere Python 3.10 o superior instalado con acceso desde `PATH`.

En este equipo el entorno y Panda3D ya están instalados. También puedes ejecutar desde PowerShell:

```powershell
cd nocturne-protocolo-umbral
.\.venv\Scripts\python.exe main.py
```

Pulsa **Enter** o **Entrar al umbral** para comenzar. El ratón se captura únicamente al jugar. **Esc** pausa la partida y libera el cursor; cambiar a otra ventana también pausa.

## Instalación manual

Única dependencia externa: **`panda3d==1.10.16`**. La lógica usa la biblioteca estándar de Python. Instalación confirmada con Python 3.10 de 64 bits en Windows.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

En Linux/macOS, después de instalar Python y disponer de un controlador gráfico compatible:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python main.py
```

El código evita rutas de trabajo relativas y utiliza una fuente de reserva si no existe Segoe UI. La ejecución interactiva en Linux/macOS no se ha verificado en este equipo.

## Controles

| Acción | Tecla |
|---|---|
| Moverse / mirar | WASD / ratón |
| Disparar / apuntar con ADS | Clic izquierdo / mantener clic derecho |
| Correr | Shift + avanzar |
| Agacharse | Mantener Ctrl o C |
| Deslizarse | Ctrl o C mientras corres |
| Saltar | Espacio |
| Recargar | R |
| Pistola / rifle / escopeta | 1 / 2 / 3, o rueda del ratón |
| Dash oscuro | Q |
| Pulso de energía | E |
| Visión demoníaca | F |
| Furia | X |
| Pausar / continuar | Esc |
| Comenzar / reintentar | Enter |
| Silenciar / activar audio | M |
| Mostrar rendimiento | F3 |

## Mecánicas

- **Movimiento:** aceleración y frenado, sprint con FOV dinámico, salto con gravedad, agachado interpolado, deslizamiento, balanceo de cámara y arma, reacción al aterrizaje y retroceso. Las colisiones usan subpasos para evitar atravesar paredes con el dash.
- **ADS:** interpola posición del arma, campo de visión y sensibilidad; reduce la dispersión. Los puntos luminosos forman miras originales. Pistola y escopeta son semiautomáticas; el rifle permite mantener el gatillo.
- **Armas:** VIGIL / 09 (12 balas, 38 de daño), RELIQUIA / AR (30 balas, 24 de daño), EXEQUIA / 12 (8 cartuchos, 9 perdigones de 17 de daño con caída por distancia). Animaciones procedurales para disparar, recargar, cambiar, correr, saltar, deslizarse y apuntar. Cambiar de arma cancela una recarga sin regalar munición.
- **Enemigos:** básico perseguidor; rápido frágil; pesado resistente; invocador a distancia con proyectiles; élite que carga y se desplaza lateralmente. Tienen siluetas, tamaños y colores diferentes, evitan obstáculos con A* y pueden subir a las galerías por sus escaleras.
- **Oleadas:** 5, 8, 12 enemigos al comienzo; después aumenta la presión y aparecen más especiales. Hay cinco segundos entre rondas. Cada ronda completada recupera 22 de vida y munición de reserva; cada eliminación recupera 2 de vida.
- **Puntuación:** eliminación básica 100, bonificación de cabeza 150, élite 500 de base, bonificaciones de bajas rápidas, poderes y supervivencia. Los combos caducan si no encadenas eliminaciones.
- **Poderes:** dash con breve invulnerabilidad (4 s de recarga); pulso que daña y empuja enemigos visibles en 8 m (10 s); visión con marcadores que atraviesan la oscuridad durante 7 s (18 s); furia durante 6 s que aumenta daño, velocidad y cadencia (24 s).
- **Mapa:** arena de 52 × 52 m con patio ritual, capilla accesible, dos galerías elevadas, escaleras, coberturas, corredores laterales, portales y una silueta urbana gótica exterior.
- **Presentación:** iluminación fría y cálida, sombras direccionales en calidad media/alta, lluvia, niebla, charcos estilizados, haces de farol aproximados, neones discretos, fogonazos, humo, marcas de impacto, chispas y partículas sobrenaturales. Menú, HUD, pausa y derrota en español.
- **Audio:** disparos, recarga, pasos, golpes, rugidos, poderes y dos capas de música original sintetizada que se mezclan durante el combate.

El récord se guarda en `%LOCALAPPDATA%\Nocturne\record.json` (Windows) o `~/.local/share/Nocturne/record.json`. Los fallos de lectura/escritura no impiden jugar. Las pruebas automáticas no guardan récords.

## Arquitectura y función de cada archivo

El código completo está en los archivos del proyecto. Esta tabla sirve de índice funcional:

| Archivo o módulo | Función |
|---|---|
| `main.py` | Configuración del motor, argumentos y punto de entrada |
| `game/app.py` | Coordina entradas, estados, simulación, audio y renderizado |
| `game/config.py` | Parámetros editables de movimiento, cámara y presentación |
| `game/player/controller.py` | Captura del ratón, cámara interpolada, ADS y retroceso |
| `game/player/movement.py` | Movimiento independiente del motor, salto, sprint y deslizamiento |
| `game/player/powers.py` | Duración y recarga de las habilidades |
| `game/weapons/weapon.py` | Cargadores, reserva, cadencia y recarga compartidos |
| `game/weapons/pistol.py`, `rifle.py`, `shotgun.py` | Configuración de las tres armas |
| `game/weapons/ballistics.py` | Impactos por rayo, cabeza/cuerpo y oclusión de coberturas |
| `game/weapons/viewmodel.py` | Modelos y animaciones de armas en primera persona |
| `game/enemies/enemy.py` | Entidades y estadísticas de enemigos y proyectiles |
| `game/enemies/demon_*.py` | Configuraciones y clases de las cinco variantes |
| `game/systems/simulation.py` | IA, daño, poderes, proyectiles, eventos y navegación por escaleras |
| `game/systems/spawn_manager.py` | Portales, selección aleatoria y aparición escalonada |
| `game/systems/wave_manager.py` | Progresión, recuentos y pausas de oleadas |
| `game/systems/score_manager.py` | Puntuación, combos y bonificaciones |
| `game/systems/persistence.py` | Lectura y guardado atómico del récord |
| `game/world/layout.py` | Única fuente de geometría sólida, colisiones y rutas A* |
| `game/world/geometry.py` | Cubos, cilindros, conos y vigas procedurales |
| `game/world/arena.py` | Arquitectura, iluminación, niebla, lluvia y decoración |
| `game/world/effects.py` | Efectos temporales con cantidad limitada y reutilización |
| `game/rendering.py` | Modelos, animación de criaturas y proyectiles visibles |
| `game/ui/hud.py` | Menú, HUD, controles, pausa y pantalla de derrota |
| `game/audio/sound.py` | Síntesis WAV, sustitución de sonidos y mezcla de música |
| `tests/` | Pruebas de reglas, colisiones, navegación e integración |
| `tools/export_source.py` | Regenera el documento con todo el código |
| `tools/package_release.py` | Genera el ZIP de código fuente portable |
| `Jugar.cmd` | Lanzador de Windows con preparación del entorno |

Los módulos `__init__.py` definen los paquetes y las exportaciones compartidas. La simulación no depende del renderizado. Los eventos conectan daños, eliminaciones y poderes con sonidos y efectos. La geometría de las coberturas se comparte con colisiones e impactos para evitar paredes visuales que no detengan balas.

## Cómo probarlo

Pruebas automáticas:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -v
.\.venv\Scripts\python.exe main.py --smoke-test --offscreen --mute --seed 7 --frames 900 --screenshot artifacts/gameplay.png
```

La segunda orden ejecuta el motor, apunta y dispara por las mismas rutas de código que los controles, usa las tres armas y los cuatro poderes, recarga y escribe las métricas en `artifacts/smoke-result.json`. La opción `--offscreen` aún necesita un controlador gráfico; no es un simulador de renderizado sin GPU. Las pruebas de reglas (`test_combat`, `test_layout`, `test_weapons_movement`, `test_ballistics`) no abren ventana.

Ejecuta estas pruebas en tu entorno antes de usar el prototipo.

Prueba manual recomendada:

1. Entra al umbral y prueba WASD, sprint, salto y Ctrl para deslizarte. Choca contra una cobertura y comprueba que puedes deslizarte por su borde.
2. Sube por ambas escaleras y entra en la capilla. Comprueba que la cámara se eleva y que los enemigos pueden seguirte.
3. Usa 1/2/3, dispara, mantén ADS y recarga. Comprueba munición, dispersión, retroceso y cambio de arma durante una recarga.
4. Prueba Q/E/F/X y espera sus recargas. Comprueba marcadores de visión, aumento de cadencia y empuje del pulso.
5. Elimina la primera oleada y comprueba puntuación, pausa, recuperación y siguiente ronda.
6. Recibe daño hasta morir, reintenta con Enter y comprueba que vida, enemigos, munición y puntuación se reinician. Pausa con Esc y comprueba que los cooldowns se congelan.

## Rendimiento y opciones

```powershell
.\.venv\Scripts\python.exe main.py --quality low
.\.venv\Scripts\python.exe main.py --quality high --seed 42
.\.venv\Scripts\python.exe main.py --mute
```

El escenario estático se agrupa, la IA limita criaturas simultáneas a 28 y los efectos a 220. Las rondas continúan indefinidamente, con un máximo de 90 enemigos por ronda para contener tiempos y recursos; la salud y el daño siguen aumentando. Es una decisión explícita de rendimiento: las cantidades no crecen sin límite. La sensibilidad y las velocidades se ajustan en `game/config.py`.

Si tu controlador no permite sombras o el juego va lento, usa `--quality low`. Si falta audio o prefieres silencio, usa `--mute`; la ausencia de dispositivo de audio no debe impedir jugar. No hay servicios remotos ni conexión durante las partidas.

## Assets y alcance del prototipo

Coloca reemplazos opcionales en `game/assets/sounds/` usando los nombres del [índice de audio](game/assets/sounds/README.md). Los modelos actuales se construyen con primitivas, con una estética angular deliberada. `game/assets/models/` y `game/assets/textures/` quedan preparados para arte posterior; no hacen falta para ejecutar nada.

Las diez fases de la especificación están integradas en una versión jugable. Es un prototipo de arena para un jugador: animaciones procedurales, IA local y efectos estilizados; no incluye campaña, multijugador, modelos esqueléticos ni reflejos físicos. Las siluetas, nombres, armas, música y arquitectura son originales y no reproducen assets de otras franquicias.

Referencia técnica utilizada: [SDK oficial de Panda3D 1.10.16](https://www.panda3d.org/download/sdk-1-10-16/) y [documentación oficial del ratón](https://docs.panda3d.org/1.10/python/programming/hardware-support/mouse-support).
