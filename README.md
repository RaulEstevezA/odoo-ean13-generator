# Generador EAN-13 para productos (Odoo 18)

Módulo de Odoo 18 que genera códigos de barras **EAN-13** válidos y únicos para variantes de producto, con configuración por empresa, control de permisos y generación individual o masiva.

La explicación de la solución adoptada (diseño, decisiones y limitaciones) está en [docs/SOLUCION.md](docs/SOLUCION.md).

## Funcionalidades

- Generación de un EAN-13 válido (con dígito de control) para variantes sin código de barras.
- Configuración por empresa: activación de la funcionalidad y secuencia de numeración.
- Generación individual desde la ficha de la variante y desde la ficha del producto (si tiene una única variante).
- Generación masiva desde la lista de variantes, con resumen de resultados y errores por variante.
- Grupo de seguridad específico para controlar qué usuarios pueden generar códigos.
- Unicidad global: el código no puede repetirse en ninguna variante (activa o archivada) ni embalaje.

## Requisitos

- Odoo 18.0 (Community o Enterprise).
- Módulos de Odoo: `product` y `base_setup` (se instalan automáticamente como dependencias).
- Para acceder a los productos desde el menú, alguna aplicación que los muestre: Inventario, Ventas o Compras.

## Instalación

Hay dos formas de preparar el entorno. Después, la instalación del módulo es igual en los dos casos.

### Opción A: entorno nuevo con Docker

Crea desde cero un Odoo 18 con PostgreSQL, usando las imágenes oficiales. Solo requiere Docker con Docker Compose.

1. Crear una carpeta para el entorno y, dentro, una carpeta `addons` con el módulo:

   ```
   odoo-ean13/
   ├── compose.yaml
   └── addons/
       └── product_ean13_generator/
   ```

   ```bash
   mkdir -p odoo-ean13/addons
   cp -r product_ean13_generator odoo-ean13/addons/
   cd odoo-ean13
   ```

2. Crear el fichero `compose.yaml` con este contenido:

   ```yaml
   services:
     db:
       image: postgres:16
       environment:
         POSTGRES_USER: odoo
         POSTGRES_PASSWORD: odoo
         POSTGRES_DB: postgres
       volumes:
         - db-data:/var/lib/postgresql/data

     odoo:
       image: odoo:18
       depends_on:
         - db
       ports:
         - "127.0.0.1:8069:8069"
       environment:
         HOST: db
         USER: odoo
         PASSWORD: odoo
       volumes:
         - ./addons:/mnt/extra-addons
         - odoo-data:/var/lib/odoo

   volumes:
     db-data:
     odoo-data:
   ```

   La imagen oficial de Odoo ya incluye `/mnt/extra-addons` en su `addons_path`, así que no hace falta configurar nada más.

3. Arrancar los contenedores:

   ```bash
   docker compose up -d
   ```

4. Abrir `http://localhost:8069` y crear una base de datos desde el gestor de Odoo. Para probar el módulo con productos de ejemplo, marcar **Datos de demostración**.

5. Instalar la aplicación **Inventario** (o Ventas), para tener acceso a los menús de productos.

Para borrar el entorno por completo, incluidos los datos: `docker compose down -v`.

### Opción B: instalación existente de Odoo

Copiar esta carpeta (la que contiene `product_ean13_generator/`) en el servidor y añadir su ruta al parámetro `addons_path` del fichero de configuración de Odoo:

```ini
addons_path = /ruta/a/odoo/addons,/ruta/a/odoo-ean13-generator
```

También se puede copiar directamente la carpeta `product_ean13_generator/` dentro de un directorio de addons que ya esté en `addons_path`.

Después, reiniciar el servidor de Odoo.

### Instalar el módulo

Desde la interfaz:

1. Activar el **modo desarrollador** (Ajustes → Activar el modo de desarrollador).
2. Ir a **Aplicaciones → Actualizar lista de aplicaciones**.
3. Quitar el filtro "Aplicaciones", buscar **Generador EAN-13 para productos** y pulsar **Activar**.

O desde la línea de comandos. Con el entorno Docker de la opción A:

```bash
docker compose exec odoo odoo -d <base_de_datos> \
  --db_host=db --db_user=odoo --db_password=odoo \
  -i product_ean13_generator --stop-after-init --no-http
docker compose restart odoo
```

Con una instalación existente:

```bash
odoo-bin -c <fichero_de_configuracion> -d <base_de_datos> \
  -i product_ean13_generator --stop-after-init --no-http
```

Y reiniciar después el servidor de Odoo. Según cómo esté instalado Odoo, el ejecutable puede llamarse `odoo-bin` (código fuente) u `odoo` (paquete o imagen oficial).

