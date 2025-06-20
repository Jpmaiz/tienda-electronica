from flask import Flask, render_template
from pymongo import MongoClient
from flask import abort
from bson.objectid import ObjectId
from flask import Flask, render_template, request, abort
from flask import Flask, render_template, request, redirect, url_for, session, abort
from bson import ObjectId


# Configuración de la app
app = Flask(
    __name__,
    static_folder="static",      # carpeta de CSS/JS/IMG
    template_folder="templates"  # carpeta de plantillas .html
)

app.secret_key = "TU_VALOR_SUPER_SECRETO_AQUÍ"

uri = (
    "mongodb+srv://maizhinojosajuanpablo:Maizjuan2"
    "@cluster0.zkplaw2.mongodb.net/tienda_electronica"
    "?retryWrites=true&w=majority&appName=Cluster0"
)
client = MongoClient(uri)
db = client["tienda_electronica"]



@app.route('/')
def home():
    categorias = list(db.categorias.find({}, {"_id": 0, "nombre": 1}))

    filtro = request.args.get('filter', 'new')
    if filtro not in ('new', 'bestseller'):
        filtro = 'new'

 
    projection = {"_id": 1, "nombre": 1, "descripcion": 1, "precio": 1, "imagen": 1}
    if filtro == 'new':
 
        cursor = db.productos.find({}, projection).sort('_id', -1).limit(8)
    else: 

         cursor = db.productos.find(
        {'tipo': 'bestseller'}, projection
    ).sort('_id', -1).limit(8)

    productos = list(cursor)


    return render_template(
        'index.html',
        categorias=categorias,
        productos=productos,
        filtro_activo=filtro
    )



@app.route('/categoria/<nombre_categoria>')
def por_categoria(nombre_categoria):

    categorias = list(db.categorias.find({}, {"_id": 0, "nombre": 1}))

    productos = list(db.productos.find(
        {"categoria": nombre_categoria},
        {"_id": 1, "nombre": 1, "descripcion": 1, "precio": 1, "imagen": 1}
    ))
    return render_template(
        'categoria.html',
        categorias=categorias,
        productos=productos,
        selected=nombre_categoria  # categoría actual
    )



@app.route('/producto/<id>')
def producto_detalle(id):
    try:

        oid = ObjectId(id)
    except Exception:
        abort(404)

    prod = db.productos.find_one({'_id': oid},
                                 {'nombre':1, 'descripcion':1, 'precio':1, 'imagen':1})
    if not prod:
        abort(404)

    prod['id'] = str(prod['_id'])
    return render_template('producto.html', producto=prod)





@app.route('/cart/add/<id>', methods=['POST'])
def add_to_cart(id):
    #  Validar que el ID sea correcto
    try:
        oid = ObjectId(id)
    except:
        abort(404)

    #  Buscar el producto en la base de datos
    prod = db.productos.find_one(
        {'_id': oid},
        {'nombre':1, 'precio':1, 'imagen':1}
    )
    if not prod:
        abort(404)

    #  Recuperar o inicializar el carrito en sesión
    cart = session.get('cart', {})

    #  Sumar 1 a la cantidad de este producto
    cart[id] = cart.get(id, 0) + 1

    #  Guardar de nuevo en sesión
    session['cart'] = cart

    #  Redirigir al usuario al carrito
    return redirect(url_for('view_cart'))




@app.route('/cart')
def view_cart():
    #  Recuperar el carrito de la sesión (un dict {id_str: cantidad})
    cart = session.get('cart', {})

    #  Si está vacío, renderizamos directamente
    if not cart:
        return render_template('cart.html', items=[], subtotal=0)

    #  Buscar los datos de cada producto en la base
    #    y construir una lista de ítems con info y cantidad
    items = []
    subtotal = 0
    for id_str, qty in cart.items():
        try:
            oid = ObjectId(id_str)
        except:
            continue  # saltar IDs inválidos

        prod = db.productos.find_one(
            {'_id': oid},
            {'nombre':1, 'precio':1, 'imagen':1}
        )
        if not prod:
            continue

        total_price = prod['precio'] * qty
        subtotal += total_price

        items.append({
            'id': id_str,
            'nombre': prod['nombre'],
            'precio': prod['precio'],
            'imagen': prod['imagen'],
            'cantidad': qty,
            'total': total_price
        })

    return render_template('cart.html', items=items, subtotal=subtotal)





#  Aumentar o disminuir cantidad
@app.route('/cart/update/<id>/<op>')
def update_cart(id, op):
    cart = session.get('cart', {})
    # Si no existe el producto en el carrito, redirige a ver carrito
    if id not in cart:
        return redirect(url_for('view_cart'))

    if op == 'increase':
        cart[id] += 1
    elif op == 'decrease':
        cart[id] = max(1, cart[id] - 1)  # nunca menos de 1
    session['cart'] = cart
    return redirect(url_for('view_cart'))

# Eliminar producto del carrito
@app.route('/cart/remove/<id>')
def remove_from_cart(id):
    cart = session.get('cart', {})
    if id in cart:
        cart.pop(id)
        session['cart'] = cart
    return redirect(url_for('view_cart'))





@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if request.method == 'POST':
        # Recupera el carrito de la sesión
        cart = session.get('cart', {})
        # Elimina cada producto del carrito de la base de datos
        for id_str in cart:
            try:
                oid = ObjectId(id_str)
                db.productos.delete_one({'_id': oid})
            except Exception:
                continue
        # Limpia el carrito
        session.pop('cart', None)
        # Redirige a la página de éxito
        return redirect(url_for('checkout_success'))

    # GET: sigue mostrando el resumen y el formulario
    cart = session.get('cart', {})
    if not cart:
        return redirect(url_for('home'))

    items = []
    subtotal = 0
    for id_str, qty in cart.items():
        try:
            oid = ObjectId(id_str)
        except:
            continue
        prod = db.productos.find_one(
            {'_id': oid},
            {'nombre': 1, 'precio': 1, 'imagen': 1}
        )
        if not prod:
            continue
        total_price = prod['precio'] * qty
        subtotal += total_price
        items.append({
            'id': id_str,
            'nombre': prod['nombre'],
            'precio': prod['precio'],
            'imagen': prod['imagen'],
            'cantidad': qty,
            'total': total_price
        })

    return render_template('checkout.html', items=items, subtotal=subtotal)




@app.route('/checkout/success')
def checkout_success():
    # Limpia el carrito o muestra el mensaje
    session.pop('cart', None)
    return render_template('success.html')




if __name__ == "__main__":
    # Ejecuta en localhost:5000 con recarga y debug activo
    app.run(host="0.0.0.0", port=5000, debug=True)

