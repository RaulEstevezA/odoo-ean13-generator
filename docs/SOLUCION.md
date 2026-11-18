# Generador EAN-13 para productos: solución adoptada

En este documento explico cómo he planteado el módulo `product_ean13_generator`, qué decisiones he tomado y por qué, y cómo cubre cada requisito de la prueba. Las instrucciones de instalación y uso están en el [README](../README.md).

## 1. Planteamiento general

Desde el principio tuve claro que quería que toda la lógica de generación estuviera en un único sitio: el método `action_generate_ean13` de `product.product`. El enunciado pide generar códigos desde la ficha de la variante y de forma masiva, y más adelante añadí también la ficha de producto. Si cada una de esas vías tuviera sus propias comprobaciones, sería fácil que acabaran comportándose de forma distinta. Por eso todas delegan en el mismo método, y las validaciones, los permisos y la unicidad se aplican igual se entre por donde se entre.

```
Ficha de variante ──────────┐
Ficha de producto (1 var.) ─┼──▶ product.product.action_generate_ean13()
Asistente masivo ───────────┘        │
                                     ├─ 1. Permisos del usuario
                                     ├─ 2. Validaciones del producto y la empresa
                                     ├─ 3. Validación de la secuencia
                                     ├─ 4. Número de la secuencia + dígito de control
                                     ├─ 5. Comprobación de unicidad
                                     └─ 6. Escritura protegida por restricción SQL
```

Para organizar el código me he guiado por los principios SOLID, sobre todo por dos:

- **Responsabilidad única.** Cada pieza se ocupa de una sola cosa. La empresa sabe si su configuración es válida, la variante sabe generar y validar su propio código, y el asistente solo recorre las variantes y recoge los resultados. La ficha de producto no genera nada: delega en su variante.
- **Abierto a la extensión, cerrado a la modificación.** Amplío los modelos de Odoo mediante herencia (`_inherit`), sin modificar su código. Dentro del módulo pasa lo mismo: cuando añadí la ficha de producto como nueva vía de generación, no tuve que tocar la lógica central, solo llamarla.

También he intentado no cambiar el comportamiento estándar de Odoo. La única excepción es la unicidad del código de barras, que paso a hacer global; explico el motivo en el apartado 9.

## 2. Componentes

| Componente | Qué hace |
|---|---|
| `res.company` | Guarda si la empresa permite la generación (`ean_generation_enabled`) y qué secuencia usa (`ean_sequence_id`). También contiene las reglas que deciden si una secuencia es válida. |
| `res.config.settings` | Muestra esa configuración en **Ajustes generales** para la empresa activa. |
| `ir.sequence` | Impide modificar una secuencia que ya se usa para EAN-13 si con el cambio deja de ser válida. |
| `product.product` | Decide si se puede generar (`can_generate_ean13`), valida, genera el código, comprueba la unicidad y define la restricción SQL. |
| `product.template` | Permite generar desde la ficha de producto cuando este tiene una sola variante. |
| `ean13.generate.wizard` | Asistente de generación masiva. |
| Grupo `group_ean13_generator` | Controla qué usuarios pueden generar códigos. |

## 3. Cómo se genera el código

Un EAN-13 tiene 12 dígitos de datos y un dígito de control al final.

Los 12 primeros salen de la secuencia que tenga configurada la empresa del producto. Es una `ir.sequence`, el mecanismo estándar de Odoo para numeraciones, y eso tiene dos ventajas: Odoo ya resuelve con ella la concurrencia entre usuarios, y el administrador puede ajustar el rango (prefijo, número siguiente) desde la interfaz, sin tocar código.

El dígito de control lo calculo con el algoritmo estándar: las posiciones impares pesan 1 y las pares pesan 3, y el dígito es lo que falta para llegar a la siguiente decena. El método rechaza cualquier base que no tenga exactamente 12 dígitos ASCII. Esto lo añadí al escribir los tests, porque `isdigit()` de Python acepta como dígitos caracteres como `１２３` (ancho completo), y no quería que algo así llegara a un código de barras.

## 4. Configuración por empresa