> **Importante:** el módulo exige que el código de barras de las variantes sea único en todo el sistema. Odoo, por defecto, permite el mismo código en empresas distintas, así que una base de datos existente puede contener duplicados. En ese caso **la instalación se detiene** con un mensaje que indica qué códigos y qué productos están duplicados. Hay que corregirlos y volver a instalar. El módulo no los corrige automáticamente para no modificar datos existentes.
>
> Para localizarlos también se puede usar esta consulta:
>
> ```sql
> SELECT barcode, array_agg(id) FROM product_product
> WHERE barcode IS NOT NULL GROUP BY barcode HAVING count(*) > 1;
> ```

## Configuración

### 1. Crear la secuencia EAN-13

En modo desarrollador, ir a **Ajustes → Técnico → Secuencias** y crear una secuencia por empresa (o una compartida) que genere **exactamente 12 dígitos**. El dígito de control (el 13.º) lo calcula el módulo.

| Campo | Valor recomendado |
|---|---|
| Nombre | `Secuencia EAN-13 <empresa>` |
| Implementación | Estándar |
| Prefijo | Vacío o solo dígitos (p. ej., el prefijo de empresa GS1) |
| Sufijo | Vacío o solo dígitos |
| Relleno | `12 - longitud del prefijo - longitud del sufijo` |
| Empresa | La empresa que la utilizará, o vacía para compartirla |
| Usar subsecuencias por rango de fechas | Desmarcado |

Ejemplos válidos: sin prefijo y relleno `12`; prefijo `84` y relleno `10`.

El módulo rechaza al guardar cualquier secuencia que no cumpla estas reglas, con un mensaje que indica la causa.

### 2. Activar la generación en cada empresa

1. Seleccionar la empresa en el selector de empresas.
2. Ir a **Ajustes → Ajustes generales → Códigos EAN-13**.
3. Marcar **Generación de códigos EAN-13** y seleccionar la **Secuencia EAN-13**.
4. Guardar.

Repetir para cada empresa. La configuración es independiente por empresa.

### 3. Dar permisos a los usuarios

En **Ajustes → Usuarios y compañías → Usuarios**, abrir el usuario y, en la sección **EAN-13 de productos**, activar **Generar códigos EAN-13**.

Los usuarios sin este grupo no ven las acciones de generación, y el servidor rechaza la operación aunque se invoque directamente.

## Uso

### Generación individual

El botón **Generar EAN-13** aparece junto al campo **Código de barras** en:

- La ficha de la variante (**Inventario → Productos → Variantes de producto**, o desde el botón **Variantes** del producto).
- La ficha del producto, cuando este tiene una única variante.

El botón solo se muestra si el usuario tiene permisos, la variante no tiene código de barras y su empresa tiene la generación activada con una secuencia válida.

### Generación masiva

1. Ir a **Inventario → Productos → Variantes de producto**.
2. Seleccionar las variantes en la vista de lista.
3. **Acción → Generar códigos EAN-13** y pulsar **Generar**.

El asistente procesa cada variante de forma independiente: un error en una variante no impide generar las demás. Al terminar, muestra cuántos códigos se han generado, cuántos errores ha habido y el detalle de cada variante.

## Tests

El módulo incluye 33 tests automáticos. Se ejecutan dentro de una transacción que se revierte al terminar, por lo que no modifican los datos de la base de datos. Aun así, se recomienda lanzarlos sobre una base de datos dedicada a pruebas.

Con el entorno Docker de la opción A:

```bash
docker compose exec odoo odoo -d <base_de_datos> \
  --db_host=db --db_user=odoo --db_password=odoo \
  --test-enable --test-tags /product_ean13_generator \
  --stop-after-init --http-port=8071
```

Con una instalación existente:

```bash
odoo-bin -c <fichero_de_configuracion> -d <base_de_datos> \
  --test-enable --test-tags /product_ean13_generator \
  --stop-after-init --http-port=8071
```

El resultado esperado es `0 failed, 0 error(s) of 33 tests`.

Al activar los tests, Odoo arranca su servidor HTTP. Se usa `--http-port=8071` para no chocar con un servidor que ya esté escuchando en el puerto 8069. Para ejecutar los tests tras modificar el código, añadir `-u product_ean13_generator`.

## Estructura

```
product_ean13_generator/
├── __manifest__.py
├── hooks.py                      # Bloquea la instalación si hay códigos duplicados
├── models/
│   ├── ir_sequence.py            # Impide invalidar una secuencia en uso
│   ├── product_product.py        # Generación, validaciones y unicidad
│   ├── product_template.py       # Generación desde productos con una variante
│   ├── res_company.py            # Configuración y validación de la secuencia
│   └── res_config_settings.py    # Configuración en Ajustes
├── wizard/
│   └── ean13_generate_wizard.py  # Generación masiva
├── views/
│   ├── ean13_generate_wizard_views.xml
│   ├── product_product_views.xml
│   ├── product_template_views.xml
│   └── res_config_settings_views.xml
├── security/
│   ├── security.xml              # Grupo "Generar códigos EAN-13"
│   └── ir.model.access.csv
└── tests/
```

## Licencia

AGPL-3. Ver [LICENSE](LICENSE).
