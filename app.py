from flask import Flask, render_template
from pymongo import MongoClient
from flask import abort
from bson.objectid import ObjectId
from flask import Flask, render_template, request, abort
from flask import Flask, render_template, request, redirect, url_for, session, abort
from bson import ObjectId

#La primera parte importa las librerías esenciales. Flask es el framework que utilizo para crear aplicaciones web en Python, 
# y me permite definir rutas, manejar peticiones y gestionar sesiones (almacenar información temporal del usuario, como el carrito).
#render_template se usa para renderizar archivos HTML con datos dinámicos.
#request me permite acceder a los datos enviados por el usuario (como formularios o parámetros en la URL).
#redirect y url_for son funciones que ayudan a redirigir al usuario entre páginas de forma segura.
#session guarda información específica de cada usuario, como el carrito de compras.
#abort me permite mostrar mensajes de error cuando algo sale mal (por ejemplo, si se busca un producto que no existe).
#pymongo es la librería que permite conectar y trabajar con MongoDB desde Python.
#Finalmente, ObjectId es necesario para manejar los identificadores únicos de cada documento en MongoDB (sirve para buscar, actualizar o borrar productos por su ID).




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

#Aquí se crea la instancia principal de la app Flask, indicando en qué carpetas están los archivos estáticos (como imágenes y CSS) y las plantillas HTML.
#La línea app.secret_key establece una clave secreta obligatoria para que Flask pueda cifrar y proteger los datos que guarda en la sesión del usuario (como su carrito de compras),
#de modo que no puedan ser manipulados desde fuera.
#Luego, configuro la conexión a MongoDB utilizando la URI provista por MongoDB Atlas. Esto me da un objeto client con el que puedo interactuar con mi base de datos. Finalmente, 
#selecciono la base de datos específica que utilizaré (tienda_electronica) y guardo la referencia en db para futuras consultas.


@app.route('/')
def home():
    # 1) Traer siempre todas las categorías para el menú
    categorias = list(db.categorias.find({}, {"_id": 0, "nombre": 1}))

    # 2) Leer el parámetro ?filter= de la URL (por defecto 'new')
    filtro = request.args.get('filter', 'new')
    if filtro not in ('new', 'bestseller'):
        filtro = 'new'

    # 3) Construir la consulta según el filtro
    projection = {"_id": 1, "nombre": 1, "descripcion": 1, "precio": 1, "imagen": 1}
    if filtro == 'new':
        # Nuevas llegadas: orden descendente por _id
        cursor = db.productos.find({}, projection).sort('_id', -1).limit(8)
    else: #'bestseller'
        # Más vendidos: orden descendente por ventas (debes tener ese campo en tu doc)
         cursor = db.productos.find(
        {'tipo': 'bestseller'}, projection
    ).sort('_id', -1).limit(8)

    productos = list(cursor)

    # 4) Renderizar pasando también el filtro activo
    return render_template(
        'index.html',
        categorias=categorias,
        productos=productos,
        filtro_activo=filtro
    )


#Esta función se activa cuando el usuario entra a la página principal.
#Primero, recupera todas las categorías de productos desde la colección categorias para mostrarlas en el menú de navegación.
#Luego, lee el filtro de productos seleccionado por el usuario en la URL (por ejemplo, /?filter=bestseller), y si no se especifica o es incorrecto,
#  muestra por defecto los productos nuevos (new).
#Para mostrar los productos, construyo una consulta diferente según el filtro:

#Si es “new”, muestra los productos más recientes usando el campo _id (MongoDB genera IDs de forma creciente con la fecha).

#Si es “bestseller”, los ordena por el campo ventas para destacar los productos más vendidos.
#Solo se muestran los 8 primeros productos para no sobrecargar la página.
#Por último, todos los datos se envían a la plantilla index.html, donde se muestran los productos y las categorías de forma visual y dinámica.


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


#Cuando el usuario elige una categoría específica, esta ruta toma el nombre de la categoría desde la URL y busca todos los productos que tengan esa categoría en la base de datos.
#Al igual que en la página principal, vuelve a consultar todas las categorías para mantener el menú actualizado.
#Envía tanto los productos filtrados como la lista de categorías a la plantilla categoria.html.
#La variable selected sirve para resaltar la categoría actual en la interfaz de usuario, haciendo más intuitiva la navegación.




@app.route('/producto/<id>')
def producto_detalle(id):
    try:
        # Convertimos la cadena 'id' a ObjectId de Mongo
        oid = ObjectId(id)
    except Exception:
        abort(404)
    # Buscamos el producto por su _id
    prod = db.productos.find_one({'_id': oid},
                                 {'nombre':1, 'descripcion':1, 'precio':1, 'imagen':1})
    if not prod:
        abort(404)
    # Convertimos el ObjectId a cadena para el template (si lo necesitamos)
    prod['id'] = str(prod['_id'])
    return render_template('producto.html', producto=prod)

#Cuando un usuario quiere ver el detalle de un producto, esta función toma el ID del producto desde la URL,
#lo convierte a formato ObjectId (obligatorio para buscar en MongoDB), y busca el documento correspondiente.
#Si el ID no es válido o no se encuentra el producto, retorna un error 404 mostrando que el producto no existe.
#Si el producto existe, envía toda la información necesaria al template producto.html, donde el usuario puede ver la descripción, la imagen, el precio y otros detalles.
#Esto permite una navegación directa y detallada para cada producto en la tienda.



