from odoo.exceptions import UserError

# Número máximo de códigos duplicados que se detallan en el mensaje.
MAX_DUPLICATES_IN_MESSAGE = 20


def _get_duplicated_barcodes(env):
    """Devuelve ``[(barcode, [product_id, ...]), ...]`` con los duplicados.

    Incluye variantes archivadas, porque la restricción SQL también les
    afecta.
    """
    env.cr.execute(
        """
        SELECT barcode, array_agg(id ORDER BY id)
          FROM product_product
         WHERE barcode IS NOT NULL
      GROUP BY barcode
        HAVING count(*) > 1
      ORDER BY barcode
        """
    )
    return env.cr.fetchall()


def pre_init_hook(env):
    """Impide instalar el módulo si ya existen códigos de barras duplicados.

    El módulo añade una restricción SQL de unicidad global sobre el código de
    barras. Si hay duplicados, Odoo instalaría el módulo sin crear esa
    restricción (solo lo indica en el log), y se perdería la garantía de
    unicidad. Los duplicados no se corrigen automáticamente para no modificar
    datos existentes sin una acción explícita del usuario.
    """
    duplicates = _get_duplicated_barcodes(env)
    if not duplicates:
        return

    products = (
        env["product.product"]
        .sudo()
        .with_context(active_test=False)
        .browse({pid for _barcode, ids in duplicates for pid in ids})
    )
    names = {product.id: product.display_name for product in products}

    lines = [
        env._(
            "- %(barcode)s: %(products)s",
            barcode=barcode or env._("(vacío)"),
            products=", ".join(f"{names[pid]} (ID {pid})" for pid in ids),
        )
        for barcode, ids in duplicates[:MAX_DUPLICATES_IN_MESSAGE]
    ]
    if len(duplicates) > MAX_DUPLICATES_IN_MESSAGE:
        lines.append(
            env._(
                "... y %(count)s códigos duplicados más.",
                count=len(duplicates) - MAX_DUPLICATES_IN_MESSAGE,
            )
        )

    raise UserError(
        env._(
            "No se puede instalar el generador de EAN-13 porque existen "
            "variantes de producto con el mismo código de barras. El módulo "
            "exige que cada código sea único en todo el sistema.\n\n"
            "Corrija los siguientes códigos antes de instalar:\n%(lines)s",
            lines="\n".join(lines),
        )
    )