Cada empresa tiene su propio interruptor y su propia secuencia. En Ajustes, el bloque está marcado como dependiente de la empresa y se aplica siempre a la empresa activa.

El enunciado dice que la generación solo debe hacerse si la empresa tiene los parámetros *correctamente* configurados. Al principio solo comprobaba que hubiera una secuencia asignada, pero revisando el comportamiento me di cuenta de que eso no bastaba. En el desplegable se podía elegir cualquier secuencia del sistema, por ejemplo la de albaranes internos. Al generar, el módulo pedía un número a esa secuencia y fallaba después, porque el resultado no eran 12 dígitos. Es decir, el error llegaba tarde, con un mensaje poco claro, y además se gastaba un número de la numeración de otro documento.

Por todo ello añadí una validación de la secuencia. Para que sea válida tiene que cumplir esto:

- Prefijo y sufijo vacíos o solo con dígitos.
- Prefijo + relleno + sufijo = 12.
- Sin subsecuencias por rango de fechas, porque reiniciarían la numeración.
- Pertenecer a la misma empresa o ser compartida (sin empresa).
- No estar agotada.

Las reglas están en un único método (`_get_ean13_sequence_errors`) y se aplican en tres momentos:

1. **Al configurar la empresa:** no deja guardar, y el mensaje indica la empresa, la secuencia y cada motivo.
2. **Al modificar una secuencia que ya está en uso:** tampoco deja guardar. Las secuencias que no se usan para EAN-13 no se ven afectadas.
3. **Antes de generar:** si la secuencia no es válida, el botón no aparece y la generación se detiene **antes** de pedir el número.

## 5. Validaciones y mensajes

Estas son las situaciones que controlo y el mensaje que recibe el usuario en cada una:

| Situación | Mensaje |
|---|---|
| Usuario sin permisos | No tiene permisos para generar códigos EAN-13. |
| Variante con código previo | La variante ya tiene un código de barras asignado. |
| Variante sin empresa | La variante debe estar asociada a una empresa. |
| Generación desactivada | La generación de códigos EAN-13 no está habilitada para la empresa X. |
| Sin secuencia | La empresa X no tiene configurada una secuencia EAN-13. |
| Secuencia inválida | La secuencia EAN-13 'S' de la empresa X no es válida: (lista de motivos). |
| Código ya usado en una variante (incluidas las archivadas) | El código EAN-13 ya está asignado a otra variante. |
| Código ya usado en un embalaje | El código EAN-13 ya está asignado a un embalaje. |
| Producto con varias variantes (desde la ficha de producto) | El producto X tiene varias variantes. Genere el código EAN-13 desde cada variante. |

Siempre que tiene sentido, el mensaje incluye la empresa o la secuencia afectada. En una generación masiva con productos de varias empresas, saber *dónde* está el problema es lo que permite corregirlo rápido.

Todos los errores funcionales son `UserError`, o sus subclases `AccessError` y `ValidationError`. Así Odoo los muestra como avisos normales, y el asistente masivo puede recogerlos sin interrumpir el resto del lote.

## 6. Cuándo está disponible la acción

El campo calculado `can_generate_ean13` reúne las condiciones: sin código previo, con empresa, generación activada y secuencia válida. Las vistas lo usan para mostrar u ocultar el botón, y el permiso se controla con el atributo `groups`.

Aun así, ocultar un botón no es seguridad: la acción se puede invocar directamente. Por eso el servidor repite todas las comprobaciones cada vez que se ejecuta.

Con la ficha de producto me pasó algo que no esperaba. Al probar, creé un producto normal y el botón no aparecía. El motivo es que, cuando un producto tiene una sola variante, Odoo abre la ficha de la plantilla y no la de la variante. El requisito habla de la ficha de la variante, así que en sentido estricto se cumplía, pero crear un producto y buscar el botón es lo primero que haría cualquiera al probar el módulo. Por eso añadí el botón también a la ficha de producto, solo cuando hay una única variante, igual que hace Odoo con el propio campo código de barras. Con varias variantes no se puede saber a cuál asignar el código, así que en ese caso se genera desde cada variante.

Por un motivo parecido, el botón también está en la ficha de variante que se abre desde la plantilla (botón **Variantes**), que en Odoo es una vista distinta de la del menú **Variantes de producto**.

