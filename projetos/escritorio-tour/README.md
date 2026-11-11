# Escritório — tour 3D e simulação de uso

Maquete 3D procedural do projeto de escritório (apresentação *139-ARQ — Virgínia Cyrne
arquitetura e interiores*), reconstruída a partir das imagens da apresentação e
renderizada no Blender (Cycles).

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `tour_escritorio.mp4` | Vídeo do tour (~1 min): entrada pela porta, giro 360°, abertura do armário em L, gavetas, suporte de teclado e aparador |
| `imagens/` | Imagens estáticas (vista geral, bancada, aparador, armário aberto, gavetas…) |
| `imagens/panorama_360.jpg` | Panorâmica equiretangular 360° (abre em qualquer visualizador 360) |
| `escritorio.py` | Script que gera a cena, a animação e os renders |

## Armário em L (como foi simulado)

- **Duas portas maiores (frente do armário):** abrem do meio, cada uma para um lado —
  dobradiças nas extremidades.
- **Porta do L menor (voltada para a bancada):** dobradiça do lado direito (lado da
  bancada), abrindo da esquerda para a direita.
- Observação de uso: com o L, a porta maior do lado do canto, aberta a 90°, encosta
  na frente da porta do L. As duas não abrem totalmente ao mesmo tempo — no vídeo elas
  são abertas em sequência.

## Medidas usadas (estimadas a partir das imagens, não da planta)

Sala 3,60 × 2,90 m, pé-direito 2,60 m · bancada 2,50 m × 0,62 m (h 0,77 m) com
3 gaveteiros de 4 gavetas · aparador 3,56 m × 0,55 m (h 0,89 m) com 6 portas ·
armário em L: frente 1,10 m (2 portas de 0,55 m) + perna do L de 0,50 m.

## Como renderizar de novo

```bash
pip install bpy            # Blender como módulo Python (testado com 5.3)
FAST_GI=1 python escritorio.py --mode anim --step 2 --res 960 540 --samples 12 --exposure 0.3 --out frames/
python escritorio.py --mode still --res 1920 1080 --samples 64 --out imagens/
python escritorio.py --mode pano  --res 4096 2048 --samples 48 --out imagens/
```
