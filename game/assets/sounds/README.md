# Banco de audio

`game/audio/sound.py` genera audio PCM original cuando hace falta. Para usar audio propio, coloca WAV con estos nombres en esta carpeta:

| Archivo | Uso |
|---|---|
| `pistol.wav`, `rifle.wav`, `shotgun.wav` | Disparos |
| `reload.wav` | Recarga |
| `step.wav` | Pasos |
| `impact.wav` | Impacto de bala |
| `roar.wav` | Aparición/rugido de criatura |
| `dash.wav`, `pulse.wav`, `vision.wav`, `fury.wav` | Habilidades |
| `kill.wav`, `wave.wav`, `hurt.wav` | Eliminación, comienzo de oleada y daño |
| `ambient.wav`, `combat.wav` | Capas de música en bucle |

Se recomiendan WAV PCM de 16 bits. Las dos pistas musicales se mezclan progresivamente; prepara bucles sin saltos. Los archivos de `generated/` son la reserva sintetizada y se regeneran si faltan. No sustituyas allí tus originales: utiliza esta carpeta superior. Los efectos tienen voces limitadas para controlar la superposición.
