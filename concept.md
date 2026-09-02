Yo diseñaría **GlyphTap** alrededor de una sola idea: **invocar → escribir → elegir → pegar**, en unos 2–3 segundos. No debería sentirse como “abrir una aplicación de iconos”, sino como el equivalente en Omarchy a un command palette especializado en iconos.

Omarchy actualmente permite precisamente este tipo de experiencia mediante plugins `overlay` que viven dentro del proceso persistente de `omarchy-shell`, igual que otros selectores y overlays del sistema, así que GlyphTap puede sentirse completamente nativo en lugar de lanzar otra ventana de Quickshell. ([Omarchy Plugins][1])

## La experiencia principal

El flujo ideal sería:

1. Presionas un atajo configurable, por ejemplo **`Super + I`**. También debería aparecer como `GlyphTap` dentro de `Super + Space`.
2. Aparece instantáneamente un overlay grande, ligeramente oscureciendo el escritorio. El cursor ya está dentro del buscador; no tienes que hacer clic en nada.
3. Escribes `calendar`, `github`, `arrow left`, `wifi off`, `database`, etc.
4. Mientras escribes aparecen decenas de iconos en una cuadrícula. GlyphTap usaría Iconify como backend, que actualmente reúne aproximadamente **300.000 iconos de más de 200 colecciones**. ([GitHub][2])
5. Navegas con flechas o mouse.
6. **Enter o clic sobre un icono = SVG copiado + GlyphTap desaparece.**
7. Haces `Ctrl+V` en Figma, código, Obsidian, un README, etc.

Ese debería ser el **happy path absoluto**. Nada de abrir una ficha, buscar un botón “Copy”, seleccionar formato y confirmar.

Visualmente imaginaría algo parecido a:

```text
┌──────────────────────────────────────────────────────────────┐
│  GlyphTap                                      SVG ▾         │
│                                                              │
│  🔍  calendar_                                               │
│                                                              │
│  All   Lucide   Material   Solar   Tabler   Phosphor   ...  │
│                                                              │
│   ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐          │
│   │  ◫  │ │  ◫  │ │  ◫  │ │  ◫  │ │  ◫  │ │  ◫  │          │
│   │     │ │     │ │     │ │     │ │     │ │     │          │
│   └─────┘ └─────┘ └─────┘ └─────┘ └─────┘ └─────┘          │
│   lucide  solar   tabler   huge...  phos...  mdi            │
│                                                              │
│  ↑↓←→ Navigate    Enter Copy    Space Preview    Esc Close  │
└──────────────────────────────────────────────────────────────┘
```

## Lo que haría que GlyphTap fuera realmente bueno

**Búsqueda instantánea.** GlyphTap debería consultar el `/search` de Iconify, que ya permite búsquedas por texto, colección y categoría, pero añadir encima caché y ranking propio. ([Iconify][3]) Al escribir `home`, no debería haber spinner visible: primero aparecen resultados cacheados y unas fracciones de segundo después se actualizan si llegan resultados mejores.

**Keyboard-first absoluto.** Al abrirse, búsqueda enfocada. Flechas navegan. `Enter` copia. `Esc` sale. `Tab` mueve entre filtros. `Space` muestra una preview grande. `Ctrl+Enter` abre acciones adicionales. Un usuario habitual podría usar GlyphTap durante semanas sin tocar el mouse.

**Un clic significa copiar.** Icônes y las propias recomendaciones de Iconify ya usan el patrón “buscar icono → copiar SVG → pegar en la herramienta de diseño”. ([GitHub][4]) GlyphTap debería reducirlo incluso más: seleccionar es copiar.

Después de copiar:

> `✓ SVG copied · lucide:calendar`

El mensaje aparece durante unos 700 ms mientras el overlay desaparece.

**SVG como predeterminado, pero no como única opción.** Arriba a la derecha habría un selector discreto `SVG ▾`. Podrías fijar permanentemente tu formato preferido: `SVG`, `Iconify name`, `React`, `Vue`, `JSX`, `CSS`, `HTML`, `Data URI` o `SVG file`. Para un developer, por ejemplo, copiar `lucide:calendar-days` directamente puede ser más útil que copiar el SVG.

`Ctrl+Enter` podría abrir rápidamente:

```text
Copy SVG             Enter
Copy icon name       N
Copy JSX             J
Copy React           R
Copy Vue             V
Save .svg            S
```

**Preview sin estorbar.** No pondría permanentemente un panel lateral, porque sacrifica espacio. Pulsar `Space` sobre un resultado expandiría temporalmente el icono y mostraría:

```text
Solar
calendar-minimalistic-linear

24 × 24
Stroke
MIT

[ Copy SVG ]
```

Soltar `Space` o pulsarlo nuevamente vuelve al grid.

**Colecciones excelentes, no 300.000 iconos arrojados indiscriminadamente.** La búsqueda global sería el default, pero GlyphTap permitiría marcar packs favoritos. Por ejemplo:

`★ Lucide  ★ Solar  ★ Phosphor  ★ Tabler`

Si trabajas normalmente con Lucide y Solar, esos resultados tendrían prioridad sobre colecciones desconocidas. Iconify expone información de sus colecciones mediante su API, por lo que esto puede construirse sin mantener manualmente el catálogo. ([Iconify][5])