@app.route('/cart/add/<id>', methods=['POST'])
def add_to_cart(id):
    # 1) Validar que el ID sea correcto
    try:
        oid = ObjectId(id)
    except:
        abort(404)

    # 2) Buscar el producto en la base de datos
    prod = db.productos.find_one(
        {'_id': oid},
        {'nombre':1, 'precio':1, 'imagen':1}
    )
    if not prod:
        abort(404)

    # 3) Recuperar o inicializar el carrito en sesión
    cart = session.get('cart', {})

    # 4) Sumar 1 a la cantidad de este producto
    cart[id] = cart.get(id, 0) + 1

    # 5) Guardar de nuevo en sesión
    session['cart'] = cart

    # 6) Redirigir al usuario al carrito
    return redirect(url_for('view_cart'))


#Cuando el usuario hace clic en “Agregar al carrito”, esta función recibe el ID del producto y lo valida.
#Si el producto existe, suma uno a la cantidad de ese producto en el carrito (que se guarda en la variable de sesión del usuario).
#Si el producto no estaba antes, lo agrega con cantidad 1.
#Esto permite al usuario ir acumulando productos de forma persistente mientras navega por la página, aunque cierre o recargue el navegador (mientras la sesión siga activa).
#Después de agregar, redirige al usuario a la página del carrito para que pueda ver y editar su compra.



@app.route('/cart')
def view_cart():
    # 1) Recuperar el carrito de la sesión (un dict {id_str: cantidad})
    cart = session.get('cart', {})

    # 2) Si está vacío, renderizamos directamente
    if not cart:
        return render_template('cart.html', items=[], subtotal=0)

    # 3) Buscar los datos de cada producto en la base
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


#Esta función permite mostrar al usuario todos los productos que ha agregado a su carrito.
#Recorre cada elemento almacenado en la sesión, consulta en la base de datos los detalles de cada producto, y calcula el subtotal de la compra.
#Envia toda la información al template cart.html, donde se puede visualizar el nombre, la imagen, el precio, la cantidad y el total de cada producto del carrito.
#Si el carrito está vacío, muestra un mensaje apropiado.



# 3.1.a) Aumentar o disminuir cantidad
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

#El usuario puede aumentar o disminuir la cantidad de un producto en el carrito desde la interfaz.
#Esta función toma el ID del producto y la operación (“increase” o “decrease”).
#Si la operación es “increase”, suma uno; si es “decrease”, resta uno pero nunca baja de uno para evitar cantidades inválidas.
#Después de modificar, guarda el carrito actualizado en la sesión y muestra el carrito actualizado.




# 3.1.b) Eliminar producto del carrito
@app.route('/cart/remove/<id>')
def remove_from_cart(id):
    cart = session.get('cart', {})
    if id in cart:
        cart.pop(id)
        session['cart'] = cart
    return redirect(url_for('view_cart'))



#Si el usuario quiere quitar completamente un producto del carrito, esta función elimina ese producto de la variable de sesión.
#Luego redirige de nuevo a la página del carrito, permitiendo que el usuario vea el cambio en tiempo real.






@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if request.method == 'POST':
        # 1. Recupera el carrito de la sesión
        cart = session.get('cart', {})
        # 2. Elimina cada producto del carrito de la base de datos
        for id_str in cart:
            try:
                oid = ObjectId(id_str)
                db.productos.delete_one({'_id': oid})
            except Exception:
                continue
        # 3. Limpia el carrito
        session.pop('cart', None)
        # 4. Redirige a la página de éxito
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




#La función checkout gestiona tanto la visualización del resumen de compra como la finalización de la compra en una tienda web. 
#Cuando el usuario visita la página (GET), recupera todos los productos que tiene en su carrito de compras desde la sesión, 
#obtiene sus detalles desde la base de datos y calcula el subtotal, mostrando así el formulario de pago. Cuando el usuario confirma el pago (POST), 
#el sistema elimina de la base de datos cada producto comprado, limpia el carrito de la sesión para dejarlo vacío y redirige al usuario a una página de éxito 
#que confirma que la compra fue realizada. Así, esta función centraliza la lógica para el proceso final de la compra y la actualización del inventario en la tienda.

@app.route('/checkout/success')
def checkout_success():
    # Limpia el carrito o muestra el mensaje
    session.pop('cart', None)
    return render_template('success.html')

#Cuando la compra termina con éxito, esta ruta elimina el carrito de la sesión, dejando la compra limpia para una próxima compra.
#Después, renderiza la página de éxito donde se puede mostrar un mensaje de confirmación y agradecimiento al usuario.



if __name__ == "__main__":
    # Ejecuta en localhost:5000 con recarga y debug activo
    app.run(host="0.0.0.0", port=5000, debug=True)

#Este bloque comprueba si el archivo está siendo ejecutado directamente (no importado como módulo).
#Si es así, arranca el servidor Flask, permitiendo acceder a la aplicación desde cualquier equipo en la red local usando el puerto 5000.
#La opción debug=True ayuda a encontrar errores durante el desarrollo mostrando mensajes detallados en la consola.
