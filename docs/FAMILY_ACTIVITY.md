# Seguimiento familiar: páginas, búsquedas y metadatos

## Implementado en esta rama

- `/activity`: sesiones temporales por dispositivo, eventos de metadatos, resumen de dominios, importación CSV y retención de 1 a 90 días.
- La API valida eventos, requiere un token temporal para ingestión de sesiones, almacena solo su hash y rechaza campos JSON no admitidos.
- El importador acepta hasta 1 MB y 1.000 filas por CSV; admite destinos de red, visitas a páginas y búsquedas, con validación adicional de las URLs.
- `browser-extension/`: extensión Chromium visible, desactivada por defecto, que captura navegación web futura en el dispositivo donde se instala y exporta registros CSV para importarlos en NetSentinel.

La extensión es el primer mecanismo del proyecto que registra realmente páginas visitadas y búsquedas. Usa eventos de navegación que el propio navegador expone a una extensión con permisos explícitos; no rompe HTTPS.

## Captura real de páginas y búsquedas

Seguí la [guía de instalación de la extensión](../browser-extension/README.md). Debe instalarse y activarse en cada navegador que se quiera supervisar. La extensión comienza vacía y apagada al instalarse; el registro se activa manualmente desde su panel.

Registra páginas HTTP(S) de nivel superior y cambios de URL que notifica la API de navegación. Cuando la URL coincide con un motor reconocido, guarda un evento de búsqueda separado. La versión inicial reconoce Google, Bing, DuckDuckGo, Yahoo, Ecosia, Brave Search, Yandex, Baidu, YouTube, Wikipedia, Amazon, Reddit y TikTok.

No lee el historial previo, contenido visible de páginas, campos de formularios, pulsaciones de teclado ni contraseñas. No puede ver búsquedas que ocurren solo dentro de una app nativa o que no aparecen en una URL compatible. La navegación privada queda fuera si no se habilita expresamente el uso de la extensión en modo privado desde el navegador; el valor predeterminado no lo habilita.

## Flujo de uso actual

1. Activá la extensión en el dispositivo supervisado; configurá registro de páginas, búsquedas, exclusiones y retención.
2. Exportá `netsentinel-browser-activity.csv` desde el panel de la extensión.
3. En NetSentinel, abrí `/activity`, seleccioná el dispositivo inventariado e importá ese archivo.
4. Revisá eventos `page_visit` y `search_query`. La importación queda etiquetada como `manual_import`.

La transferencia CSV es manual. No existe sincronización central en vivo entre equipos; no expongas el panel local en la red doméstica como atajo.

## Fuentes de metadatos del router

Las sesiones `router_dns`, `router_flow` y `device_agent` permiten recibir eventos normalizados durante una ventana temporal. Aún no hay un adaptador nativo para un modelo concreto de router/AP ni un agente de actividad de aplicaciones para Windows/macOS/Linux. Abrir una sesión no genera tráfico ni instala componentes.

## Esquema CSV

```csv
observed_at,event_type,domain,destination_ip,destination_port,protocol,app_name,blocked,page_url,search_engine,search_terms
```

Tipos disponibles: `dns_query`, `connection`, `tls_sni`, `app_usage`, `blocked`, `page_visit`, `search_query`.

Ejemplo de visita:

```csv
2026-10-11T18:30:00Z,page_visit,example.com,,,,browser-extension,false,https://example.com/guide,,,
```

Ejemplo de búsqueda:

```csv
2026-10-11T18:31:00Z,search_query,www.google.com,,,,browser-extension,false,https://www.google.com/search,Google,"cómo configurar controles parentales"
```

No se admiten campos como usuario, contraseña, token, cookie, cuerpos HTTP ni cargas útiles. Las páginas se guardan sin fragmento y quitando parámetros conocidos de autenticación/sesión, búsquedas e identificadores comunes de seguimiento. Los términos buscados quedan en un campo explícito separado; son datos sensibles y deben conservarse solo el tiempo necesario.

## Retención

- Retención predeterminada: 7 días en NetSentinel y en la extensión Chromium.
- En ambas ubicaciones se puede ajustar de 1 a 90 días.
- La extensión conserva como máximo 1.000 eventos; los más antiguos se descartan al alcanzar el límite.
- NetSentinel elimina eventos vencidos cuando se consulta/actualiza la vista o se cambian los ajustes.
- Los CSV y las copias SQLite pueden revelar intereses y hábitos de navegación; protegé los archivos y borrá los registros cuando ya no hagan falta.

## Interpretación

Una visita o consulta describe actividad reportada por el navegador, no prueba quién estaba frente a la pantalla, identidad, intención ni qué acciones realizó dentro de una cuenta. Esta herramienta no captura contraseñas, cookies, formularios ni contenido de mensajes.