## 7. Generación masiva

Se lanza desde la lista de variantes, con **Acción → Generar códigos EAN-13**.

Lo que más me preocupaba aquí era el tratamiento de errores. Si de cien variantes falla una, no tiene sentido perder las otras noventa y nueve. Por eso cada variante se procesa dentro de su propio `savepoint`: si falla, se deshacen solo sus cambios y se sigue con la siguiente. Al final, el asistente muestra cuántos códigos se han generado, cuántos errores ha habido y una línea por variante con el código o el motivo del error.

El asistente no tiene reglas propias: llama a la misma acción que la generación individual, así que valida y comprueba permisos exactamente igual.

## 8. Seguridad

- He creado un grupo, **Generar códigos EAN-13**, en una categoría propia, que se asigna desde la ficha del usuario.
- El botón, la acción de la lista y el acceso al asistente están restringidos a ese grupo.
- El servidor comprueba el grupo (`has_group`) en cada generación.
- La configuración en Ajustes solo la ven los administradores.

Uso `sudo` en dos puntos, y quiero dejar claro por qué:

- **Para comprobar la unicidad.** Un código puede estar en un producto de otra empresa que el usuario no ve. Si buscara con sus permisos, no lo encontraría y la comprobación no serviría.
- **Para escribir el código.** He entendido el grupo como el permiso que autoriza a asignar códigos generados, aunque el usuario no tenga permisos generales para editar productos. Solo se escribe el campo `barcode`, y únicamente después de pasar todas las validaciones. Si en un entorno real se prefiriera exigir también permiso de edición, bastaría con quitar ese `sudo`.

## 9. Unicidad

Odoo, por defecto, permite el mismo código de barras en empresas distintas. El enunciado pide códigos únicos **dentro del sistema**, así que decidí que la unicidad fuera global. Se aplica también a los códigos introducidos a mano, para que un código generado no pueda coincidir nunca con otro.

La garantizo en tres niveles:

1. **Comprobación previa:** busco el código en todas las variantes (incluidas las archivadas y las de cualquier empresa) y en los embalajes. Si ya existe, el usuario recibe un mensaje claro. Las archivadas las incluí después de ver que, si no, un producto archivado con ese código pasaba la comprobación y el error llegaba desde la base de datos.
2. **Restricción SQL `UNIQUE(barcode)`:** es la última garantía, también frente a escrituras manuales o concurrentes.

   Al documentar la instalación comprobé en el código de Odoo que, si la base ya contiene códigos duplicados, Odoo instala el módulo igualmente pero **sin crear la restricción**, y solo lo deja reflejado en el log. Es decir, la garantía desaparecería sin que nadie se diera cuenta. Para evitarlo, añadí un `pre_init_hook` que busca duplicados antes de instalar y, si los encuentra, detiene la instalación con la lista de códigos y productos afectados. No los corrijo automáticamente, porque eso sería modificar datos existentes sin una acción explícita del usuario.
3. **Choque concurrente:** si dos usuarios obtienen el mismo código al mismo tiempo, la base de datos rechaza el segundo. Ese error lo convierto en un mensaje comprensible, solo cuando procede de esta restricción concreta. Cualquier otro error de base de datos se deja pasar tal cual, para no ocultarlo.

## 10. Multiempresa

- La configuración y la secuencia se toman siempre de la **empresa del producto**, no de la empresa activa del usuario. En una generación masiva con productos de varias empresas, cada uno usa su propia secuencia.
- Las secuencias tienen que pertenecer a la misma empresa o ser compartidas.
- Los productos sin empresa no pueden generar código, porque no hay una configuración de empresa que aplicar. Es uno de los casos que cita el enunciado. Valoré alternativas (preguntar la empresa en un asistente, una secuencia global…), pero cada una implica una regla de negocio que el enunciado no define, y no quería inventarla.

## 11. Integridad de la información

- Nunca se sobrescribe un código existente: si la variante ya tiene uno, se rechaza antes de generar.
- No se consumen números de secuencias inválidas o que pertenecen a otros documentos.
- No se puede dejar una secuencia en uso en un estado que produzca códigos incorrectos.
- La instalación no modifica ningún dato existente: si encuentra códigos duplicados, se detiene y deja que sea el usuario quien los corrija.