**Recents y Favorites serían fundamentales.** Si abres GlyphTap sin escribir nada, mostraría:

`Recently used` → los últimos ~20 iconos.

Debajo:

`Favorites` → los iconos que has guardado.

Esto hace que GlyphTap termine funcionando también como tu pequeña biblioteca personal de iconos.

Favorito podría ser simplemente `Ctrl+D` o clic derecho → `Favorite`.

**Memoria inteligente del comportamiento.** Si buscas `github` repetidamente y siempre eliges `simple-icons:github`, ese debería convertirse gradualmente en tu primer resultado. Si casi siempre eliges Solar y Lucide, esos packs deberían subir automáticamente. Todo local, sin cuenta.

**Filtros rápidos, no formularios.** Una segunda pulsación de `Tab` podría entrar en filtros:

`All · Outline · Filled · Duotone · Color`

y luego colección:

`All sets · Lucide · Solar · Tabler · Material · …`

Pero deberían ser completamente opcionales; la mayoría de búsquedas nunca deberían necesitarlos.

**Personalización visual mínima.** No convertiría GlyphTap en un editor SVG complejo. Como máximo, al abrir la preview permitiría cambiar `color`, `size`, `stroke` cuando el icono lo soporte, además de rotate/flip. Iconify puede generar SVG dinámicamente con color, dimensiones, rotación y flip. ([GitHub][6])

Lo importante es no matar la velocidad del producto intentando convertirse en Figma.

## Integración específica con Omarchy

Aquí es donde creo que GlyphTap podría destacar frente a simplemente abrir `icones.js.org`.

Debería ser un **plugin `overlay` nativo de Omarchy**, ejecutándose dentro del mismo `omarchy-shell`. Omarchy recomienda precisamente que los plugins compartan el proceso Quickshell persistente y no arranquen una segunda instancia. ([Omarchy Plugins][1])

Además, debería adoptar automáticamente:

**tema actual de Omarchy → GlyphTap.**

Si cambias de Tokyo Night a Catppuccin o cualquier otro theme, GlyphTap cambia instantáneamente colores, foreground, border, selección y background. Eso haría que las screenshots del plugin se vean espectaculares en la página de plugins.

Y permitiría:

```bash
omarchy-shell shell toggle glyphtap
```

además del shortcut. Ese patrón ya se utiliza en otros plugins overlay actuales de Omarchy. ([GitHub][7])

## Un detalle que puede hacerlo muy adictivo

Añadiría un **modo persistente**.

Normalmente:

`Enter` → copiar → cerrar.

Pero:

`Ctrl+Enter` → copiar → **mantener GlyphTap abierto**.

Entonces puedes seleccionar rápidamente:

```text
home
user
settings
search
logout
```

y copiar cinco SVG sucesivamente mientras estás diseñando una interfaz.

Podría mostrarse abajo:

> `5 icons copied this session`

Y quizás permitir arrastrar un icono directamente desde GlyphTap hacia una aplicación compatible como archivo `.svg`.

## Offline

No descargaría los ~300.000 iconos de entrada. Iconify está precisamente diseñado para entregar iconos bajo demanda. ([GitHub][8])

GlyphTap mantendría localmente:

* metadata/búsquedas recientes;
* favoritos;
* iconos recientemente utilizados;
* packs que el usuario haya marcado para uso offline.

Así, la instalación sigue siendo pequeña, las búsquedas habituales funcionan instantáneamente y no dependes permanentemente de una descarga masiva.

---

Creo que la identidad del producto debería terminar reducida a esto:

**GlyphTap**
**Find. Tap. Copy.**

`Super + I` → `calendar` → `Enter` → `Ctrl + V`

Si esa secuencia se siente instantánea y hermosa, **ya tienes el 90% de lo que haría que el plugin obtuviera muchas descargas**. Todo lo demás —favoritos, formatos, colecciones, preview— debería existir alrededor de ese flujo sin hacerlo más lento.

[1]: https://plugins.omarchy.org/develop.html?utm_source=chatgpt.com "Develop a Plugin | Omarchy Plugins"
[2]: https://github.com/iconify?utm_source=chatgpt.com "Iconify · GitHub"
[3]: https://iconify.design/docs/api/search.html?utm_source=chatgpt.com "Searching icons"
[4]: https://github.com/iconify/website/blob/main/docs/usage/index.md?utm_source=chatgpt.com "website/docs/usage/index.md at main · iconify/website · GitHub"
[5]: https://iconify.design/docs/api/collections.html?utm_source=chatgpt.com "List of icon sets"
[6]: https://github.com/iconify/website/blob/main/docs/api/svg.md?utm_source=chatgpt.com "website/docs/api/svg.md at main · iconify/website · GitHub"
[7]: https://github.com/konradk/hark?utm_source=chatgpt.com "GitHub - konradk/hark: AI command palette for Hyprland and Omarchy - Quickshell overlay, screenshot attachments, web search. · GitHub"
[8]: https://github.com/iconify/website/blob/main/docs/icons/icon-data.md?utm_source=chatgpt.com "website/docs/icons/icon-data.md at main · iconify/website · GitHub"