## 12. Correspondencia con los requisitos

| Requisito | Dónde se cubre |
|---|---|
| 1. Generación de códigos | `action_generate_ean13`, `_generate_ean13_from_sequence`, `_calculate_ean13_check_digit` |
| 2. Configuración por empresa | `res.company`, `res.config.settings`, validación de la secuencia |
| 3. Generación individual y disponibilidad | Botón en las fichas de variante y de producto, `can_generate_ean13` |
| 4. Generación masiva | `ean13.generate.wizard` con `savepoint` por variante |
| 5. Seguridad | Grupo `group_ean13_generator`, `groups` en vistas y acción, `has_group` en el servidor |
| 6. Validaciones | `_validate_ean13_generation`, `_check_ean13_generation_access`, `_get_ean13_sequence_errors` |
| 7. Unicidad | `_check_ean13_availability`, restricción SQL y tratamiento de `UniqueViolation` |
| 8. Multiempresa | Configuración de la empresa del producto, validación de la empresa de la secuencia |
| 9. Integridad | Sin sobrescritura, validación antes de consumir la secuencia |
| 10. Experiencia de usuario | Integración en Ajustes, fichas y acciones estándar; mensajes con la causa y la empresa |

## 13. Tests

El módulo incluye 33 tests automáticos (`post_install`), que cubren:

- **Dígito de control:** valores conocidos y bases inválidas, incluidos los dígitos Unicode.
- **Validaciones:** código previo, sin empresa, generación desactivada, sin secuencia y permisos.
- **Unicidad:** contra variantes activas y archivadas, contra embalajes, entre empresas y con un choque concurrente simulado.
- **Configuración de la secuencia:** casos válidos e inválidos, modificación de una secuencia en uso, y que no se consuma ningún número cuando la secuencia no es válida.
- **Ficha de producto:** con una y con varias variantes.
- **Vistas:** que el botón aparezca o no según el grupo, en las tres fichas.
- **Asistente masivo:** varias empresas con errores intercalados.
- **Instalación:** que se detenga si hay códigos duplicados, incluidos los de variantes archivadas.

Al lanzarlos contra mi base de desarrollo, algunos fallaban porque los códigos que esperaban ya los había generado yo probando a mano. Para que no dependan de los datos, todos heredan de una clase base que deja libres los códigos existentes **dentro de la transacción del test**. Odoo revierte esa transacción al terminar, así que se pueden ejecutar contra cualquier base sin modificar nada.

## 14. Limitaciones conocidas

Estas son las limitaciones que conozco. Algunas las he dejado así de forma consciente y otras dependen del propio Odoo:

- **Choques con la numeración.** Si la secuencia entrega un número cuyo código ya existe (por ejemplo, porque alguien lo introdujo a mano), la generación de esa variante se detiene con un error en lugar de pasar al siguiente número. Nunca se crea un duplicado, pero la variante se queda sin código hasta que se ajuste la secuencia. Reintentar automáticamente implicaría consumir números en silencio, y preferí no tomar esa decisión sin que el enunciado la pidiera.
- **Códigos GS1.** Los códigos son EAN-13 válidos, pero solo son oficiales si la secuencia usa como prefijo el prefijo de empresa asignado por GS1.
- **Rango de la secuencia.** Odoo guarda el siguiente número de una secuencia como entero de 32 bits (máximo 2.147.483.647), menos que el rango teórico de 12 dígitos. Lo descubrí al escribir un test de secuencia agotada. En la práctica no es un problema, pero conviene saberlo.
- **Productos sin empresa.** No pueden generar código, por las razones del apartado 10.

## 15. Cómo he trabajado

He utilizado IA como apoyo durante el desarrollo: para revisar el código, contrastar alternativas, consultar el comportamiento interno de Odoo y acelerar la escritura de tests y documentación. Las decisiones sobre qué implementar, qué dejar fuera y cómo resolver cada problema han sido mías, y he probado cada cambio tanto con los tests como en la propia interfaz de Odoo.
